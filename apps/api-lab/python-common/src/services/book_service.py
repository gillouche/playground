import base64
import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime, timedelta

from cache.redis_cache import BOOK_TTL, BOOKS_ALL_TTL, RedisCache
from config import app_config
from generated.models import (
    Book,
    BookCreate,
    BookUpdate,
    ListBooksQuery,
    ListReservationsQuery,
    PaginatedBooks,
    PaginatedReservations,
    Reservation,
    ReservationCreate,
)
from middleware.circuit_breaker import CircuitBreaker
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
from observability.tracing import get_tracer
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.models import Book as BookModel
from database.models import Reservation as ReservationModel
from database.models import ReservationStatus

logger = logging.getLogger("api-lab.service")

LOAN_DURATION_DAYS = 14

BOOK_SORT_COLUMNS = {
    "created_at": BookModel.created_at,
    "updated_at": BookModel.updated_at,
    "title": BookModel.title,
    "author": BookModel.author,
    "published_year": BookModel.published_year,
    "isbn": BookModel.isbn,
}

RESERVATION_SORT_COLUMNS = {
    "reserved_at": ReservationModel.reserved_at,
    "due_date": ReservationModel.due_date,
    "returned_at": ReservationModel.returned_at,
    "status": ReservationModel.status,
}


class DuplicateISBNError(Exception):
    def __init__(self, isbn: str):
        self.isbn = isbn
        super().__init__(f"A book with ISBN '{isbn}' already exists")


class StaleVersionError(Exception):
    pass


class ActiveReservationsError(Exception):
    def __init__(self):
        super().__init__("Cannot delete book with active reservations")


_TOKEN_SECRET = (app_config.git_commit + "continuation-token-salt").encode()


def _sign_offset(offset: int) -> str:
    return hmac.new(_TOKEN_SECRET, str(offset).encode(), hashlib.sha256).hexdigest()[:16]


def _encode_continuation_token(offset: int) -> str:
    sig = _sign_offset(offset)
    return base64.b64encode(f"{offset}:{sig}".encode()).decode()


def _decode_continuation_token(token: str | None) -> int:
    if not token:
        return 0
    try:
        decoded = base64.b64decode(token).decode()
        parts = decoded.split(":", 1)
        if len(parts) != 2:
            return 0
        offset = int(parts[0])
        if offset < 0:
            return 0
        expected_sig = _sign_offset(offset)
        if not hmac.compare_digest(parts[1], expected_sig):
            return 0
        return offset
    except (ValueError, UnicodeDecodeError):
        return 0


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _build_list_books_query(query: ListBooksQuery, sort_column, limit: int, offset: int):
    stmt = select(BookModel)
    if query.available_only:
        stmt = stmt.where(BookModel.available_copies > 0)
    if query.genre:
        stmt = stmt.where(BookModel.genre == query.genre)
    if query.author:
        stmt = stmt.where(BookModel.author.ilike(f"%{_escape_like(query.author)}%", escape="\\"))
    if query.search:
        try:
            ts_vector = func.to_tsvector(
                "english",
                BookModel.title + " " + BookModel.author + " " + BookModel.isbn,
            )
            ts_query = func.plainto_tsquery("english", query.search)
            stmt = stmt.where(ts_vector.op("@@")(ts_query))
        except Exception:
            stmt = stmt.where(
                or_(
                    BookModel.title.ilike(f"%{_escape_like(query.search)}%", escape="\\"),
                    BookModel.author.ilike(f"%{_escape_like(query.search)}%", escape="\\"),
                    BookModel.isbn.ilike(f"%{_escape_like(query.search)}%", escape="\\"),
                )
            )

    if query.sort_order == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    return stmt.offset(offset).limit(limit + 1)


def _build_list_reservations_query(
    query: ListReservationsQuery, sort_column, limit: int, offset: int
):
    stmt = select(ReservationModel)
    if query.user_id:
        stmt = stmt.where(ReservationModel.user_id == query.user_id)
    if query.status:
        stmt = stmt.where(ReservationModel.status == ReservationStatus(query.status))
    if query.book_id:
        stmt = stmt.where(ReservationModel.book_id == query.book_id)

    if query.sort_order == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    return stmt.offset(offset).limit(limit + 1)


class BookService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], cache: RedisCache):
        self._session_factory = session_factory
        self._cache = cache
        self._tracer = get_tracer("api-lab.book_service")
        self._db_circuit_breaker = CircuitBreaker(
            failure_threshold=5, recovery_timeout=30.0, name="db"
        )

    async def list_books(self, query: ListBooksQuery | None = None) -> PaginatedBooks:
        if query is None:
            query = ListBooksQuery()
        with self._tracer.start_as_current_span("BookService.list_books") as span:
            span.set_attribute("books.available_only", query.available_only)
            if query.genre:
                span.set_attribute("books.genre_filter", query.genre)
            if query.author:
                span.set_attribute("books.author_filter", query.author)
            if query.search:
                span.set_attribute("books.search_filter", query.search)

            limit = max(1, min(query.limit, 100))
            offset = _decode_continuation_token(query.continuation_token)

            cache_key = (
                f"books:all:{query.available_only}:{query.genre}:{query.author}:{query.search}"
                f":{limit}:{offset}:{query.sort_by}:{query.sort_order}"
            )
            cached = await self._cache.get(cache_key)
            if cached:
                cache_hits_total.labels(operation="list_books").inc()
                span.set_attribute("books.cache_hit", True)
                cached_result = PaginatedBooks(**cached)
                span.set_attribute("books.count", len(cached_result.items))
                return cached_result
            cache_misses_total.labels(operation="list_books").inc()
            span.set_attribute("books.cache_hit", False)

            sort_column = BOOK_SORT_COLUMNS.get(query.sort_by, BookModel.created_at)

            async def _db_op():
                async with self._session_factory() as session:
                    stmt = _build_list_books_query(query, sort_column, limit, offset)
                    db_result = await session.execute(stmt)
                    return db_result.scalars().all()

            with db_query_duration_seconds.labels(operation="list_books").time():
                books = await self._db_circuit_breaker.call(_db_op)

            has_more = len(books) > limit
            if has_more:
                books = books[:limit]

            next_token = _encode_continuation_token(offset + limit) if has_more else None
            items = [Book.model_validate(b) for b in books]

            paginated = PaginatedBooks(
                items=items, continuation_token=next_token, has_more=has_more
            )
            await self._cache.set(cache_key, paginated.model_dump(), BOOKS_ALL_TTL)
            span.set_attribute("books.count", len(items))
            return paginated

    async def get_book(self, book_id: uuid.UUID) -> Book | None:
        with self._tracer.start_as_current_span("BookService.get_book") as span:
            span.set_attribute("book.id", str(book_id))

            cache_key = f"books:{book_id}"
            cached = await self._cache.get(cache_key)
            if cached:
                cache_hits_total.labels(operation="get_book").inc()
                span.set_attribute("books.cache_hit", True)
                span.set_attribute("book.found", True)
                return Book(**cached)
            cache_misses_total.labels(operation="get_book").inc()
            span.set_attribute("books.cache_hit", False)

            async def _db_op():
                async with self._session_factory() as session:
                    db_result = await session.execute(
                        select(BookModel).where(BookModel.id == book_id)
                    )
                    return db_result.scalar_one_or_none()

            with db_query_duration_seconds.labels(operation="get_book").time():
                book = await self._db_circuit_breaker.call(_db_op)

            if not book:
                span.set_attribute("book.found", False)
                return None
            response = Book.model_validate(book)
            await self._cache.set(cache_key, response.model_dump(), BOOK_TTL)
            span.set_attribute("book.found", True)
            return response

    async def create_book(self, data: BookCreate) -> Book:
        with self._tracer.start_as_current_span("BookService.create_book") as span:
            span.set_attribute("book.isbn", data.isbn)
            span.set_attribute("book.title", data.title)
            span.set_attribute("book.total_copies", data.total_copies)

            async def _db_op():
                async with self._session_factory() as session:
                    new_book = BookModel(
                        isbn=data.isbn,
                        title=data.title,
                        author=data.author,
                        genre=data.genre,
                        published_year=data.published_year,
                        total_copies=data.total_copies,
                        available_copies=data.total_copies,
                        version=1,
                    )
                    session.add(new_book)
                    try:
                        await session.commit()
                    except IntegrityError as e:
                        await session.rollback()
                        if "isbn" in str(e.orig).lower() or "unique" in str(e.orig).lower():
                            raise DuplicateISBNError(data.isbn) from e
                        raise
                    await session.refresh(new_book)
                    return new_book

            with db_query_duration_seconds.labels(operation="create_book").time():
                book = await self._db_circuit_breaker.call(_db_op)

            books_created_total.inc()
            await self._cache.invalidate_books()
            await self._update_gauges()
            response = Book.model_validate(book)
            span.set_attribute("book.id", str(book.id))
            return response

    async def update_book(
        self, book_id: uuid.UUID, data: BookUpdate, expected_version: int | None = None
    ) -> Book | None:
        with self._tracer.start_as_current_span("BookService.update_book") as span:
            span.set_attribute("book.id", str(book_id))

            async def _db_op():
                async with self._session_factory() as session:
                    db_result = await session.execute(
                        select(BookModel).where(BookModel.id == book_id)
                    )
                    found_book = db_result.scalar_one_or_none()
                    if not found_book:
                        return None
                    if expected_version is not None and found_book.version != expected_version:
                        raise StaleVersionError(
                            f"Expected version {expected_version}, "
                            f"but current version is {found_book.version}"
                        )
                    update_data = data.model_dump(exclude_unset=True)
                    if "total_copies" in update_data:
                        diff = update_data["total_copies"] - found_book.total_copies
                        found_book.available_copies = max(0, found_book.available_copies + diff)
                    for field, value in update_data.items():
                        setattr(found_book, field, value)
                    found_book.version += 1
                    found_book.updated_at = datetime.now(UTC)
                    try:
                        await session.commit()
                    except IntegrityError as e:
                        await session.rollback()
                        if "isbn" in str(e.orig).lower() or "unique" in str(e.orig).lower():
                            raise DuplicateISBNError(update_data.get("isbn", "")) from e
                        raise
                    await session.refresh(found_book)
                    return found_book

            with db_query_duration_seconds.labels(operation="update_book").time():
                book = await self._db_circuit_breaker.call(_db_op)

            if not book:
                span.set_attribute("book.found", False)
                return None
            await self._cache.invalidate_books()
            await self._update_gauges()
            span.set_attribute("book.found", True)
            return Book.model_validate(book)

    async def delete_book(self, book_id: uuid.UUID) -> bool:
        with self._tracer.start_as_current_span("BookService.delete_book") as span:
            span.set_attribute("book.id", str(book_id))

            async def _db_op() -> bool:
                async with self._session_factory() as session:
                    db_result = await session.execute(
                        select(BookModel).where(BookModel.id == book_id)
                    )
                    found_book = db_result.scalar_one_or_none()
                    if not found_book:
                        return False

                    active_count_result = await session.execute(
                        select(func.count(ReservationModel.id)).where(
                            ReservationModel.book_id == book_id,
                            ReservationModel.status == ReservationStatus.ACTIVE,
                        )
                    )
                    active_count = active_count_result.scalar() or 0
                    if active_count > 0:
                        raise ActiveReservationsError

                    await session.delete(found_book)
                    await session.commit()
                    return True

            with db_query_duration_seconds.labels(operation="delete_book").time():
                found = await self._db_circuit_breaker.call(_db_op)

            if not found:
                span.set_attribute("book.found", False)
                return False
            await self._cache.invalidate_books()
            await self._update_gauges()
            span.set_attribute("book.found", True)
            return True

    async def reserve_books(self, data: ReservationCreate, user_id: uuid.UUID) -> list[Reservation]:
        with self._tracer.start_as_current_span("BookService.reserve_books") as span:
            span.set_attribute("reservation.user_id", str(user_id))
            span.set_attribute("reservation.book_count", len(data.book_ids))

            async def _db_op():
                async with self._session_factory() as session:
                    new_reservations = []
                    for bid in data.book_ids:
                        db_result = await session.execute(
                            select(BookModel).where(BookModel.id == bid).with_for_update()
                        )
                        found_book = db_result.scalar_one_or_none()
                        if not found_book:
                            raise ValueError(f"Book {bid} not found")
                        if found_book.available_copies <= 0:
                            raise ValueError(
                                f"Book '{found_book.title}' is not available for reservation"
                            )
                        found_book.available_copies -= 1
                        new_reservation = ReservationModel(
                            book_id=bid,
                            user_id=user_id,
                            due_date=datetime.now(UTC) + timedelta(days=LOAN_DURATION_DAYS),
                            status=ReservationStatus.ACTIVE,
                        )
                        session.add(new_reservation)
                        new_reservations.append(new_reservation)
                    await session.commit()
                    for r in new_reservations:
                        await session.refresh(r)
                    return new_reservations

            with db_query_duration_seconds.labels(operation="reserve_books").time():
                reservations = await self._db_circuit_breaker.call(_db_op)

            reservations_created_total.inc(len(reservations))
            await self._cache.invalidate_books()
            await self._update_gauges()
            responses = [Reservation.model_validate(r) for r in reservations]
            span.set_attribute("books.count", len(responses))
            return responses

    async def return_reservation(self, reservation_id: uuid.UUID) -> Reservation | None:
        with self._tracer.start_as_current_span("BookService.return_reservation") as span:
            span.set_attribute("reservation.id", str(reservation_id))

            async def _db_op():
                async with self._session_factory() as session:
                    db_result = await session.execute(
                        select(ReservationModel).where(ReservationModel.id == reservation_id)
                    )
                    found_reservation = db_result.scalar_one_or_none()
                    if not found_reservation:
                        return None
                    if found_reservation.status != ReservationStatus.ACTIVE:
                        raise ValueError(f"Reservation is already {found_reservation.status.value}")
                    found_reservation.status = ReservationStatus.RETURNED
                    found_reservation.returned_at = datetime.now(UTC)
                    book_result = await session.execute(
                        select(BookModel)
                        .where(BookModel.id == found_reservation.book_id)
                        .with_for_update()
                    )
                    found_book = book_result.scalar_one()
                    found_book.available_copies += 1
                    await session.commit()
                    await session.refresh(found_reservation)
                    return found_reservation

            with db_query_duration_seconds.labels(operation="return_reservation").time():
                reservation = await self._db_circuit_breaker.call(_db_op)

            if not reservation:
                span.set_attribute("book.found", False)
                return None
            reservations_returned_total.inc()
            await self._cache.invalidate_books()
            await self._update_gauges()
            span.set_attribute("book.found", True)
            return Reservation.model_validate(reservation)

    async def list_reservations(
        self, query: ListReservationsQuery | None = None
    ) -> PaginatedReservations:
        if query is None:
            query = ListReservationsQuery()
        with self._tracer.start_as_current_span("BookService.list_reservations") as span:
            if query.user_id:
                span.set_attribute("reservation.user_id_filter", str(query.user_id))
            if query.status:
                span.set_attribute("reservation.status_filter", query.status)
            if query.book_id:
                span.set_attribute("book.id", str(query.book_id))

            limit = max(1, min(query.limit, 100))
            offset = _decode_continuation_token(query.continuation_token)

            sort_column = RESERVATION_SORT_COLUMNS.get(query.sort_by, ReservationModel.reserved_at)

            async def _db_op():
                async with self._session_factory() as session:
                    stmt = _build_list_reservations_query(query, sort_column, limit, offset)
                    db_result = await session.execute(stmt)
                    return db_result.scalars().all()

            with db_query_duration_seconds.labels(operation="list_reservations").time():
                reservations = await self._db_circuit_breaker.call(_db_op)

            has_more = len(reservations) > limit
            if has_more:
                reservations = reservations[:limit]

            next_token = _encode_continuation_token(offset + limit) if has_more else None
            items = [Reservation.model_validate(r) for r in reservations]

            span.set_attribute("books.count", len(items))
            return PaginatedReservations(
                items=items, continuation_token=next_token, has_more=has_more
            )

    async def get_reservation(self, reservation_id: uuid.UUID) -> Reservation | None:
        with self._tracer.start_as_current_span("BookService.get_reservation") as span:
            span.set_attribute("reservation.id", str(reservation_id))

            async def _db_op():
                async with self._session_factory() as session:
                    db_result = await session.execute(
                        select(ReservationModel).where(ReservationModel.id == reservation_id)
                    )
                    return db_result.scalar_one_or_none()

            with db_query_duration_seconds.labels(operation="get_reservation").time():
                reservation = await self._db_circuit_breaker.call(_db_op)

            if not reservation:
                span.set_attribute("book.found", False)
                return None
            span.set_attribute("book.found", True)
            return Reservation.model_validate(reservation)

    async def _update_gauges(self) -> None:
        try:

            async def _db_op() -> None:
                async with self._session_factory() as session:
                    db_result = await session.execute(select(func.sum(BookModel.available_copies)))
                    total_available = db_result.scalar() or 0
                    books_available_gauge.set(total_available)

                    db_result = await session.execute(
                        select(func.count(ReservationModel.id)).where(
                            ReservationModel.status == ReservationStatus.ACTIVE
                        )
                    )
                    active_count = db_result.scalar() or 0
                    active_reservations_gauge.set(active_count)

            await self._db_circuit_breaker.call(_db_op)
        except Exception:
            logger.debug("Failed to update metric gauges", exc_info=True)
