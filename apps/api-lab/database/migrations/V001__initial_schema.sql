-- V001: Initial schema for api-lab library management system.
-- Creates the books and reservations tables with all indexes and constraints.

DO $$ BEGIN
    CREATE TYPE reservation_status AS ENUM ('ACTIVE', 'RETURNED', 'OVERDUE');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isbn VARCHAR(13) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    genre VARCHAR(100) NOT NULL,
    published_year INTEGER NOT NULL,
    total_copies INTEGER NOT NULL,
    available_copies INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT check_available_copies_non_negative CHECK (available_copies >= 0)
);

CREATE INDEX IF NOT EXISTS ix_books_isbn ON books (isbn);
CREATE INDEX IF NOT EXISTS ix_books_author ON books (author);

CREATE TABLE IF NOT EXISTS reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES books(id),
    user_id VARCHAR(255) NOT NULL,
    reserved_at TIMESTAMPTZ DEFAULT now(),
    due_date TIMESTAMPTZ NOT NULL,
    returned_at TIMESTAMPTZ,
    status reservation_status DEFAULT 'ACTIVE'
);

CREATE INDEX IF NOT EXISTS ix_reservations_user_id ON reservations (user_id);
CREATE INDEX IF NOT EXISTS ix_reservations_status ON reservations (status);
CREATE INDEX IF NOT EXISTS ix_reservations_book_id ON reservations (book_id);
