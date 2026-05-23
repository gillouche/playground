-- V003: Add indexes that match query patterns from book_service.
-- These improve list/filter performance under realistic load.

CREATE INDEX IF NOT EXISTS ix_books_genre ON books (genre);
CREATE INDEX IF NOT EXISTS ix_books_created_at ON books (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_books_updated_at ON books (updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_books_title ON books (title);
CREATE INDEX IF NOT EXISTS ix_books_published_year ON books (published_year);
CREATE INDEX IF NOT EXISTS ix_books_available
    ON books (created_at DESC) WHERE available_copies > 0;

CREATE INDEX IF NOT EXISTS ix_reservations_reserved_at
    ON reservations (reserved_at DESC);
CREATE INDEX IF NOT EXISTS ix_reservations_due_date
    ON reservations (due_date) WHERE status = 'ACTIVE';
CREATE INDEX IF NOT EXISTS ix_reservations_user_status
    ON reservations (user_id, status);
CREATE INDEX IF NOT EXISTS ix_reservations_book_status
    ON reservations (book_id, status);
