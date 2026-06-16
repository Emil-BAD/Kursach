-- Этап 3: добавление новых таблиц для ИС общежития
-- PostgreSQL
-- Скрипт не меняет старые таблицы users / rooms / dormitories / products
-- Он только добавляет новые таблицы и индексы

BEGIN;

CREATE TABLE IF NOT EXISTS service_requests (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    request_type VARCHAR(30) NOT NULL DEFAULT 'request',
    status VARCHAR(30) NOT NULL DEFAULT 'new',
    student_id INTEGER NOT NULL REFERENCES users(id),
    executor_id INTEGER REFERENCES users(id),
    dormitory_id INTEGER REFERENCES dormitories(id),
    room_id INTEGER REFERENCES rooms(id),
    resolution_comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    CONSTRAINT chk_service_requests_type
        CHECK (request_type IN ('repair', 'complaint', 'request')),
    CONSTRAINT chk_service_requests_status
        CHECK (status IN ('new', 'in_progress', 'resolved', 'rejected', 'closed'))
);

CREATE TABLE IF NOT EXISTS service_request_comments (
    id SERIAL PRIMARY KEY,
    service_request_id INTEGER NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES users(id),
    comment TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_request_attachments (
    id SERIAL PRIMARY KEY,
    service_request_id INTEGER NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    uploaded_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS residence_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    dormitory_id INTEGER NOT NULL REFERENCES dormitories(id),
    room_id INTEGER NOT NULL REFERENCES rooms(id),
    check_in_date DATE NOT NULL,
    check_out_date DATE,
    eviction_reason TEXT,
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_residence_dates
        CHECK (check_out_date IS NULL OR check_out_date >= check_in_date)
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    dormitory_id INTEGER REFERENCES dormitories(id),
    room_id INTEGER REFERENCES rooms(id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    description TEXT,
    due_date DATE,
    paid_at TIMESTAMP,
    admin_comment TEXT,
    created_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payments_dates
        CHECK (period_end >= period_start),
    CONSTRAINT chk_payments_amount
        CHECK (amount >= 0),
    CONSTRAINT chk_payments_status
        CHECK (status IN ('pending', 'paid', 'overdue', 'cancelled', 'partially_paid'))
);

CREATE TABLE IF NOT EXISTS rental_listings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    daily_price NUMERIC(10, 2) NOT NULL,
    deposit_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    dormitory_id INTEGER REFERENCES dormitories(id),
    image_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    listing_status VARCHAR(30) NOT NULL DEFAULT 'active',
    availability_status VARCHAR(30) NOT NULL DEFAULT 'free',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_rental_listings_daily_price
        CHECK (daily_price >= 0),
    CONSTRAINT chk_rental_listings_deposit
        CHECK (deposit_amount >= 0),
    CONSTRAINT chk_rental_listings_status
        CHECK (listing_status IN ('active', 'paused', 'archived')),
    CONSTRAINT chk_rental_listings_availability
        CHECK (availability_status IN ('free', 'occupied'))
);

CREATE TABLE IF NOT EXISTS rental_bookings (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES rental_listings(id),
    renter_id INTEGER NOT NULL REFERENCES users(id),
    approved_by_id INTEGER REFERENCES users(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    deposit_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    fine_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total_price NUMERIC(10, 2) NOT NULL,
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_rental_bookings_dates
        CHECK (end_date >= start_date),
    CONSTRAINT chk_rental_bookings_deposit
        CHECK (deposit_amount >= 0),
    CONSTRAINT chk_rental_bookings_fine
        CHECK (fine_amount >= 0),
    CONSTRAINT chk_rental_bookings_total_price
        CHECK (total_price >= 0),
    CONSTRAINT chk_rental_bookings_status
        CHECK (status IN ('pending', 'approved', 'active', 'completed', 'cancelled', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_service_requests_student_id
    ON service_requests(student_id);

CREATE INDEX IF NOT EXISTS idx_service_requests_executor_id
    ON service_requests(executor_id);

CREATE INDEX IF NOT EXISTS idx_service_requests_dormitory_id
    ON service_requests(dormitory_id);

CREATE INDEX IF NOT EXISTS idx_service_requests_room_id
    ON service_requests(room_id);

CREATE INDEX IF NOT EXISTS idx_service_requests_type
    ON service_requests(request_type);

CREATE INDEX IF NOT EXISTS idx_service_requests_status
    ON service_requests(status);

CREATE INDEX IF NOT EXISTS idx_service_request_comments_request_id
    ON service_request_comments(service_request_id);

CREATE INDEX IF NOT EXISTS idx_service_request_attachments_request_id
    ON service_request_attachments(service_request_id);

CREATE INDEX IF NOT EXISTS idx_residence_history_user_id
    ON residence_history(user_id);

CREATE INDEX IF NOT EXISTS idx_residence_history_dormitory_id
    ON residence_history(dormitory_id);

CREATE INDEX IF NOT EXISTS idx_residence_history_room_id
    ON residence_history(room_id);

CREATE INDEX IF NOT EXISTS idx_residence_history_check_in_date
    ON residence_history(check_in_date);

CREATE INDEX IF NOT EXISTS idx_payments_user_id
    ON payments(user_id);

CREATE INDEX IF NOT EXISTS idx_payments_dormitory_id
    ON payments(dormitory_id);

CREATE INDEX IF NOT EXISTS idx_payments_room_id
    ON payments(room_id);

CREATE INDEX IF NOT EXISTS idx_payments_status
    ON payments(status);

CREATE INDEX IF NOT EXISTS idx_payments_period
    ON payments(period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_rental_listings_owner_id
    ON rental_listings(owner_id);

CREATE INDEX IF NOT EXISTS idx_rental_listings_dormitory_id
    ON rental_listings(dormitory_id);

CREATE INDEX IF NOT EXISTS idx_rental_listings_listing_status
    ON rental_listings(listing_status);

CREATE INDEX IF NOT EXISTS idx_rental_listings_availability_status
    ON rental_listings(availability_status);

CREATE INDEX IF NOT EXISTS idx_rental_bookings_listing_id
    ON rental_bookings(listing_id);

CREATE INDEX IF NOT EXISTS idx_rental_bookings_renter_id
    ON rental_bookings(renter_id);

CREATE INDEX IF NOT EXISTS idx_rental_bookings_status
    ON rental_bookings(status);

CREATE INDEX IF NOT EXISTS idx_rental_bookings_period
    ON rental_bookings(start_date, end_date);

COMMIT;
