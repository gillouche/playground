import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ReservationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESERVATION_STATUS_UNSPECIFIED: _ClassVar[ReservationStatus]
    RESERVATION_STATUS_ACTIVE: _ClassVar[ReservationStatus]
    RESERVATION_STATUS_RETURNED: _ClassVar[ReservationStatus]
    RESERVATION_STATUS_OVERDUE: _ClassVar[ReservationStatus]
RESERVATION_STATUS_UNSPECIFIED: ReservationStatus
RESERVATION_STATUS_ACTIVE: ReservationStatus
RESERVATION_STATUS_RETURNED: ReservationStatus
RESERVATION_STATUS_OVERDUE: ReservationStatus

class Book(_message.Message):
    __slots__ = ("id", "isbn", "title", "author", "genre", "published_year", "total_copies", "available_copies", "created_at", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    ISBN_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    GENRE_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_YEAR_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COPIES_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_COPIES_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    isbn: str
    title: str
    author: str
    genre: str
    published_year: int
    total_copies: int
    available_copies: int
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., isbn: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ..., genre: _Optional[str] = ..., published_year: _Optional[int] = ..., total_copies: _Optional[int] = ..., available_copies: _Optional[int] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class Reservation(_message.Message):
    __slots__ = ("id", "book_id", "user_id", "reserved_at", "due_date", "returned_at", "status")
    ID_FIELD_NUMBER: _ClassVar[int]
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    RESERVED_AT_FIELD_NUMBER: _ClassVar[int]
    DUE_DATE_FIELD_NUMBER: _ClassVar[int]
    RETURNED_AT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    id: str
    book_id: str
    user_id: str
    reserved_at: _timestamp_pb2.Timestamp
    due_date: _timestamp_pb2.Timestamp
    returned_at: _timestamp_pb2.Timestamp
    status: ReservationStatus
    def __init__(self, id: _Optional[str] = ..., book_id: _Optional[str] = ..., user_id: _Optional[str] = ..., reserved_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., due_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., returned_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., status: _Optional[_Union[ReservationStatus, str]] = ...) -> None: ...

class ListBooksRequest(_message.Message):
    __slots__ = ("available_only", "genre", "author", "search")
    AVAILABLE_ONLY_FIELD_NUMBER: _ClassVar[int]
    GENRE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    available_only: bool
    genre: str
    author: str
    search: str
    def __init__(self, available_only: bool = ..., genre: _Optional[str] = ..., author: _Optional[str] = ..., search: _Optional[str] = ...) -> None: ...

class ListBooksResponse(_message.Message):
    __slots__ = ("books",)
    BOOKS_FIELD_NUMBER: _ClassVar[int]
    books: _containers.RepeatedCompositeFieldContainer[Book]
    def __init__(self, books: _Optional[_Iterable[_Union[Book, _Mapping]]] = ...) -> None: ...

class GetBookRequest(_message.Message):
    __slots__ = ("book_id",)
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    book_id: str
    def __init__(self, book_id: _Optional[str] = ...) -> None: ...

class CreateBookRequest(_message.Message):
    __slots__ = ("isbn", "title", "author", "genre", "published_year", "total_copies")
    ISBN_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    GENRE_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_YEAR_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COPIES_FIELD_NUMBER: _ClassVar[int]
    isbn: str
    title: str
    author: str
    genre: str
    published_year: int
    total_copies: int
    def __init__(self, isbn: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ..., genre: _Optional[str] = ..., published_year: _Optional[int] = ..., total_copies: _Optional[int] = ...) -> None: ...

class UpdateBookRequest(_message.Message):
    __slots__ = ("book_id", "isbn", "title", "author", "genre", "published_year", "total_copies")
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    ISBN_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    GENRE_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_YEAR_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COPIES_FIELD_NUMBER: _ClassVar[int]
    book_id: str
    isbn: str
    title: str
    author: str
    genre: str
    published_year: int
    total_copies: int
    def __init__(self, book_id: _Optional[str] = ..., isbn: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ..., genre: _Optional[str] = ..., published_year: _Optional[int] = ..., total_copies: _Optional[int] = ...) -> None: ...

class DeleteBookRequest(_message.Message):
    __slots__ = ("book_id",)
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    book_id: str
    def __init__(self, book_id: _Optional[str] = ...) -> None: ...

class DeleteBookResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetInventoryRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetInventoryResponse(_message.Message):
    __slots__ = ("books",)
    BOOKS_FIELD_NUMBER: _ClassVar[int]
    books: _containers.RepeatedCompositeFieldContainer[Book]
    def __init__(self, books: _Optional[_Iterable[_Union[Book, _Mapping]]] = ...) -> None: ...

class ReserveBooksRequest(_message.Message):
    __slots__ = ("user_id", "book_ids")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    BOOK_IDS_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    book_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, user_id: _Optional[str] = ..., book_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class ReserveBooksResponse(_message.Message):
    __slots__ = ("reservations",)
    RESERVATIONS_FIELD_NUMBER: _ClassVar[int]
    reservations: _containers.RepeatedCompositeFieldContainer[Reservation]
    def __init__(self, reservations: _Optional[_Iterable[_Union[Reservation, _Mapping]]] = ...) -> None: ...

class ReturnReservationRequest(_message.Message):
    __slots__ = ("reservation_id",)
    RESERVATION_ID_FIELD_NUMBER: _ClassVar[int]
    reservation_id: str
    def __init__(self, reservation_id: _Optional[str] = ...) -> None: ...

class ListReservationsRequest(_message.Message):
    __slots__ = ("user_id", "status", "book_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    status: str
    book_id: str
    def __init__(self, user_id: _Optional[str] = ..., status: _Optional[str] = ..., book_id: _Optional[str] = ...) -> None: ...

class ListReservationsResponse(_message.Message):
    __slots__ = ("reservations",)
    RESERVATIONS_FIELD_NUMBER: _ClassVar[int]
    reservations: _containers.RepeatedCompositeFieldContainer[Reservation]
    def __init__(self, reservations: _Optional[_Iterable[_Union[Reservation, _Mapping]]] = ...) -> None: ...

class GetReservationRequest(_message.Message):
    __slots__ = ("reservation_id",)
    RESERVATION_ID_FIELD_NUMBER: _ClassVar[int]
    reservation_id: str
    def __init__(self, reservation_id: _Optional[str] = ...) -> None: ...
