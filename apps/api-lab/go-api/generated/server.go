// Code generated from openapi.yaml - DO NOT EDIT.

package generated

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"github.com/google/uuid"
)

// ListBooksParams holds query parameters for the ListBooks operation.
type ListBooksParams struct {
	AvailableOnly bool
	Genre         *string
	Author        *string
	Search        *string
}

// ListReservationsParams holds query parameters for the ListReservations operation.
type ListReservationsParams struct {
	UserID *string
	Status *string
	BookID *string
}

// ServerInterface defines the handler methods for the Library API.
type ServerInterface interface {
	ListBooks(ctx context.Context, params ListBooksParams) ([]BookResponse, error)
	CreateBook(ctx context.Context, body BookCreate) (*BookResponse, error)
	GetBook(ctx context.Context, bookID uuid.UUID) (*BookResponse, error)
	UpdateBook(ctx context.Context, bookID uuid.UUID, body BookUpdate) (*BookResponse, error)
	DeleteBook(ctx context.Context, bookID uuid.UUID) error
	GetInventory(ctx context.Context) (*InventoryResponse, error)
	CreateReservations(ctx context.Context, body ReservationCreate) ([]ReservationResponse, error)
	ListReservations(ctx context.Context, params ListReservationsParams) ([]ReservationResponse, error)
	GetReservation(ctx context.Context, reservationID uuid.UUID) (*ReservationResponse, error)
	ReturnReservation(ctx context.Context, reservationID uuid.UUID) (*ReservationResponse, error)
	HealthCheck(ctx context.Context) (*HealthResponse, error)
	ReadinessCheck(ctx context.Context) (*HealthResponse, error)
	ServiceInfo(ctx context.Context) (*InfoResponse, error)
}

// RegisterRoutes wires up all API routes to the given ServeMux using the ServerInterface.
func RegisterRoutes(mux *http.ServeMux, si ServerInterface) {
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		resp, err := si.HealthCheck(r.Context())
		if err != nil {
			handleServerError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, resp)
	})

	mux.HandleFunc("/ready", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		resp, err := si.ReadinessCheck(r.Context())
		if err != nil {
			handleServerError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, resp)
	})

	mux.HandleFunc("/info", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		resp, err := si.ServiceInfo(r.Context())
		if err != nil {
			handleServerError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, resp)
	})

	mux.HandleFunc("/api/v1/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			params := ListBooksParams{
				AvailableOnly: r.URL.Query().Get("available_only") == "true",
				Genre:         queryParam(r, "genre"),
				Author:        queryParam(r, "author"),
				Search:        queryParam(r, "search"),
			}
			resp, err := si.ListBooks(r.Context(), params)
			if err != nil {
				handleServerError(w, err)
				return
			}
			writeJSON(w, http.StatusOK, resp)

		case http.MethodPost:
			var body BookCreate
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				writeError(w, http.StatusBadRequest, "invalid request body")
				return
			}
			resp, err := si.CreateBook(r.Context(), body)
			if err != nil {
				handleServerError(w, err)
				return
			}
			writeJSON(w, http.StatusCreated, resp)

		default:
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	})

	mux.HandleFunc("/api/v1/books/", func(w http.ResponseWriter, r *http.Request) {
		// Extract book_id from path: /api/v1/books/{book_id}
		path := strings.TrimPrefix(r.URL.Path, "/api/v1/books/")
		if path == "" {
			writeError(w, http.StatusBadRequest, "missing book_id")
			return
		}

		bookID, err := uuid.Parse(path)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid book_id: must be a valid UUID")
			return
		}

		switch r.Method {
		case http.MethodGet:
			resp, err := si.GetBook(r.Context(), bookID)
			if err != nil {
				handleServerError(w, err)
				return
			}
			writeJSON(w, http.StatusOK, resp)

		case http.MethodPut:
			var body BookUpdate
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				writeError(w, http.StatusBadRequest, "invalid request body")
				return
			}
			resp, err := si.UpdateBook(r.Context(), bookID, body)
			if err != nil {
				handleServerError(w, err)
				return
			}
			writeJSON(w, http.StatusOK, resp)

		case http.MethodDelete:
			if err := si.DeleteBook(r.Context(), bookID); err != nil {
				handleServerError(w, err)
				return
			}
			w.WriteHeader(http.StatusNoContent)

		default:
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	})

	mux.HandleFunc("/api/v1/inventory", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		resp, err := si.GetInventory(r.Context())
		if err != nil {
			handleServerError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, resp)
	})

	mux.HandleFunc("/api/v1/reservations", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost:
			var body ReservationCreate
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				writeError(w, http.StatusBadRequest, "invalid request body")
				return
			}
			resp, err := si.CreateReservations(r.Context(), body)
			if err != nil {
				handleServerError(w, err)
				return
			}
			writeJSON(w, http.StatusCreated, resp)

		case http.MethodGet:
			params := ListReservationsParams{
				UserID: queryParam(r, "user_id"),
				Status: queryParam(r, "status"),
				BookID: queryParam(r, "book_id"),
			}
			resp, err := si.ListReservations(r.Context(), params)
			if err != nil {
				handleServerError(w, err)
				return
			}
			writeJSON(w, http.StatusOK, resp)

		default:
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	})

	mux.HandleFunc("/api/v1/reservations/", func(w http.ResponseWriter, r *http.Request) {
		// Path: /api/v1/reservations/{id} or /api/v1/reservations/{id}/return
		path := strings.TrimPrefix(r.URL.Path, "/api/v1/reservations/")
		if path == "" {
			writeError(w, http.StatusBadRequest, "missing reservation id")
			return
		}

		parts := strings.SplitN(path, "/", 2)
		reservationID, err := uuid.Parse(parts[0])
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid reservation id: must be a valid UUID")
			return
		}

		// Check for /return sub-path
		if len(parts) == 2 && parts[1] == "return" {
			if r.Method != http.MethodPost {
				writeError(w, http.StatusMethodNotAllowed, "method not allowed")
				return
			}
			resp, err := si.ReturnReservation(r.Context(), reservationID)
			if err != nil {
				handleServerError(w, err)
				return
			}
			writeJSON(w, http.StatusOK, resp)
			return
		}

		// GET /api/v1/reservations/{id}
		if r.Method != http.MethodGet {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}
		resp, err := si.GetReservation(r.Context(), reservationID)
		if err != nil {
			handleServerError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, resp)
	})
}

// APIError allows server implementations to control HTTP status codes.
type APIError struct {
	StatusCode int
	Message    string
}

func (e *APIError) Error() string {
	return e.Message
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		// Response already started, log would be appropriate here.
		_ = err
	}
}

func writeError(w http.ResponseWriter, status int, detail string) {
	writeJSON(w, status, ErrorResponse{
		Detail:     detail,
		StatusCode: status,
	})
}

func handleServerError(w http.ResponseWriter, err error) {
	var apiErr *APIError
	if errors.As(err, &apiErr) {
		writeError(w, apiErr.StatusCode, apiErr.Message)
		return
	}
	writeError(w, http.StatusInternalServerError, err.Error())
}

func queryParam(r *http.Request, name string) *string {
	v := r.URL.Query().Get(name)
	if v == "" {
		return nil
	}
	return &v
}
