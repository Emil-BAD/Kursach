-- Полная схема БД v2 для проекта ИС общежитий КАИ
-- PostgreSQL
-- Версия согласована с текущими SQLAlchemy-моделями и API в папке api/
--
-- Что входит:
-- - старая база (пользователи, новости, мероприятия, товары и т.д.)
-- - доработки этапа 3 (заявки, история проживания, оплаты, аренда)
-- - доработки этапа 4 (внутренний баланс и пополнения)
-- - доработки этапа 5 (бытовой календарь, блоки общежития и кухонные дежурства)
-- - исправления несовпадений старого SQL и текущего API
--
-- Важно:
-- 1. Этот файл подходит для НОВОГО развёртывания с нуля.
-- 2. Для старой уже существующей БД лучше делать миграции, а не запускать всё поверх.
-- 3. Роли в сид-данных выровнены под текущий код: student/admin/commandant/moderator.

BEGIN;

-- =========================
-- Справочники и базовые таблицы
-- =========================

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    role_description TEXT
);

CREATE TABLE IF NOT EXISTS dormitories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(200) NOT NULL,
    image_urls TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[]
);

CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    room_number INTEGER NOT NULL CHECK (room_number > 0),
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    dormitory_id INTEGER NOT NULL REFERENCES dormitories(id) ON DELETE CASCADE,
    cleanliness_points INTEGER NOT NULL DEFAULT 0 CHECK (cleanliness_points >= 0),
    CONSTRAINT uq_rooms_dormitory_room UNIQUE (dormitory_id, room_number)
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    student_card VARCHAR(30) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    contact_number BIGINT NOT NULL CHECK (contact_number > 0),
    dormitory_id INTEGER REFERENCES dormitories(id) ON DELETE SET NULL,
    room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    group_number INTEGER,
    specialization VARCHAR(100),
    role_id INTEGER NOT NULL REFERENCES roles(id),
    email VARCHAR(100),
    phone VARCHAR(20),
    social_links JSONB,
    birth_date DATE,
    course INTEGER CHECK (course IS NULL OR course > 0),
    faculty VARCHAR(100),
    device_token VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    points JSONB NOT NULL DEFAULT '{"total": 100}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_not_null
    ON users (LOWER(email))
    WHERE email IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_users_phone_not_null
    ON users (phone)
    WHERE phone IS NOT NULL;

CREATE TABLE IF NOT EXISTS violation_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    default_penalty_points INTEGER CHECK (default_penalty_points IS NULL OR default_penalty_points >= 0)
);

CREATE TABLE IF NOT EXISTS activity_types (
    id SERIAL PRIMARY KEY,
    activity_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    entity_type VARCHAR(20) NOT NULL,
    CONSTRAINT chk_categories_entity_type CHECK (entity_type IN ('news', 'event', 'product')),
    CONSTRAINT uq_categories_name_entity_type UNIQUE (name, entity_type)
);

-- =========================
-- Основные таблицы старой системы
-- =========================

CREATE TABLE IF NOT EXISTS user_violations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    violation_type_id INTEGER NOT NULL REFERENCES violation_types(id) ON DELETE RESTRICT,
    violation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    penalty_points INTEGER NOT NULL CHECK (penalty_points >= 0),
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type_id INTEGER NOT NULL REFERENCES activity_types(id) ON DELETE RESTRICT,
    activity_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    earned_points INTEGER NOT NULL CHECK (earned_points >= 0),
    description TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS news (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    dormitory_id INTEGER REFERENCES dormitories(id) ON DELETE SET NULL,
    is_private BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    event_date TIMESTAMP NOT NULL,
    location VARCHAR(200) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    organizer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    dormitory_id INTEGER REFERENCES dormitories(id) ON DELETE SET NULL,
    is_private BOOLEAN NOT NULL DEFAULT FALSE,
    requirements TEXT,
    CONSTRAINT chk_events_status CHECK (status IN ('open', 'closed', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS event_registrations (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_event_registrations_status CHECK (status IN ('pending', 'confirmed', 'cancelled')),
    CONSTRAINT uq_event_registrations_event_user UNIQUE (event_id, user_id)
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    image_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    dormitory_id INTEGER REFERENCES dormitories(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    rejection_reason TEXT,
    seller_telegram VARCHAR(255),
    seller_vk VARCHAR(255),
    CONSTRAINT chk_products_status CHECK (status IN ('pending', 'approved', 'rejected'))
);

CREATE TABLE IF NOT EXISTS product_moderation_logs (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    moderator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL,
    reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_product_moderation_logs_action CHECK (action IN ('approved', 'rejected'))
);

CREATE TABLE IF NOT EXISTS favorite_products (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_favorite_products_user_product UNIQUE (user_id, product_id)
);

CREATE TABLE IF NOT EXISTS notification_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    entity_type VARCHAR(50),
    entity_id INTEGER
);

CREATE TABLE IF NOT EXISTS cleanliness_history (
    id SERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    score INTEGER NOT NULL CHECK (score BETWEEN 2 AND 5),
    assigned_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS action_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- Этап 3: заявки, проживание, оплаты, аренда
-- =========================

CREATE TABLE IF NOT EXISTS service_requests (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    request_type VARCHAR(30) NOT NULL DEFAULT 'request',
    status VARCHAR(30) NOT NULL DEFAULT 'new',
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    executor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    dormitory_id INTEGER REFERENCES dormitories(id) ON DELETE SET NULL,
    room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    resolution_comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    CONSTRAINT chk_service_requests_type CHECK (request_type IN ('repair', 'complaint', 'request')),
    CONSTRAINT chk_service_requests_status CHECK (status IN ('new', 'in_progress', 'resolved', 'rejected', 'closed'))
);

CREATE TABLE IF NOT EXISTS service_request_comments (
    id SERIAL PRIMARY KEY,
    service_request_id INTEGER NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comment TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_request_attachments (
    id SERIAL PRIMARY KEY,
    service_request_id INTEGER NOT NULL REFERENCES service_requests(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    uploaded_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS residence_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dormitory_id INTEGER NOT NULL REFERENCES dormitories(id) ON DELETE RESTRICT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    check_in_date DATE NOT NULL,
    check_out_date DATE,
    eviction_reason TEXT,
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_residence_history_dates CHECK (check_out_date IS NULL OR check_out_date >= check_in_date)
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dormitory_id INTEGER REFERENCES dormitories(id) ON DELETE SET NULL,
    room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    payment_channel VARCHAR(30),
    description TEXT,
    due_date DATE,
    paid_at TIMESTAMP,
    admin_comment TEXT,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payments_dates CHECK (period_end >= period_start),
    CONSTRAINT chk_payments_status CHECK (status IN ('pending', 'paid', 'overdue', 'cancelled', 'partially_paid')),
    CONSTRAINT chk_payments_channel CHECK (payment_channel IS NULL OR payment_channel IN ('wallet', 'bank_transfer', 'cash', 'manual', 'external'))
);

CREATE TABLE IF NOT EXISTS payment_account_settings (
    id SERIAL PRIMARY KEY,
    account_number VARCHAR(100) NOT NULL,
    recipient_name VARCHAR(200) NOT NULL,
    bank_name VARCHAR(200),
    payment_instructions TEXT,
    updated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_top_ups (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
    status VARCHAR(30) NOT NULL DEFAULT 'confirmed',
    transfer_reference VARCHAR(64) NOT NULL UNIQUE,
    account_number_snapshot VARCHAR(100) NOT NULL,
    recipient_name_snapshot VARCHAR(200) NOT NULL,
    bank_name_snapshot VARCHAR(200),
    receipt_file_name VARCHAR(255),
    receipt_file_url VARCHAR(500),
    comment TEXT,
    reviewed_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    credited_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payment_top_ups_status CHECK (status IN ('submitted', 'confirmed', 'rejected'))
);

CREATE TABLE IF NOT EXISTS rental_listings (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    daily_price NUMERIC(10, 2) NOT NULL CHECK (daily_price >= 0),
    deposit_amount NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (deposit_amount >= 0),
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    dormitory_id INTEGER REFERENCES dormitories(id) ON DELETE SET NULL,
    image_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'approved',
    listing_status VARCHAR(30) NOT NULL DEFAULT 'active',
    availability_status VARCHAR(30) NOT NULL DEFAULT 'free',
    pickup_location VARCHAR(255),
    minimum_rental_period_text VARCHAR(120),
    contact_name VARCHAR(120),
    contact_value VARCHAR(255),
    contact_note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_rental_listings_review_status CHECK (status IN ('pending', 'approved', 'rejected')),
    CONSTRAINT chk_rental_listings_status CHECK (listing_status IN ('active', 'paused', 'archived')),
    CONSTRAINT chk_rental_listings_availability CHECK (availability_status IN ('free', 'occupied'))
);

CREATE TABLE IF NOT EXISTS rental_bookings (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES rental_listings(id) ON DELETE CASCADE,
    renter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    approved_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    deposit_amount NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (deposit_amount >= 0),
    fine_amount NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (fine_amount >= 0),
    total_price NUMERIC(10, 2) NOT NULL CHECK (total_price >= 0),
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_rental_bookings_dates CHECK (end_date >= start_date),
    CONSTRAINT chk_rental_bookings_status CHECK (status IN ('pending', 'approved', 'active', 'completed', 'cancelled', 'rejected'))
);

-- =========================
-- Этап 5: бытовой календарь и дежурства
-- =========================

CREATE TABLE IF NOT EXISTS dormitory_blocks (
    id SERIAL PRIMARY KEY,
    dormitory_id INTEGER NOT NULL REFERENCES dormitories(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    kitchen_label VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dormitory_blocks_dormitory_name UNIQUE (dormitory_id, name)
);

CREATE TABLE IF NOT EXISTS dormitory_block_rooms (
    id SERIAL PRIMARY KEY,
    block_id INTEGER NOT NULL REFERENCES dormitory_blocks(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    rotation_order INTEGER NOT NULL CHECK (rotation_order > 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dormitory_block_rooms_block_room UNIQUE (block_id, room_id)
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    event_kind VARCHAR(30) NOT NULL,
    scope_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    start_at TIMESTAMP NOT NULL,
    end_at TIMESTAMP NOT NULL,
    is_all_day BOOLEAN NOT NULL DEFAULT FALSE,
    location VARCHAR(255),
    dormitory_id INTEGER REFERENCES dormitories(id) ON DELETE SET NULL,
    block_id INTEGER REFERENCES dormitory_blocks(id) ON DELETE SET NULL,
    room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    related_news_id INTEGER REFERENCES news(id) ON DELETE SET NULL,
    source_type VARCHAR(30) NOT NULL DEFAULT 'manual',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_calendar_events_kind CHECK (event_kind IN ('repair', 'water_outage', 'kitchen_duty', 'community_work', 'inspection', 'other')),
    CONSTRAINT chk_calendar_events_scope CHECK (scope_type IN ('global', 'dormitory', 'block', 'room')),
    CONSTRAINT chk_calendar_events_status CHECK (status IN ('scheduled', 'cancelled', 'completed', 'draft')),
    CONSTRAINT chk_calendar_events_source CHECK (source_type IN ('manual', 'duty_generated', 'news_generated')),
    CONSTRAINT chk_calendar_events_dates CHECK (end_at >= start_at),
    CONSTRAINT chk_calendar_events_scope_dormitory CHECK (scope_type <> 'dormitory' OR dormitory_id IS NOT NULL),
    CONSTRAINT chk_calendar_events_scope_block CHECK (scope_type <> 'block' OR block_id IS NOT NULL),
    CONSTRAINT chk_calendar_events_scope_room CHECK (scope_type <> 'room' OR room_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS kitchen_duty_plans (
    id SERIAL PRIMARY KEY,
    dormitory_id INTEGER NOT NULL REFERENCES dormitories(id) ON DELETE RESTRICT,
    block_id INTEGER NOT NULL REFERENCES dormitory_blocks(id) ON DELETE RESTRICT,
    month_start DATE NOT NULL,
    month_end DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_kitchen_duty_plans_dates CHECK (month_end >= month_start),
    CONSTRAINT chk_kitchen_duty_plans_status CHECK (status IN ('draft', 'generated', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS kitchen_duty_assignments (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES kitchen_duty_plans(id) ON DELETE CASCADE,
    calendar_event_id INTEGER NOT NULL REFERENCES calendar_events(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    duty_date DATE NOT NULL,
    duty_order INTEGER NOT NULL CHECK (duty_order > 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_kitchen_duty_assignments_plan_date UNIQUE (plan_id, duty_date),
    CONSTRAINT uq_kitchen_duty_assignments_event UNIQUE (calendar_event_id)
);

-- =========================
-- Индексы
-- =========================

CREATE INDEX IF NOT EXISTS idx_users_dormitory_id ON users(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_users_room_id ON users(room_id);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);

CREATE INDEX IF NOT EXISTS idx_user_violations_user_id ON user_violations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_violations_type_id ON user_violations(violation_type_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_type_id ON user_activities(activity_type_id);

CREATE INDEX IF NOT EXISTS idx_news_dormitory_id ON news(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_events_dormitory_id ON events(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_event_registrations_user_id ON event_registrations(user_id);

CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_dormitory_id ON products(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_product_moderation_logs_product_id ON product_moderation_logs(product_id);
CREATE INDEX IF NOT EXISTS idx_favorite_products_user_id ON favorite_products(user_id);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_cleanliness_history_room_id ON cleanliness_history(room_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_user_id ON action_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

CREATE INDEX IF NOT EXISTS idx_service_requests_student_id ON service_requests(student_id);
CREATE INDEX IF NOT EXISTS idx_service_requests_executor_id ON service_requests(executor_id);
CREATE INDEX IF NOT EXISTS idx_service_requests_dormitory_id ON service_requests(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_service_requests_room_id ON service_requests(room_id);
CREATE INDEX IF NOT EXISTS idx_service_requests_type ON service_requests(request_type);
CREATE INDEX IF NOT EXISTS idx_service_requests_status ON service_requests(status);
CREATE INDEX IF NOT EXISTS idx_service_request_comments_request_id ON service_request_comments(service_request_id);
CREATE INDEX IF NOT EXISTS idx_service_request_attachments_request_id ON service_request_attachments(service_request_id);

CREATE INDEX IF NOT EXISTS idx_residence_history_user_id ON residence_history(user_id);
CREATE INDEX IF NOT EXISTS idx_residence_history_dormitory_id ON residence_history(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_residence_history_room_id ON residence_history(room_id);
CREATE INDEX IF NOT EXISTS idx_residence_history_check_in_date ON residence_history(check_in_date);

CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_dormitory_id ON payments(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_payments_room_id ON payments(room_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_channel ON payments(payment_channel);
CREATE INDEX IF NOT EXISTS idx_payments_period ON payments(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_payment_top_ups_user_id ON payment_top_ups(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_top_ups_status ON payment_top_ups(status);
CREATE INDEX IF NOT EXISTS idx_payment_top_ups_created_at ON payment_top_ups(created_at);

CREATE INDEX IF NOT EXISTS idx_rental_listings_owner_id ON rental_listings(owner_id);
CREATE INDEX IF NOT EXISTS idx_rental_listings_category_id ON rental_listings(category_id);
CREATE INDEX IF NOT EXISTS idx_rental_listings_dormitory_id ON rental_listings(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_rental_listings_status ON rental_listings(status);
CREATE INDEX IF NOT EXISTS idx_rental_listings_listing_status ON rental_listings(listing_status);
CREATE INDEX IF NOT EXISTS idx_rental_listings_availability_status ON rental_listings(availability_status);
CREATE INDEX IF NOT EXISTS idx_rental_bookings_listing_id ON rental_bookings(listing_id);
CREATE INDEX IF NOT EXISTS idx_rental_bookings_renter_id ON rental_bookings(renter_id);
CREATE INDEX IF NOT EXISTS idx_rental_bookings_status ON rental_bookings(status);
CREATE INDEX IF NOT EXISTS idx_rental_bookings_period ON rental_bookings(start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_dormitory_blocks_dormitory_id ON dormitory_blocks(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_dormitory_blocks_is_active ON dormitory_blocks(is_active);
CREATE INDEX IF NOT EXISTS idx_dormitory_block_rooms_room_id ON dormitory_block_rooms(room_id);
CREATE INDEX IF NOT EXISTS idx_dormitory_block_rooms_rotation_order ON dormitory_block_rooms(rotation_order);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start_at ON calendar_events(start_at);
CREATE INDEX IF NOT EXISTS idx_calendar_events_event_kind ON calendar_events(event_kind);
CREATE INDEX IF NOT EXISTS idx_calendar_events_status ON calendar_events(status);
CREATE INDEX IF NOT EXISTS idx_calendar_events_dormitory_id ON calendar_events(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_block_id ON calendar_events(block_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_room_id ON calendar_events(room_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_related_news_id ON calendar_events(related_news_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_plans_dormitory_id ON kitchen_duty_plans(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_plans_block_id ON kitchen_duty_plans(block_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_plans_month_start ON kitchen_duty_plans(month_start);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_plans_status ON kitchen_duty_plans(status);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_assignments_room_id ON kitchen_duty_assignments(room_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_assignments_duty_date ON kitchen_duty_assignments(duty_date);

CREATE INDEX IF NOT EXISTS idx_products_title_tsv
    ON products USING GIN (to_tsvector('russian', COALESCE(title, '')));

CREATE INDEX IF NOT EXISTS idx_products_description_tsv
    ON products USING GIN (to_tsvector('russian', COALESCE(description, '')));

CREATE INDEX IF NOT EXISTS idx_news_title_tsv
    ON news USING GIN (to_tsvector('russian', COALESCE(title, '')));

CREATE INDEX IF NOT EXISTS idx_service_requests_title_tsv
    ON service_requests USING GIN (to_tsvector('russian', COALESCE(title, '')));

CREATE INDEX IF NOT EXISTS idx_rental_listings_title_tsv
    ON rental_listings USING GIN (to_tsvector('russian', COALESCE(title, '')));

-- =========================
-- Начальные данные
-- =========================

INSERT INTO roles (id, role_name, role_description) VALUES
    (1, 'student', 'Студент'),
    (2, 'admin', 'Администратор системы'),
    (3, 'commandant', 'Комендант общежития'),
    (4, 'moderator', 'Модератор маркетплейса'),
    (5, 'sanitary_commission_member', 'Член санитарной комиссии'),
    (6, 'sanitary_commission_head', 'Глава санитарной комиссии'),
    (7, 'council_president', 'Председатель совета общежития'),
    (8, 'council_member', 'Член совета общежития'),
    (9, 'educator', 'Сотрудник / воспитатель')
ON CONFLICT (id) DO NOTHING;

INSERT INTO categories (name, entity_type) VALUES
    ('Важные', 'news'),
    ('Просто новости', 'news'),
    ('Киновечер', 'event'),
    ('Дискотека', 'event'),
    ('Субботник', 'event'),
    ('Еда и напитки', 'product'),
    ('Одежда', 'product'),
    ('Электроника', 'product'),
    ('Техника', 'product'),
    ('Инструменты', 'product'),
    ('Учебные материалы', 'product'),
    ('Учеба', 'product'),
    ('Спорт', 'product'),
    ('Мебель', 'product'),
    ('Бытовые товары', 'product'),
    ('Услуги', 'product'),
    ('Прочее', 'product'),
    ('Другое', 'product')
ON CONFLICT (name, entity_type) DO NOTHING;

INSERT INTO violation_types (name, description, default_penalty_points) VALUES
    ('Нарушение чистоты', 'Оставил мусор в комнате', 5),
    ('Шум после 23:00', 'Громкая музыка после 23:00', 10),
    ('Неучастие в субботнике', 'Не явился на субботник без уважительной причины', 15)
ON CONFLICT (name) DO NOTHING;

INSERT INTO activity_types (activity_name, description) VALUES
    ('Помощь в субботнике', 'Активное участие в субботнике'),
    ('Организация мероприятия', 'Помощь в организации киновечера'),
    ('Уборка территории', 'Уборка двора общежития')
ON CONFLICT (activity_name) DO NOTHING;

INSERT INTO dormitories (id, name, address, image_urls) VALUES
    (1, 'Общежитие №1', 'Казань, ул. Студенческая, 1', ARRAY[]::TEXT[]),
    (2, 'Общежитие №2', 'Казань, ул. Академика Кирпичникова, 11', ARRAY[]::TEXT[])
ON CONFLICT (id) DO NOTHING;

INSERT INTO rooms (id, room_number, capacity, dormitory_id, cleanliness_points) VALUES
    (1, 101, 3, 1, 4),
    (2, 315, 2, 2, 5)
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (
    id,
    student_card,
    password_hash,
    full_name,
    contact_number,
    dormitory_id,
    room_id,
    group_number,
    specialization,
    role_id,
    email,
    phone,
    social_links,
    birth_date,
    course,
    faculty,
    points
) VALUES
    (
        1,
        'ST123',
        '$2b$12$oCSuKOelYsQAAd.ZnXsU0OQfmiPVvcrU/o7uCRpat/spSkgJXBnIa',
        'Иванов Иван Иванович',
        79001234567,
        1,
        1,
        101,
        'Информатика',
        1,
        'ivanov@example.com',
        '+79991234567',
        '{"telegram": "https://t.me/ivan"}'::jsonb,
        '2003-05-15',
        2,
        'ИТ',
        '{"total": 100}'::jsonb
    ),
    (
        2,
        'ADMIN001',
        '$2b$12$h9ePlr7PHMcGWwALDT198ORNqeKfwXTHsaB6S6RRNPoQ5VOzMCS6.',
        'Админов Админ Админович',
        79001234568,
        1,
        1,
        0,
        'Администрирование',
        2,
        'admin@example.com',
        '+79991234568',
        '{"telegram": "https://t.me/admin"}'::jsonb,
        '2002-03-10',
        3,
        'ИТ',
        '{"total": 100}'::jsonb
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO user_activities (user_id, activity_type_id, activity_date, earned_points, description, notes) VALUES
    (1, 1, CURRENT_TIMESTAMP - INTERVAL '2 day', 10, 'Помощь в субботнике 2026-04-27', NULL),
    (1, 2, CURRENT_TIMESTAMP - INTERVAL '3 day', 20, 'Организация киновечера 2026-04-26', NULL),
    (1, 3, CURRENT_TIMESTAMP - INTERVAL '4 day', 15, 'Уборка двора 2026-04-25', NULL)
ON CONFLICT DO NOTHING;

INSERT INTO cleanliness_history (room_id, score, assigned_by, assigned_at) VALUES
    (1, 4, 2, CURRENT_TIMESTAMP - INTERVAL '7 day'),
    (1, 5, 2, CURRENT_TIMESTAMP - INTERVAL '3 day'),
    (2, 5, 2, CURRENT_TIMESTAMP - INTERVAL '1 day')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS dormitory_blocks (
    id SERIAL PRIMARY KEY,
    dormitory_id INTEGER NOT NULL REFERENCES dormitories(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    kitchen_label VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dormitory_blocks_dormitory_name UNIQUE (dormitory_id, name)
);

CREATE TABLE IF NOT EXISTS dormitory_block_rooms (
    id SERIAL PRIMARY KEY,
    block_id INTEGER NOT NULL REFERENCES dormitory_blocks(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    rotation_order INTEGER NOT NULL CHECK (rotation_order > 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dormitory_block_rooms_block_room UNIQUE (block_id, room_id)
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    event_kind VARCHAR(30) NOT NULL,
    scope_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    start_at TIMESTAMP NOT NULL,
    end_at TIMESTAMP NOT NULL,
    is_all_day BOOLEAN NOT NULL DEFAULT FALSE,
    location VARCHAR(255),
    dormitory_id INTEGER REFERENCES dormitories(id) ON DELETE SET NULL,
    block_id INTEGER REFERENCES dormitory_blocks(id) ON DELETE SET NULL,
    room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    related_news_id INTEGER REFERENCES news(id) ON DELETE SET NULL,
    source_type VARCHAR(30) NOT NULL DEFAULT 'manual',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_calendar_events_kind CHECK (event_kind IN ('repair', 'water_outage', 'kitchen_duty', 'community_work', 'inspection', 'other')),
    CONSTRAINT chk_calendar_events_scope CHECK (scope_type IN ('global', 'dormitory', 'block', 'room')),
    CONSTRAINT chk_calendar_events_status CHECK (status IN ('scheduled', 'cancelled', 'completed', 'draft')),
    CONSTRAINT chk_calendar_events_source CHECK (source_type IN ('manual', 'duty_generated', 'news_generated')),
    CONSTRAINT chk_calendar_events_dates CHECK (end_at >= start_at),
    CONSTRAINT chk_calendar_events_scope_dormitory CHECK (scope_type <> 'dormitory' OR dormitory_id IS NOT NULL),
    CONSTRAINT chk_calendar_events_scope_block CHECK (scope_type <> 'block' OR block_id IS NOT NULL),
    CONSTRAINT chk_calendar_events_scope_room CHECK (scope_type <> 'room' OR room_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS kitchen_duty_plans (
    id SERIAL PRIMARY KEY,
    dormitory_id INTEGER NOT NULL REFERENCES dormitories(id) ON DELETE RESTRICT,
    block_id INTEGER NOT NULL REFERENCES dormitory_blocks(id) ON DELETE RESTRICT,
    month_start DATE NOT NULL,
    month_end DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_kitchen_duty_plans_dates CHECK (month_end >= month_start),
    CONSTRAINT chk_kitchen_duty_plans_status CHECK (status IN ('draft', 'generated', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS kitchen_duty_assignments (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES kitchen_duty_plans(id) ON DELETE CASCADE,
    calendar_event_id INTEGER NOT NULL REFERENCES calendar_events(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    duty_date DATE NOT NULL,
    duty_order INTEGER NOT NULL CHECK (duty_order > 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_kitchen_duty_assignments_plan_date UNIQUE (plan_id, duty_date),
    CONSTRAINT uq_kitchen_duty_assignments_event UNIQUE (calendar_event_id)
);

CREATE INDEX IF NOT EXISTS idx_dormitory_blocks_dormitory_id
    ON dormitory_blocks(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_dormitory_blocks_is_active
    ON dormitory_blocks(is_active);
CREATE INDEX IF NOT EXISTS idx_dormitory_block_rooms_room_id
    ON dormitory_block_rooms(room_id);
CREATE INDEX IF NOT EXISTS idx_dormitory_block_rooms_rotation_order
    ON dormitory_block_rooms(rotation_order);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start_at
    ON calendar_events(start_at);
CREATE INDEX IF NOT EXISTS idx_calendar_events_event_kind
    ON calendar_events(event_kind);
CREATE INDEX IF NOT EXISTS idx_calendar_events_status
    ON calendar_events(status);
CREATE INDEX IF NOT EXISTS idx_calendar_events_dormitory_id
    ON calendar_events(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_block_id
    ON calendar_events(block_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_room_id
    ON calendar_events(room_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_related_news_id
    ON calendar_events(related_news_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_plans_dormitory_id
    ON kitchen_duty_plans(dormitory_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_plans_block_id
    ON kitchen_duty_plans(block_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_plans_month_start
    ON kitchen_duty_plans(month_start);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_plans_status
    ON kitchen_duty_plans(status);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_assignments_room_id
    ON kitchen_duty_assignments(room_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_duty_assignments_duty_date
    ON kitchen_duty_assignments(duty_date);

COMMIT;
