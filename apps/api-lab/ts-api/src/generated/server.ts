// Generated from openapi.yaml - DO NOT EDIT

import { FastifyInstance } from "fastify";
import {
  BookCreate,
  BookUpdate,
  BookResponse,
  ReservationCreate,
  ReservationResponse,
  InventoryResponse,
  HealthResponse,
  InfoResponse,
} from "./models";

export interface ListBooksParams {
  available_only?: boolean;
  genre?: string;
  author?: string;
  search?: string;
}

export interface ListReservationsParams {
  user_id?: string;
  status?: string;
  book_id?: string;
}

export interface LibraryAPI {
  listBooks(params: ListBooksParams): Promise<BookResponse[]>;
  createBook(body: BookCreate): Promise<BookResponse>;
  getBook(bookId: string): Promise<BookResponse | null>;
  updateBook(bookId: string, body: BookUpdate): Promise<BookResponse | null>;
  deleteBook(bookId: string): Promise<boolean>;
  getInventory(): Promise<InventoryResponse>;
  createReservations(body: ReservationCreate): Promise<ReservationResponse[]>;
  listReservations(params: ListReservationsParams): Promise<ReservationResponse[]>;
  getReservation(reservationId: string): Promise<ReservationResponse | null>;
  returnReservation(reservationId: string): Promise<ReservationResponse | null>;
  healthCheck(): Promise<HealthResponse>;
  readinessCheck(): Promise<HealthResponse>;
  serviceInfo(): Promise<InfoResponse>;
}

export function registerRoutes(server: FastifyInstance, api: LibraryAPI): void {
  // GET /api/v1/books
  server.get<{
    Querystring: ListBooksParams;
  }>("/api/v1/books", async (request, reply) => {
    const params: ListBooksParams = {
      available_only: request.query.available_only,
      genre: request.query.genre,
      author: request.query.author,
      search: request.query.search,
    };
    const result = await api.listBooks(params);
    return reply.status(200).send(result);
  });

  // POST /api/v1/books
  server.post<{
    Body: BookCreate;
  }>("/api/v1/books", async (request, reply) => {
    const result = await api.createBook(request.body);
    return reply.status(201).send(result);
  });

  // GET /api/v1/books/:book_id
  server.get<{
    Params: { book_id: string };
  }>("/api/v1/books/:book_id", async (request, reply) => {
    const result = await api.getBook(request.params.book_id);
    if (result === null) {
      return reply.status(404).send({ detail: "Book not found", status_code: 404 });
    }
    return reply.status(200).send(result);
  });

  // PUT /api/v1/books/:book_id
  server.put<{
    Params: { book_id: string };
    Body: BookUpdate;
  }>("/api/v1/books/:book_id", async (request, reply) => {
    const result = await api.updateBook(request.params.book_id, request.body);
    if (result === null) {
      return reply.status(404).send({ detail: "Book not found", status_code: 404 });
    }
    return reply.status(200).send(result);
  });

  // DELETE /api/v1/books/:book_id
  server.delete<{
    Params: { book_id: string };
  }>("/api/v1/books/:book_id", async (request, reply) => {
    const deleted = await api.deleteBook(request.params.book_id);
    if (!deleted) {
      return reply.status(404).send({ detail: "Book not found", status_code: 404 });
    }
    return reply.status(204).send();
  });

  // GET /api/v1/inventory
  server.get("/api/v1/inventory", async (_request, reply) => {
    const result = await api.getInventory();
    return reply.status(200).send(result);
  });

  // POST /api/v1/reservations
  server.post<{
    Body: ReservationCreate;
  }>("/api/v1/reservations", async (request, reply) => {
    const result = await api.createReservations(request.body);
    return reply.status(201).send(result);
  });

  // GET /api/v1/reservations
  server.get<{
    Querystring: ListReservationsParams;
  }>("/api/v1/reservations", async (request, reply) => {
    const params: ListReservationsParams = {
      user_id: request.query.user_id,
      status: request.query.status,
      book_id: request.query.book_id,
    };
    const result = await api.listReservations(params);
    return reply.status(200).send(result);
  });

  // GET /api/v1/reservations/:id
  server.get<{
    Params: { id: string };
  }>("/api/v1/reservations/:id", async (request, reply) => {
    const result = await api.getReservation(request.params.id);
    if (result === null) {
      return reply.status(404).send({ detail: "Reservation not found", status_code: 404 });
    }
    return reply.status(200).send(result);
  });

  // POST /api/v1/reservations/:id/return
  server.post<{
    Params: { id: string };
  }>("/api/v1/reservations/:id/return", async (request, reply) => {
    const result = await api.returnReservation(request.params.id);
    if (result === null) {
      return reply.status(404).send({ detail: "Reservation not found", status_code: 404 });
    }
    return reply.status(200).send(result);
  });

  // GET /healthz
  server.get("/healthz", async (_request, reply) => {
    const result = await api.healthCheck();
    return reply.status(200).send(result);
  });

  // GET /ready
  server.get("/ready", async (_request, reply) => {
    const result = await api.readinessCheck();
    return reply.status(200).send(result);
  });

  // GET /info
  server.get("/info", async (_request, reply) => {
    const result = await api.serviceInfo();
    return reply.status(200).send(result);
  });
}
