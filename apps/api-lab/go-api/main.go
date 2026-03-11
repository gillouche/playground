// Package main implements the Go API skeleton for the api-lab library management system.
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/gillouche/playground/apps/api-lab/go-api/generated"
	"github.com/google/uuid"
)

// libraryServer implements generated.ServerInterface.
type libraryServer struct{}

var errNotImplemented = &generated.APIError{
	StatusCode: http.StatusNotImplemented,
	Message:    "not implemented",
}

func (s *libraryServer) ListBooks(_ context.Context, _ generated.ListBooksParams) ([]generated.BookResponse, error) {
	return nil, errNotImplemented
}

func (s *libraryServer) CreateBook(_ context.Context, _ generated.BookCreate) (*generated.BookResponse, error) {
	return nil, errNotImplemented
}

func (s *libraryServer) GetBook(_ context.Context, _ uuid.UUID) (*generated.BookResponse, error) {
	return nil, errNotImplemented
}

func (s *libraryServer) UpdateBook(_ context.Context, _ uuid.UUID, _ generated.BookUpdate) (*generated.BookResponse, error) {
	return nil, errNotImplemented
}

func (s *libraryServer) DeleteBook(_ context.Context, _ uuid.UUID) error {
	return errNotImplemented
}

func (s *libraryServer) GetInventory(_ context.Context) (*generated.InventoryResponse, error) {
	return nil, errNotImplemented
}

func (s *libraryServer) CreateReservations(_ context.Context, _ generated.ReservationCreate) ([]generated.ReservationResponse, error) {
	return nil, errNotImplemented
}

func (s *libraryServer) ListReservations(_ context.Context, _ generated.ListReservationsParams) ([]generated.ReservationResponse, error) {
	return nil, errNotImplemented
}

func (s *libraryServer) GetReservation(_ context.Context, _ uuid.UUID) (*generated.ReservationResponse, error) {
	return nil, errNotImplemented
}

func (s *libraryServer) ReturnReservation(_ context.Context, _ uuid.UUID) (*generated.ReservationResponse, error) {
	return nil, errNotImplemented
}

func (s *libraryServer) HealthCheck(_ context.Context) (*generated.HealthResponse, error) {
	return &generated.HealthResponse{Status: "ok"}, nil
}

func (s *libraryServer) ReadinessCheck(_ context.Context) (*generated.HealthResponse, error) {
	// TODO: Check PostgreSQL connection (pgx/v5)
	// TODO: Check Redis connection (go-redis/v9)
	return &generated.HealthResponse{Status: "ready"}, nil
}

func (s *libraryServer) ServiceInfo(_ context.Context) (*generated.InfoResponse, error) {
	hostname, _ := os.Hostname() //nolint:errcheck // best-effort hostname
	return &generated.InfoResponse{
		Hostname:    hostname,
		AppVersion:  os.Getenv("APP_VERSION"),
		Environment: os.Getenv("ENVIRONMENT"),
		App:         os.Getenv("APP"),
		Component:   os.Getenv("COMPONENT"),
		Node:        os.Getenv("NODE_NAME"),
		PodIP:       os.Getenv("POD_IP"),
		LogLevel:    getEnvDefault("LOG_LEVEL", "INFO"),
		GitTag:      os.Getenv("GIT_TAG"),
		GitCommit:   os.Getenv("GIT_COMMIT"),
	}, nil
}

func main() {
	mux := http.NewServeMux()
	generated.RegisterRoutes(mux, &libraryServer{})

	// TODO: REST API handlers for /api/v1/books, /api/v1/reservations, /api/v1/inventory
	// TODO: PostgreSQL connection with pgx/v5
	// TODO: Redis caching with go-redis/v9
	// TODO: gRPC server with google.golang.org/grpc
	// TODO: GraphQL with github.com/99designs/gqlgen
	// TODO: OpenTelemetry with go.opentelemetry.io/otel
	// TODO: Prometheus metrics with github.com/prometheus/client_golang
	// TODO: Structured logging with log/slog
	// TODO: Circuit breaker with github.com/sony/gobreaker
	// TODO: Graceful shutdown

	port := getEnvDefault("PORT", "8080")
	server := &http.Server{Addr: fmt.Sprintf(":%s", port), Handler: mux} //nolint:gosec // skeleton server

	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
		<-sigCh
		log.Println("Shutting down...")
		if err := server.Close(); err != nil {
			log.Printf("Server close error: %v", err)
		}
	}()

	log.Printf("Go API server starting on port %s", port)
	if err := server.ListenAndServe(); err != http.ErrServerClosed {
		log.Fatalf("Server error: %v", err)
	}
}

func getEnvDefault(key, defaultValue string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultValue
}
