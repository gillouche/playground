import logging
import uuid
from datetime import UTC, datetime, timedelta

from cache.redis_cache import BOOK_TTL, BOOKS_ALL_TTL, INVENTORY_TTL, RedisCache
from database.models import Book, Reservation, ReservationStatus
from schemas.book import (
    BookCreate,
    BookResponse,
    BookUpdate,
    ReservationCreate,
    ReservationResponse,
)
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("api-lab.service")

LOAN_DURATION_DAYS = 14


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
            return [BookResponse(**b) for b in cached]

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
            return BookResponse(**cached)

        async with self._session_factory() as session:
            result = await session.execute(select(Book).where(Book.id == book_id))
            book = result.scalar_one_or_none()
            if not book:
                return None
            response = BookResponse.model_validate(book)
            await self._cache.set(cache_key, response.model_dump(), BOOK_TTL)
            return response

    async def create_book(self, data: BookCreate) -> BookResponse:
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
            await session.commit()
            await session.refresh(book)
            await self._cache.invalidate_books()
            return BookResponse.model_validate(book)

    async def update_book(self, book_id: uuid.UUID, data: BookUpdate) -> BookResponse | None:
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
            await session.commit()
            await session.refresh(book)
            await self._cache.invalidate_books()
            return BookResponse.model_validate(book)

    async def delete_book(self, book_id: uuid.UUID) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(Book).where(Book.id == book_id))
            book = result.scalar_one_or_none()
            if not book:
                return False
            await session.delete(book)
            await session.commit()
            await self._cache.invalidate_books()
            return True

    async def get_inventory(self) -> list[BookResponse]:
        cache_key = "inventory"
        cached = await self._cache.get(cache_key)
        if cached:
            return [BookResponse(**b) for b in cached]

        async with self._session_factory() as session:
            result = await session.execute(select(Book).where(Book.available_copies > 0))
            books = result.scalars().all()
            responses = [BookResponse.model_validate(b) for b in books]
            await self._cache.set(cache_key, [r.model_dump() for r in responses], INVENTORY_TTL)
            return responses

    async def reserve_books(self, data: ReservationCreate) -> list[ReservationResponse]:
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
            await self._cache.invalidate_books()
            return [ReservationResponse.model_validate(r) for r in reservations]

    async def return_reservation(self, reservation_id: uuid.UUID) -> ReservationResponse | None:
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
            await self._cache.invalidate_books()
            return ReservationResponse.model_validate(reservation)

    async def list_reservations(
        self,
        user_id: str | None = None,
        status: str | None = None,
        book_id: uuid.UUID | None = None,
    ) -> list[ReservationResponse]:
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
        async with self._session_factory() as session:
            result = await session.execute(
                select(Reservation).where(Reservation.id == reservation_id)
            )
            reservation = result.scalar_one_or_none()
            if not reservation:
                return None
            return ReservationResponse.model_validate(reservation)
