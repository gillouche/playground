// Code generated from openapi.yaml - DO NOT EDIT.

package generated

import (
	"time"

	"github.com/google/uuid"
)

// ReservationStatus represents the status of a reservation.
type ReservationStatus string

const (
	ReservationStatusActive   ReservationStatus = "ACTIVE"
	ReservationStatusReturned ReservationStatus = "RETURNED"
	ReservationStatusOverdue  ReservationStatus = "OVERDUE"
)

// Book represents a library book entity.
type Book struct {
	ID              uuid.UUID `json:"id"`
	ISBN            string    `json:"isbn"`
	Title           string    `json:"title"`
	Author          string    `json:"author"`
	Genre           string    `json:"genre"`
	PublishedYear   int       `json:"published_year"`
	TotalCopies     int       `json:"total_copies"`
	AvailableCopies int       `json:"available_copies"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
}

// BookCreate represents the request body for creating a book.
type BookCreate struct {
	ISBN          string `json:"isbn"`
	Title         string `json:"title"`
	Author        string `json:"author"`
	Genre         string `json:"genre"`
	PublishedYear int    `json:"published_year"`
	TotalCopies   int    `json:"total_copies"`
}

// BookUpdate represents the request body for updating a book.
type BookUpdate struct {
	ISBN          *string `json:"isbn,omitempty"`
	Title         *string `json:"title,omitempty"`
	Author        *string `json:"author,omitempty"`
	Genre         *string `json:"genre,omitempty"`
	PublishedYear *int    `json:"published_year,omitempty"`
	TotalCopies   *int    `json:"total_copies,omitempty"`
}

// BookResponse is the API response for a book (same as Book).
type BookResponse = Book

// Reservation represents a book reservation.
type Reservation struct {
	ID         uuid.UUID         `json:"id"`
	BookID     uuid.UUID         `json:"book_id"`
	UserID     string            `json:"user_id"`
	ReservedAt time.Time         `json:"reserved_at"`
	DueDate    time.Time         `json:"due_date"`
	ReturnedAt *time.Time        `json:"returned_at,omitempty"`
	Status     ReservationStatus `json:"status"`
}

// ReservationCreate represents the request body for creating reservations.
type ReservationCreate struct {
	UserID  string      `json:"user_id"`
	BookIDs []uuid.UUID `json:"book_ids"`
}

// ReservationResponse is the API response for a reservation (same as Reservation).
type ReservationResponse = Reservation

// InventoryResponse represents the inventory listing.
type InventoryResponse struct {
	Items []Book `json:"items"`
}

// ErrorResponse represents an API error.
type ErrorResponse struct {
	Detail     string `json:"detail"`
	StatusCode int    `json:"status_code"`
}

// HealthResponse represents a health/readiness check response.
type HealthResponse struct {
	Status string `json:"status"`
}

// InfoResponse represents service information.
type InfoResponse struct {
	Hostname    string `json:"hostname,omitempty"`
	AppVersion  string `json:"app_version,omitempty"`
	Environment string `json:"environment,omitempty"`
	App         string `json:"app,omitempty"`
	Component   string `json:"component,omitempty"`
	Node        string `json:"node,omitempty"`
	PodIP       string `json:"pod_ip,omitempty"`
	LogLevel    string `json:"log_level,omitempty"`
	GitTag      string `json:"git_tag,omitempty"`
	GitCommit   string `json:"git_commit,omitempty"`
}
