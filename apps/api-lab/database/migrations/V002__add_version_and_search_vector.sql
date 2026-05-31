ALTER TABLE books ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE books ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;

CREATE INDEX IF NOT EXISTS ix_books_search_vector ON books USING gin (search_vector);

UPDATE books SET search_vector = to_tsvector('english', coalesce(title, '') || ' ' || coalesce(author, '') || ' ' || coalesce(isbn, ''))
WHERE search_vector IS NULL;

CREATE OR REPLACE FUNCTION books_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', coalesce(NEW.title, '') || ' ' || coalesce(NEW.author, '') || ' ' || coalesce(NEW.isbn, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_books_search_vector ON books;
CREATE TRIGGER trg_books_search_vector
    BEFORE INSERT OR UPDATE OF title, author, isbn ON books
    FOR EACH ROW
    EXECUTE FUNCTION books_search_vector_update();

ALTER TABLE reservations ALTER COLUMN user_id TYPE UUID USING user_id::uuid;
