// Generated from openapi.yaml - DO NOT EDIT

/** Status of a reservation */
export type ReservationStatus = "ACTIVE" | "RETURNED" | "OVERDUE";

export interface Book {
  /** @format uuid */
  id: string;
  isbn: string;
  title: string;
  author: string;
  genre: string;
  published_year: number;
  total_copies: number;
  available_copies: number;
  /** @format date-time */
  created_at: string;
  /** @format date-time */
  updated_at: string;
}

export interface BookCreate {
  isbn: string;
  title: string;
  author: string;
  genre: string;
  published_year: number;
  total_copies: number;
}

export interface BookUpdate {
  isbn?: string;
  title?: string;
  author?: string;
  genre?: string;
  published_year?: number;
  total_copies?: number;
}

/** BookResponse is identical to Book (allOf $ref) */
export type BookResponse = Book;

export interface Reservation {
  /** @format uuid */
  id: string;
  /** @format uuid */
  book_id: string;
  user_id: string;
  /** @format date-time */
  reserved_at: string;
  /** @format date-time */
  due_date: string;
  /** @format date-time */
  returned_at?: string | null;
  status: ReservationStatus;
}

export interface ReservationCreate {
  user_id: string;
  /** @format uuid */
  book_ids: string[];
}

/** ReservationResponse is identical to Reservation (allOf $ref) */
export type ReservationResponse = Reservation;

export interface InventoryResponse {
  items: Book[];
}

export interface ErrorResponse {
  detail: string;
  status_code: number;
}

export interface HealthResponse {
  status: string;
}

export interface InfoResponse {
  hostname?: string;
  app_version?: string;
  environment?: string;
  app?: string;
  component?: string;
  node?: string;
  pod_ip?: string;
  log_level?: string;
  git_tag?: string;
  git_commit?: string;
}
