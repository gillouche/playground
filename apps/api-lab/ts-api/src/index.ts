import Fastify from "fastify";
import * as os from "os";
import {
  LibraryAPI,
  registerRoutes,
  BookCreate,
  BookUpdate,
  BookResponse,
  ReservationCreate,
  ReservationResponse,
  InventoryResponse,
  HealthResponse,
  InfoResponse,
  ListBooksParams,
  ListReservationsParams,
} from "./generated";

const server = Fastify({ logger: true });

const libraryAPI: LibraryAPI = {
  async listBooks(_params: ListBooksParams): Promise<BookResponse[]> {
    // TODO: Implement with database query
    throw new Error("Not implemented");
  },

  async createBook(_body: BookCreate): Promise<BookResponse> {
    // TODO: Implement with database insert
    throw new Error("Not implemented");
  },

  async getBook(_bookId: string): Promise<BookResponse | null> {
    // TODO: Implement with database lookup
    throw new Error("Not implemented");
  },

  async updateBook(_bookId: string, _body: BookUpdate): Promise<BookResponse | null> {
    // TODO: Implement with database update
    throw new Error("Not implemented");
  },

  async deleteBook(_bookId: string): Promise<boolean> {
    // TODO: Implement with database delete
    throw new Error("Not implemented");
  },

  async getInventory(): Promise<InventoryResponse> {
    // TODO: Implement with database query
    throw new Error("Not implemented");
  },

  async createReservations(_body: ReservationCreate): Promise<ReservationResponse[]> {
    // TODO: Implement with database transaction
    throw new Error("Not implemented");
  },

  async listReservations(_params: ListReservationsParams): Promise<ReservationResponse[]> {
    // TODO: Implement with database query
    throw new Error("Not implemented");
  },

  async getReservation(_reservationId: string): Promise<ReservationResponse | null> {
    // TODO: Implement with database lookup
    throw new Error("Not implemented");
  },

  async returnReservation(_reservationId: string): Promise<ReservationResponse | null> {
    // TODO: Implement with database update
    throw new Error("Not implemented");
  },

  async healthCheck(): Promise<HealthResponse> {
    return { status: "ok" };
  },

  async readinessCheck(): Promise<HealthResponse> {
    // TODO: Check PostgreSQL connection (pg or Prisma)
    // TODO: Check Redis connection (ioredis)
    return { status: "ready" };
  },

  async serviceInfo(): Promise<InfoResponse> {
    return {
      hostname: process.env.HOSTNAME || os.hostname(),
      app_version: process.env.APP_VERSION,
      environment: process.env.ENVIRONMENT,
      app: process.env.APP,
      component: process.env.COMPONENT,
      node: process.env.NODE_NAME,
      pod_ip: process.env.POD_IP,
      log_level: process.env.LOG_LEVEL || "INFO",
      git_tag: process.env.GIT_TAG,
      git_commit: process.env.GIT_COMMIT,
    };
  },
};

registerRoutes(server, libraryAPI);

// TODO: PostgreSQL connection with pg or Prisma
//   - Connection pooling
//   - Transaction support for reservations

// TODO: Redis caching with ioredis
//   - Cache books (TTL 30s), individual books (TTL 60s), inventory (TTL 15s)
//   - Cache invalidation on writes

// TODO: gRPC server with @grpc/grpc-js
//   - Implement LibraryService from library.proto
//   - Run on port 50051 alongside HTTP server
//   - Enable gRPC reflection

// TODO: GraphQL with Apollo Server + @as-integrations/fastify
//   - Schema matching OpenAPI spec
//   - Queries and Mutations for all book/reservation operations

// TODO: OpenTelemetry with @opentelemetry/sdk-node
//   - TracerProvider with OTLP exporter
//   - HTTP instrumentation
//   - gRPC instrumentation

// TODO: Prometheus metrics with prom-client
//   - HTTP request metrics
//   - Custom counters and histograms
//   - Expose /metrics endpoint

// TODO: Structured logging with pino (Fastify default)
//   - JSON output
//   - Trace ID correlation

// TODO: Circuit breaker with opossum
//   - Wrap database and cache calls
//   - Configurable thresholds and timeout

const port = parseInt(process.env.PORT || "8080", 10);

server.listen({ port, host: "0.0.0.0" }, (err) => {
  if (err) {
    server.log.error(err);
    process.exit(1);
  }
  server.log.info(`TypeScript API server listening on port ${port}`);
});

// Graceful shutdown
process.on("SIGTERM", async () => {
  server.log.info("Received SIGTERM, shutting down...");
  await server.close();
  process.exit(0);
});

process.on("SIGINT", async () => {
  server.log.info("Received SIGINT, shutting down...");
  await server.close();
  process.exit(0);
});
