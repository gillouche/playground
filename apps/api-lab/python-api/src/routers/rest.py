import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from generated.models import (
    BookCreate,
    BookResponse,
    BookUpdate,
    InventoryResponse,
    ReservationCreate,
    ReservationResponse,
)
from services.book_service import BookService

router = APIRouter(prefix="/api/v1", tags=["library"])

# These will be set during app startup
_book_service: BookService | None = None


def set_book_service(service: BookService):
    global _book_service  # noqa: PLW0603
    _book_service = service


def get_book_service() -> BookService:
    if _book_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _book_service


@router.get("/books", response_model=list[BookResponse])
async def list_books(
    available_only: bool = Query(False),
    genre: str | None = Query(None),
    author: str | None = Query(None),
    search: str | None = Query(None),
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    return await service.list_books(
        available_only=available_only, genre=genre, author=author, search=search
    )


@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: uuid.UUID,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    book = await service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("/books", response_model=BookResponse, status_code=201)
async def create_book(
    data: BookCreate,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    return await service.create_book(data)


@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: uuid.UUID,
    data: BookUpdate,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    book = await service.update_book(book_id, data)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.delete("/books/{book_id}", status_code=204)
async def delete_book(
    book_id: uuid.UUID,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    deleted = await service.delete_book(book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found")


@router.get("/inventory", response_model=InventoryResponse)
async def get_inventory(
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    books = await service.get_inventory()
    return InventoryResponse(items=books)


@router.post("/reservations", response_model=list[ReservationResponse], status_code=201)
async def reserve_books(
    data: ReservationCreate,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    try:
        return await service.reserve_books(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/reservations/{reservation_id}/return", response_model=ReservationResponse)
async def return_reservation(
    reservation_id: uuid.UUID,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    try:
        reservation = await service.return_reservation(reservation_id)
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/reservations", response_model=list[ReservationResponse])
async def list_reservations(
    user_id: str | None = Query(None),
    status: str | None = Query(None),
    book_id: uuid.UUID | None = Query(None),  # noqa: B008
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    return await service.list_reservations(user_id=user_id, status=status, book_id=book_id)


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: uuid.UUID,
    service: BookService = Depends(get_book_service),  # noqa: B008
):
    reservation = await service.get_reservation(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation
