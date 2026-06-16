-- Этап 5: Calendar API v1
-- Запускать на уже существующей БД PostgreSQL.

BEGIN;

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
