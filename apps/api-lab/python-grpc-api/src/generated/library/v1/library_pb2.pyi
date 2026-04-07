import datetime

from google.protobuf import field_mask_pb2 as _field_mask_pb2
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

class BookSortField(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BOOK_SORT_FIELD_UNSPECIFIED: _ClassVar[BookSortField]
    BOOK_SORT_FIELD_TITLE: _ClassVar[BookSortField]
    BOOK_SORT_FIELD_AUTHOR: _ClassVar[BookSortField]
    BOOK_SORT_FIELD_PUBLISHED_YEAR: _ClassVar[BookSortField]
    BOOK_SORT_FIELD_CREATED_AT: _ClassVar[BookSortField]

class ReservationSortField(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESERVATION_SORT_FIELD_UNSPECIFIED: _ClassVar[ReservationSortField]
    RESERVATION_SORT_FIELD_RESERVED_AT: _ClassVar[ReservationSortField]
    RESERVATION_SORT_FIELD_DUE_DATE: _ClassVar[ReservationSortField]
    RESERVATION_SORT_FIELD_STATUS: _ClassVar[ReservationSortField]

class SortOrder(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SORT_ORDER_UNSPECIFIED: _ClassVar[SortOrder]
    SORT_ORDER_ASC: _ClassVar[SortOrder]
    SORT_ORDER_DESC: _ClassVar[SortOrder]
RESERVATION_STATUS_UNSPECIFIED: ReservationStatus
RESERVATION_STATUS_ACTIVE: ReservationStatus
RESERVATION_STATUS_RETURNED: ReservationStatus
RESERVATION_STATUS_OVERDUE: ReservationStatus
BOOK_SORT_FIELD_UNSPECIFIED: BookSortField
BOOK_SORT_FIELD_TITLE: BookSortField
BOOK_SORT_FIELD_AUTHOR: BookSortField
BOOK_SORT_FIELD_PUBLISHED_YEAR: BookSortField
BOOK_SORT_FIELD_CREATED_AT: BookSortField
RESERVATION_SORT_FIELD_UNSPECIFIED: ReservationSortField
RESERVATION_SORT_FIELD_RESERVED_AT: ReservationSortField
RESERVATION_SORT_FIELD_DUE_DATE: ReservationSortField
RESERVATION_SORT_FIELD_STATUS: ReservationSortField
SORT_ORDER_UNSPECIFIED: SortOrder
SORT_ORDER_ASC: SortOrder
SORT_ORDER_DESC: SortOrder

class Book(_message.Message):
    __slots__ = ("id", "isbn", "title", "author", "genre", "published_year", "total_copies", "available_copies", "created_at", "updated_at", "version")
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
    VERSION_FIELD_NUMBER: _ClassVar[int]
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
    version: int
    def __init__(self, id: _Optional[str] = ..., isbn: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ..., genre: _Optional[str] = ..., published_year: _Optional[int] = ..., total_copies: _Optional[int] = ..., available_copies: _Optional[int] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., version: _Optional[int] = ...) -> None: ...

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
    __slots__ = ("available_only", "genre", "author", "search", "page_size", "page_token", "sort_by", "sort_order")
    AVAILABLE_ONLY_FIELD_NUMBER: _ClassVar[int]
    GENRE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    SEARCH_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    SORT_BY_FIELD_NUMBER: _ClassVar[int]
    SORT_ORDER_FIELD_NUMBER: _ClassVar[int]
    available_only: bool
    genre: str
    author: str
    search: str
    page_size: int
    page_token: str
    sort_by: BookSortField
    sort_order: SortOrder
    def __init__(self, available_only: bool = ..., genre: _Optional[str] = ..., author: _Optional[str] = ..., search: _Optional[str] = ..., page_size: _Optional[int] = ..., page_token: _Optional[str] = ..., sort_by: _Optional[_Union[BookSortField, str]] = ..., sort_order: _Optional[_Union[SortOrder, str]] = ...) -> None: ...

class ListBooksResponse(_message.Message):
    __slots__ = ("books", "next_page_token")
    BOOKS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    books: _containers.RepeatedCompositeFieldContainer[Book]
    next_page_token: str
    def __init__(self, books: _Optional[_Iterable[_Union[Book, _Mapping]]] = ..., next_page_token: _Optional[str] = ...) -> None: ...

class GetBookRequest(_message.Message):
    __slots__ = ("book_id",)
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    book_id: str
    def __init__(self, book_id: _Optional[str] = ...) -> None: ...

class CreateBookRequest(_message.Message):
    __slots__ = ("isbn", "title", "author", "genre", "published_year", "total_copies", "idempotency_key")
    ISBN_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    GENRE_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_YEAR_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COPIES_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    isbn: str
    title: str
    author: str
    genre: str
    published_year: int
    total_copies: int
    idempotency_key: str
    def __init__(self, isbn: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ..., genre: _Optional[str] = ..., published_year: _Optional[int] = ..., total_copies: _Optional[int] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

class UpdateBookRequest(_message.Message):
    __slots__ = ("book_id", "isbn", "title", "author", "genre", "published_year", "total_copies", "update_mask", "expected_version")
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    ISBN_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    GENRE_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_YEAR_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COPIES_FIELD_NUMBER: _ClassVar[int]
    UPDATE_MASK_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_VERSION_FIELD_NUMBER: _ClassVar[int]
    book_id: str
    isbn: str
    title: str
    author: str
    genre: str
    published_year: int
    total_copies: int
    update_mask: _field_mask_pb2.FieldMask
    expected_version: int
    def __init__(self, book_id: _Optional[str] = ..., isbn: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ..., genre: _Optional[str] = ..., published_year: _Optional[int] = ..., total_copies: _Optional[int] = ..., update_mask: _Optional[_Union[_field_mask_pb2.FieldMask, _Mapping]] = ..., expected_version: _Optional[int] = ...) -> None: ...

class DeleteBookRequest(_message.Message):
    __slots__ = ("book_id",)
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    book_id: str
    def __init__(self, book_id: _Optional[str] = ...) -> None: ...

class DeleteBookResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ReserveBooksRequest(_message.Message):
    __slots__ = ("user_id", "book_ids", "idempotency_key")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    BOOK_IDS_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    book_ids: _containers.RepeatedScalarFieldContainer[str]
    idempotency_key: str
    def __init__(self, user_id: _Optional[str] = ..., book_ids: _Optional[_Iterable[str]] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

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
    __slots__ = ("user_id", "status", "book_id", "page_size", "page_token", "sort_by", "sort_order")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    BOOK_ID_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    SORT_BY_FIELD_NUMBER: _ClassVar[int]
    SORT_ORDER_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    status: ReservationStatus
    book_id: str
    page_size: int
    page_token: str
    sort_by: ReservationSortField
    sort_order: SortOrder
    def __init__(self, user_id: _Optional[str] = ..., status: _Optional[_Union[ReservationStatus, str]] = ..., book_id: _Optional[str] = ..., page_size: _Optional[int] = ..., page_token: _Optional[str] = ..., sort_by: _Optional[_Union[ReservationSortField, str]] = ..., sort_order: _Optional[_Union[SortOrder, str]] = ...) -> None: ...

class ListReservationsResponse(_message.Message):
    __slots__ = ("reservations", "next_page_token")
    RESERVATIONS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    reservations: _containers.RepeatedCompositeFieldContainer[Reservation]
    next_page_token: str
    def __init__(self, reservations: _Optional[_Iterable[_Union[Reservation, _Mapping]]] = ..., next_page_token: _Optional[str] = ...) -> None: ...

class GetReservationRequest(_message.Message):
    __slots__ = ("reservation_id",)
    RESERVATION_ID_FIELD_NUMBER: _ClassVar[int]
    reservation_id: str
    def __init__(self, reservation_id: _Optional[str] = ...) -> None: ...
