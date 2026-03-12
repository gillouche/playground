import logging
import uuid
from datetime import UTC, datetime, timedelta

from cache.redis_cache import BOOK_TTL, BOOKS_ALL_TTL, INVENTORY_TTL, RedisCache
from database.models import Book, Reservation, ReservationStatus
from generated.models import (
    BookCreate,
    BookResponse,
    BookUpdate,
    ReservationCreate,
    ReservationResponse,
)
from observability.metrics import (
    active_reservations_gauge,
    books_available_gauge,
    books_created_total,
    cache_hits_total,
    cache_misses_total,
    db_query_duration_seconds,
    reservations_created_total,
    reservations_returned_total,
)
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("api-lab.service")

LOAN_DURATION_DAYS = 14


class DuplicateISBNError(Exception):
    """Raised when attempting to create a book with a duplicate ISBN."""

    def __init__(self, isbn: str):
        self.isbn = isbn
        super().__init__(f"A book with ISBN '{isbn}' already exists")


class BookService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], cache: RedisCache):
        self._session_factory = session_factory
        self._cache = cache

    async def list_books(
        self,
        available_only: bool = False,
        genre: str | None = None,
        author: str | None = None,
        search: str | None = None,
    ) -> list[BookResponse]:
        cache_key = f"books:all:{available_only}:{genre}:{author}:{search}"
        cached = await self._cache.get(cache_key)
        if cached:
            cache_hits_total.labels(operation="list_books").inc()
            return [BookResponse(**b) for b in cached]
        cache_misses_total.labels(operation="list_books").inc()

        with db_query_duration_seconds.labels(operation="list_books").time():
            async with self._session_factory() as session:
                query = select(Book)
                if available_only:
                    query = query.where(Book.available_copies > 0)
                if genre:
                    query = query.where(Book.genre == genre)
                if author:
                    query = query.where(Book.author.ilike(f"%{author}%"))
                if search:
                    query = query.where(
                        or_(
                            Book.title.ilike(f"%{search}%"),
                            Book.author.ilike(f"%{search}%"),
                            Book.isbn.ilike(f"%{search}%"),
                        )
                    )
                result = await session.execute(query)
                books = result.scalars().all()

        responses = [BookResponse.model_validate(b) for b in books]
        await self._cache.set(cache_key, [r.model_dump() for r in responses], BOOKS_ALL_TTL)
        return responses

    async def get_book(self, book_id: uuid.UUID) -> BookResponse | None:
        cache_key = f"books:{book_id}"
        cached = await self._cache.get(cache_key)
        if cached:
            cache_hits_total.labels(operation="get_book").inc()
            return BookResponse(**cached)
        cache_misses_total.labels(operation="get_book").inc()

        with db_query_duration_seconds.labels(operation="get_book").time():
            async with self._session_factory() as session:
                result = await session.execute(select(Book).where(Book.id == book_id))
                book = result.scalar_one_or_none()

        if not book:
            return None
        response = BookResponse.model_validate(book)
        await self._cache.set(cache_key, response.model_dump(), BOOK_TTL)
        return response

    async def create_book(self, data: BookCreate) -> BookResponse:
        with db_query_duration_seconds.labels(operation="create_book").time():
            async with self._session_factory() as session:
                book = Book(
                    isbn=data.isbn,
                    title=data.title,
                    author=data.author,
                    genre=data.genre,
                    published_year=data.published_year,
                    total_copies=data.total_copies,
                    available_copies=data.total_copies,
                )
                session.add(book)
                try:
                    await session.commit()
                except IntegrityError as e:
                    await session.rollback()
                    if "isbn" in str(e.orig).lower() or "unique" in str(e.orig).lower():
                        raise DuplicateISBNError(data.isbn) from e
                    raise
                await session.refresh(book)

        books_created_total.inc()
        await self._cache.invalidate_books()
        await self._update_gauges()
        return BookResponse.model_validate(book)

    async def update_book(self, book_id: uuid.UUID, data: BookUpdate) -> BookResponse | None:
        with db_query_duration_seconds.labels(operation="update_book").time():
            async with self._session_factory() as session:
                result = await session.execute(select(Book).where(Book.id == book_id))
                book = result.scalar_one_or_none()
                if not book:
                    return None
                update_data = data.model_dump(exclude_unset=True)
                if "total_copies" in update_data:
                    diff = update_data["total_copies"] - book.total_copies
                    book.available_copies = max(0, book.available_copies + diff)
                for field, value in update_data.items():
                    setattr(book, field, value)
                book.updated_at = datetime.now(UTC)
                try:
                    await session.commit()
                except IntegrityError as e:
                    await session.rollback()
                    if "isbn" in str(e.orig).lower() or "unique" in str(e.orig).lower():
                        raise DuplicateISBNError(update_data.get("isbn", "")) from e
                    raise
                await session.refresh(book)

        await self._cache.invalidate_books()
        await self._update_gauges()
        return BookResponse.model_validate(book)

    async def delete_book(self, book_id: uuid.UUID) -> bool:
        with db_query_duration_seconds.labels(operation="delete_book").time():
            async with self._session_factory() as session:
                result = await session.execute(select(Book).where(Book.id == book_id))
                book = result.scalar_one_or_none()
                if not book:
                    return False
                await session.delete(book)
                await session.commit()

        await self._cache.invalidate_books()
        await self._update_gauges()
        return True

    async def get_inventory(self) -> list[BookResponse]:
        cache_key = "inventory"
        cached = await self._cache.get(cache_key)
        if cached:
            cache_hits_total.labels(operation="get_inventory").inc()
            return [BookResponse(**b) for b in cached]
        cache_misses_total.labels(operation="get_inventory").inc()

        with db_query_duration_seconds.labels(operation="get_inventory").time():
            async with self._session_factory() as session:
                result = await session.execute(select(Book).where(Book.available_copies > 0))
                books = result.scalars().all()

        responses = [BookResponse.model_validate(b) for b in books]
        await self._cache.set(cache_key, [r.model_dump() for r in responses], INVENTORY_TTL)
        return responses

    async def reserve_books(self, data: ReservationCreate) -> list[ReservationResponse]:
        with db_query_duration_seconds.labels(operation="reserve_books").time():
            async with self._session_factory() as session:
                reservations = []
                for book_id in data.book_ids:
                    result = await session.execute(
                        select(Book).where(Book.id == book_id).with_for_update()
                    )
                    book = result.scalar_one_or_none()
                    if not book:
                        raise ValueError(f"Book {book_id} not found")
                    if book.available_copies <= 0:
                        raise ValueError(f"Book '{book.title}' is not available for reservation")
                    book.available_copies -= 1
                    reservation = Reservation(
                        book_id=book_id,
                        user_id=data.user_id,
                        due_date=datetime.now(UTC) + timedelta(days=LOAN_DURATION_DAYS),
                        status=ReservationStatus.ACTIVE,
                    )
                    session.add(reservation)
                    reservations.append(reservation)
                await session.commit()
                for r in reservations:
                    await session.refresh(r)

        reservations_created_total.inc(len(reservations))
        await self._cache.invalidate_books()
        await self._update_gauges()
        return [ReservationResponse.model_validate(r) for r in reservations]

    async def return_reservation(self, reservation_id: uuid.UUID) -> ReservationResponse | None:
        with db_query_duration_seconds.labels(operation="return_reservation").time():
            async with self._session_factory() as session:
                result = await session.execute(
                    select(Reservation).where(Reservation.id == reservation_id)
                )
                reservation = result.scalar_one_or_none()
                if not reservation:
                    return None
                if reservation.status != ReservationStatus.ACTIVE:
                    raise ValueError(f"Reservation is already {reservation.status.value}")
                reservation.status = ReservationStatus.RETURNED
                reservation.returned_at = datetime.now(UTC)
                book_result = await session.execute(
                    select(Book).where(Book.id == reservation.book_id).with_for_update()
                )
                book = book_result.scalar_one()
                book.available_copies += 1
                await session.commit()
                await session.refresh(reservation)

        reservations_returned_total.inc()
        await self._cache.invalidate_books()
        await self._update_gauges()
        return ReservationResponse.model_validate(reservation)

    async def list_reservations(
        self,
        user_id: str | None = None,
        status: str | None = None,
        book_id: uuid.UUID | None = None,
    ) -> list[ReservationResponse]:
        with db_query_duration_seconds.labels(operation="list_reservations").time():
            async with self._session_factory() as session:
                query = select(Reservation)
                if user_id:
                    query = query.where(Reservation.user_id == user_id)
                if status:
                    query = query.where(Reservation.status == ReservationStatus(status))
                if book_id:
                    query = query.where(Reservation.book_id == book_id)
                result = await session.execute(query)
                reservations = result.scalars().all()
        return [ReservationResponse.model_validate(r) for r in reservations]

    async def get_reservation(self, reservation_id: uuid.UUID) -> ReservationResponse | None:
        with db_query_duration_seconds.labels(operation="get_reservation").time():
            async with self._session_factory() as session:
                result = await session.execute(
                    select(Reservation).where(Reservation.id == reservation_id)
                )
                reservation = result.scalar_one_or_none()
        if not reservation:
            return None
        return ReservationResponse.model_validate(reservation)

    async def _update_gauges(self):
        """Update Prometheus gauges for books available and active reservations."""
        try:
            async with self._session_factory() as session:
                result = await session.execute(select(func.sum(Book.available_copies)))
                total_available = result.scalar() or 0
                books_available_gauge.set(total_available)

                result = await session.execute(
                    select(func.count(Reservation.id)).where(
                        Reservation.status == ReservationStatus.ACTIVE
                    )
                )
                active_count = result.scalar() or 0
                active_reservations_gauge.set(active_count)
        except Exception:
            logger.debug("Failed to update metric gauges", exc_info=True)
