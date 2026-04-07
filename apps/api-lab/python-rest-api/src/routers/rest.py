import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Response
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
    ReservationUpdate,
)
from services.book_service import (
    ActiveReservationsError,
    BookService,
    DuplicateISBNError,
    StaleVersionError,
)

router = APIRouter(prefix="/api/v1", tags=["library"])

_book_service: BookService | None = None


def set_book_service(service: BookService):
    global _book_service  # noqa: PLW0603
    _book_service = service


def get_book_service() -> BookService:
    if _book_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _book_service


@router.get("/books", response_model=PaginatedBooks)
async def list_books(
    query: ListBooksQuery = Depends(),  # noqa: B008
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    return await service.list_books(query)


@router.get("/books/{book_id}", response_model=Book)
async def get_book(
    book_id: uuid.UUID,
    response: Response,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    book = await service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    response.headers["ETag"] = f'"{book.version}"'
    return book


@router.post("/books", response_model=Book, status_code=201)
async def create_book(
    data: BookCreate,
    response: Response,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    try:
        book = await service.create_book(data)
    except DuplicateISBNError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    response.headers["Location"] = f"/api/v1/books/{book.id}"
    response.headers["ETag"] = f'"{book.version}"'
    return book


@router.put("/books/{book_id}", response_model=Book)
async def update_book(
    book_id: uuid.UUID,
    data: BookUpdate,
    response: Response,
    if_match: str = Header(...),
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    expected_version = int(if_match.strip('"'))
    try:
        book = await service.update_book(book_id, data, expected_version=expected_version)
    except DuplicateISBNError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except StaleVersionError as e:
        raise HTTPException(status_code=412, detail=str(e)) from e
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    response.headers["ETag"] = f'"{book.version}"'
    return book


@router.delete("/books/{book_id}", status_code=204)
async def delete_book(
    book_id: uuid.UUID,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    try:
        deleted = await service.delete_book(book_id)
    except ActiveReservationsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found")


@router.post("/reservations", response_model=list[Reservation], status_code=201)
async def reserve_books(
    data: ReservationCreate,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    try:
        return await service.reserve_books(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.patch("/reservations/{reservation_id}", response_model=Reservation)
async def return_reservation(
    reservation_id: uuid.UUID,
    data: ReservationUpdate,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    from generated.models import ReservationStatus

    if data.status != ReservationStatus.RETURNED:
        raise HTTPException(status_code=400, detail="Only status=RETURNED is supported")
    try:
        reservation = await service.return_reservation(reservation_id)
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/reservations", response_model=PaginatedReservations)
async def list_reservations(
    query: ListReservationsQuery = Depends(),  # noqa: B008
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    return await service.list_reservations(query)


@router.get("/reservations/{reservation_id}", response_model=Reservation)
async def get_reservation(
    reservation_id: uuid.UUID,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    reservation = await service.get_reservation(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation
