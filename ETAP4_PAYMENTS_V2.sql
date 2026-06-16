-- Этап 4: API v2 для платежей, внутреннего баланса и пополнений
-- Запускать на уже существующей БД PostgreSQL.

BEGIN;

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS payment_channel VARCHAR(30);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_payments_channel'
    ) THEN
        ALTER TABLE payments
            ADD CONSTRAINT chk_payments_channel
            CHECK (payment_channel IS NULL OR payment_channel IN ('wallet', 'bank_transfer', 'cash', 'manual', 'external'));
    END IF;
END $$;

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
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_payment_top_ups_status'
    ) THEN
        ALTER TABLE payment_top_ups
            ADD CONSTRAINT chk_payment_top_ups_status
            CHECK (status IN ('submitted', 'confirmed', 'rejected'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_payments_channel ON payments(payment_channel);
CREATE INDEX IF NOT EXISTS idx_payment_top_ups_user_id ON payment_top_ups(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_top_ups_status ON payment_top_ups(status);
CREATE INDEX IF NOT EXISTS idx_payment_top_ups_created_at ON payment_top_ups(created_at);

COMMIT;
