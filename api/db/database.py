from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import logging
import time

from api.core.config import settings
from api.db.models import Base

logger = logging.getLogger(__name__)


def _normalize_sqlalchemy_scheme(database_url: str) -> str:
    """
    Приводит URL к базовому виду `postgresql://...`.

    Это нужно, чтобы случайно не передать в синхронный SQLAlchemy URL вроде
    `postgresql+asyncpg://...`. Дальше уже централизованно применяем нужный
    sync-драйвер через `DB_DRIVER`.
    """
    prefixes = (
        "postgresql+asyncpg://",
        "postgresql+psycopg://",
        "postgresql+psycopg2://",
        "postgresql+pg8000://",
    )

    for prefix in prefixes:
        if database_url.startswith(prefix):
            return database_url.replace(prefix, "postgresql://", 1)

    return database_url


def _apply_sqlalchemy_driver(database_url: str) -> str:
    """
    Явно выбирает драйвер SQLAlchemy для PostgreSQL.

    Это позволяет без переписывания `.env` переключаться между `psycopg2`,
    `psycopg` v3 и `pg8000`. Для Neon это удобно, потому что часть Windows-
    окружений нестабильно работает именно на `psycopg2-binary`, а с `psycopg`
    подключение проходит нормально.
    """
    if not database_url.startswith("postgresql://"):
        return database_url

    driver_map = {
        "psycopg2": "postgresql+psycopg2://",
        "psycopg": "postgresql+psycopg://",
        "pg8000": "postgresql+pg8000://",
    }
    prefix = driver_map.get(settings.DB_DRIVER, "postgresql+psycopg2://")
    converted_url = database_url.replace("postgresql://", prefix, 1)

    if converted_url != database_url:
        print(f"[INFO] Для SQLAlchemy выбран драйвер PostgreSQL: {settings.DB_DRIVER}.")

    return converted_url


def _patch_psycopg_dialect_for_neon(database_url: str) -> None:
    """
    Включает безопасную инициализацию PostgreSQL-диалекта для Neon + psycopg.

    Практически проблема выглядит так:
    1. прямой `psycopg.connect(...)` к Neon проходит;
    2. но `SQLAlchemy + postgresql+psycopg` падает ещё на внутренней
       инициализации диалекта (`current_schema()`, fetch type info, rollback).

    Для нашего проекта это не критично: нам не нужна рефлексия схемы или
    сложная introspection-магия, нужен обычный ORM CRUD. Поэтому безопасно
    проставляем базовые значения диалекта вручную и пропускаем проблемную
    автоинициализацию.
    """
    host = urlsplit(database_url).hostname or ""
    if settings.DB_DRIVER != "psycopg" or "neon.tech" not in host:
        return

    def safe_initialize(self, connection):
        self.server_version_info = (15, 0)
        self.default_schema_name = "public"
        self.default_isolation_level = "READ COMMITTED"
        self.supports_smallserial = True
        self.supports_identity_columns = True
        self._supports_drop_index_concurrently = True
        self._backslash_escapes = False
        self.insert_executemany_returning = self.insert_returning

    PGDialect_psycopg.initialize = safe_initialize
    print("[INFO] Для SQLAlchemy включён безопасный режим инициализации PostgreSQL-диалекта (Neon + psycopg).")


def _normalize_database_url(database_url: str) -> str:
    """
    Нормализует строку подключения для SQLAlchemy/psycopg2.

    Для Neon pooled endpoint'ов параметр `channel_binding=require` может
    конфликтовать с некоторыми сборками `psycopg2-binary` и приводить к
    внезапному обрыву соединения ещё на этапе инициализации dialect.
    `psql` при этом может подключаться нормально.

    Поэтому для Python-драйвера аккуратно убираем только этот параметр,
    не трогая `sslmode=require`.
    """
    if "channel_binding=" not in database_url:
        return database_url

    parts = urlsplit(database_url)
    query_items = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "channel_binding"]
    normalized_query = urlencode(query_items, doseq=True)
    normalized_url = urlunsplit((parts.scheme, parts.netloc, parts.path, normalized_query, parts.fragment))

    if normalized_url != database_url:
        print("[INFO] DATABASE_URL нормализован для SQLAlchemy: параметр channel_binding удалён")

    return normalized_url


def _adapt_database_url_for_selected_driver(database_url: str) -> str:
    """
    Убирает из URL параметры, которые не поддерживает выбранный DB-драйвер.

    Для `pg8000` SQLAlchemy передаёт query-параметры прямо в `pg8000.connect`.
    Этот драйвер не понимает libpq-параметры вроде `sslmode` и `options`,
    поэтому такие значения нужно удалить до создания engine.
    """
    if settings.DB_DRIVER != "pg8000":
        return database_url

    parts = urlsplit(database_url)
    removed_keys: list[str] = []
    query_items: list[tuple[str, str]] = []

    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key in {"sslmode", "options"}:
            removed_keys.append(key)
            continue
        query_items.append((key, value))

    normalized_query = urlencode(query_items, doseq=True)
    normalized_url = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, normalized_query, parts.fragment)
    )

    if removed_keys:
        print(
            "[INFO] Для pg8000 удалены неподдерживаемые параметры URL: "
            + ", ".join(removed_keys)
            + "."
        )

    return normalized_url


def _prefer_direct_neon_url(database_url: str) -> str:
    """
    Переключает основной SQLAlchemy engine на direct URL только по явному флагу.

    По умолчанию backend должен продолжать работать на обычном `DATABASE_URL`
    (часто это pooled endpoint). `DATABASE_URL_DIRECT` держим отдельно:
    1. для runtime schema patches;
    2. для основного engine только если явно включён
       `PREFER_DIRECT_DATABASE_URL=true`.
    """
    if settings.PREFER_DIRECT_DATABASE_URL and settings.DATABASE_URL_DIRECT:
        print("[INFO] Для основного SQLAlchemy engine используется DATABASE_URL_DIRECT.")
        return settings.DATABASE_URL_DIRECT

    if settings.PREFER_DIRECT_DATABASE_URL and not settings.DATABASE_URL_DIRECT:
        print(
            "[INFO] PREFER_DIRECT_DATABASE_URL=true, но DATABASE_URL_DIRECT не задан. "
            "Используется DATABASE_URL как есть."
        )

    return database_url


def _ensure_neon_endpoint_option(database_url: str) -> str:
    """
    Добавляет `options=endpoint%3D...` для Neon, если параметр ещё не передан.

    Это полезно для клиентов, у которых бывают проблемы с SNI при TLS-подключении.
    """
    parts = urlsplit(database_url)
    host = parts.hostname or ""

    if "neon.tech" not in host:
        return database_url

    query_items = parse_qsl(parts.query, keep_blank_values=True)
    if any(key == "options" for key, _ in query_items):
        return database_url

    endpoint_id = host.split(".", 1)[0].replace("-pooler", "")
    if not endpoint_id.startswith("ep-"):
        return database_url

    query_items.append(("options", f"endpoint={endpoint_id}"))
    normalized_query = urlencode(query_items, doseq=True)
    normalized_url = urlunsplit((parts.scheme, parts.netloc, parts.path, normalized_query, parts.fragment))

    print(f"[INFO] Для Neon добавлен параметр options=endpoint={endpoint_id}.")
    return normalized_url


DATABASE_URL = _apply_sqlalchemy_driver(
    _adapt_database_url_for_selected_driver(
        _ensure_neon_endpoint_option(
            _normalize_database_url(
                _normalize_sqlalchemy_scheme(
                    _prefer_direct_neon_url(settings.DATABASE_URL)
                )
            )
        )
    )
)

_patch_psycopg_dialect_for_neon(DATABASE_URL)


def _build_engine_kwargs(database_url: str) -> dict:
    """
    Собирает параметры движка под конкретный тип PostgreSQL endpoint.

    Для Neon-соединений в этом проекте безопаснее не держать клиентский пул
    SQLAlchemy. Практический эффект мы уже наблюдаем: повторное использование
    одного и того же соединения может приводить к внезапному обрыву со стороны
    сервера, тогда как новые соединения отрабатывают стабильно. Поэтому для
    всех `neon.tech` endpoint'ов переводим SQLAlchemy в `NullPool`.
    """
    connect_args = {
        "application_name": "kai_dorm_api",
    }

    if settings.DB_DRIVER == "pg8000":
        connect_args["timeout"] = 10
    else:
        connect_args["connect_timeout"] = 10

    engine_kwargs = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }

    host = urlsplit(database_url).hostname or ""
    is_neon = "neon.tech" in host

    if is_neon:
        engine_kwargs["poolclass"] = NullPool
        print("[INFO] Обнаружен Neon PostgreSQL endpoint. SQLAlchemy переведён в NullPool.")

    if settings.DB_DRIVER == "psycopg" and is_neon:
        engine_kwargs["connect_args"]["prepare_threshold"] = None
        print("[INFO] Для Neon + psycopg отключены prepared statements (psycopg prepare_threshold=None).")

    if settings.DB_DRIVER == "pg8000" and is_neon:
        engine_kwargs["connect_args"]["ssl_context"] = True
        print("[INFO] Для Neon + pg8000 включён ssl_context.")

    return engine_kwargs

# Создаём движок для подключения к базе.
# echo=settings.DEBUG включает SQL-логирование только в разработке.
engine = create_engine(
    DATABASE_URL,
    **_build_engine_kwargs(DATABASE_URL),
)

# Создаем фабрику сессий
# expire_on_commit=False нужен, чтобы после commit() в конце запроса
# объекты не "протухали" перед сериализацией ответа.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)

def init_db():
    """
    Инициализация схемы БД.

    По умолчанию автоматическое `create_all()` отключено, потому что в проекте
    используется заранее подготовленная PostgreSQL-схема. Это безопаснее для
    production/staging и не требует DDL-операций на каждом старте приложения.
    """
    if not settings.AUTO_CREATE_TABLES:
        print("[INFO] AUTO_CREATE_TABLES=false, автоматическое создание таблиц пропущено")
    else:
        Base.metadata.create_all(bind=engine)

    if not settings.ENABLE_RUNTIME_SCHEMA_PATCHES:
        print(
            "[INFO] ENABLE_RUNTIME_SCHEMA_PATCHES=false, runtime schema patches пропущены. "
            "Ожидается, что схема уже обновлена вручную."
        )
        return

    _apply_runtime_schema_patches()


def _session_has_pending_writes(db) -> bool:
    return bool(db.new or db.dirty or db.deleted)


def _invalidate_session_safely(db, *, reason: str) -> None:
    try:
        db.invalidate()
    except Exception:
        logger.exception("Failed to invalidate DB session cleanly (%s).", reason)


def _normalize_sqlalchemy_database_url(database_url: str) -> str:
    """
    Нормализует и подготавливает PostgreSQL URL для SQLAlchemy.
    """
    normalized_url = _apply_sqlalchemy_driver(
        _adapt_database_url_for_selected_driver(
            _ensure_neon_endpoint_option(
                _normalize_database_url(
                    _normalize_sqlalchemy_scheme(database_url)
                )
            )
        )
    )

    _patch_psycopg_dialect_for_neon(normalized_url)
    return normalized_url


def _get_runtime_schema_patch_database_url() -> str:
    """
    Возвращает URL для runtime DDL-патчей.

    Для Neon DDL надёжнее выполнять через direct endpoint. Поэтому:
    1. если задан `DATABASE_URL_DIRECT`, используем его;
    2. иначе падаем обратно на основной `DATABASE_URL`, но предупреждаем,
       если это pooled Neon endpoint.
    """
    raw_database_url = settings.DATABASE_URL_DIRECT or settings.DATABASE_URL

    if settings.DATABASE_URL_DIRECT:
        print("[INFO] Для runtime schema patches используется DATABASE_URL_DIRECT.")
    else:
        host = urlsplit(raw_database_url).hostname or ""
        if "neon.tech" in host and "-pooler" in host:
            print(
                "[WARN] Runtime schema patches выполняются через pooled Neon endpoint. "
                "Для гарантированного DDL рекомендуется задать DATABASE_URL_DIRECT."
            )

    return _normalize_sqlalchemy_database_url(raw_database_url)


def _get_runtime_schema_patch_database_urls() -> list[tuple[str, str]]:
    """
    Возвращает кандидаты URL для DDL-патчей в порядке предпочтения.
    """
    candidates: list[tuple[str, str]] = []

    if settings.DATABASE_URL_DIRECT:
        print("[INFO] Для runtime schema patches используется DATABASE_URL_DIRECT.")
        candidates.append(
            ("DATABASE_URL_DIRECT", _normalize_sqlalchemy_database_url(settings.DATABASE_URL_DIRECT))
        )

    primary_url = _normalize_sqlalchemy_database_url(settings.DATABASE_URL)
    if not candidates or candidates[-1][1] != primary_url:
        host = urlsplit(settings.DATABASE_URL).hostname or ""
        if "neon.tech" in host and "-pooler" in host:
            print(
                "[INFO] Для runtime schema patches также подготовлен fallback на pooled DATABASE_URL."
            )
        candidates.append(("DATABASE_URL", primary_url))

    return candidates


def _build_runtime_schema_patch_engine(database_url: str):
    """
    Создаёт отдельный движок под короткие DDL-операции.

    Используем `AUTOCOMMIT` и `NullPool`, чтобы каждый `ALTER/CREATE INDEX`
    шёл в новом соединении и не зависел от длинной общей транзакции.
    """
    engine_kwargs = _build_engine_kwargs(database_url)
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["isolation_level"] = "AUTOCOMMIT"
    return create_engine(
        database_url,
        **engine_kwargs,
    )


def _execute_runtime_schema_statement(patch_engine, label: str, statement: str) -> None:
    """
    Выполняет один DDL-патч с повторным подключением при обрыве соединения.
    """
    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            with patch_engine.connect() as connection:
                connection.execute(text(statement))
            logger.info("Runtime schema patch applied: %s", label)
            return
        except OperationalError as exc:
            last_error = exc
            logger.warning(
                "Runtime schema patch '%s' failed on attempt %s/3. Retrying with a fresh connection.",
                label,
                attempt,
                exc_info=True,
            )
            time.sleep(0.35 * attempt)
        except SQLAlchemyError as exc:
            last_error = exc
            logger.exception("Runtime schema patch '%s' failed.", label)
            break

    if last_error is not None:
        raise RuntimeError(f"Runtime schema patch failed: {label}") from last_error


def _verify_runtime_schema_patches(patch_engine) -> None:
    """
    Проверяет, что обязательные runtime-колонки после старта действительно есть.
    """
    required_columns_by_table = {
        "rental_listings": {
            "category_id",
            "status",
            "pickup_location",
            "minimum_rental_period_text",
            "contact_name",
            "contact_value",
            "contact_note",
        },
        "news": {
            "calendar_start_at",
            "calendar_end_at",
        },
        "calendar_events": {
            "related_event_id",
        },
    }

    with patch_engine.connect() as connection:
        missing_messages: list[str] = []
        for table_name, required_columns in required_columns_by_table.items():
            rows = connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = :table_name
                    """
                ),
                {"table_name": table_name},
            )
            existing_columns = {row[0] for row in rows}
            missing_columns = sorted(required_columns - existing_columns)
            if missing_columns:
                missing_messages.append(f"{table_name}: {', '.join(missing_columns)}")

    if missing_messages:
        raise RuntimeError(
            "Runtime schema patches did not finish successfully. Missing columns: "
            + "; ".join(missing_messages)
        )


def _schema_supports_runtime_rental_features(check_engine) -> bool:
    try:
        _verify_runtime_schema_patches(check_engine)
        return True
    except Exception:
        return False


def _apply_runtime_schema_patches() -> None:
    """
    Небольшие идемпотентные DDL-патчи для локальной разработки.

    В проекте пока нет полноценной системы миграций, поэтому для новых полей
    rental market поддерживаем совместимость схемы на старых БД без ручного SQL.
    """
    statements = [
        (
            "add rental_listings.category_id",
            """
            ALTER TABLE rental_listings
            ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL
            """,
        ),
        (
            "add rental_listings.status",
            """
            ALTER TABLE rental_listings
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'approved'
            """,
        ),
        (
            "add rental_listings.pickup_location",
            """
            ALTER TABLE rental_listings
            ADD COLUMN IF NOT EXISTS pickup_location VARCHAR(255)
            """,
        ),
        (
            "add rental_listings.minimum_rental_period_text",
            """
            ALTER TABLE rental_listings
            ADD COLUMN IF NOT EXISTS minimum_rental_period_text VARCHAR(120)
            """,
        ),
        (
            "add rental_listings.contact_name",
            """
            ALTER TABLE rental_listings
            ADD COLUMN IF NOT EXISTS contact_name VARCHAR(120)
            """,
        ),
        (
            "add rental_listings.contact_value",
            """
            ALTER TABLE rental_listings
            ADD COLUMN IF NOT EXISTS contact_value VARCHAR(255)
            """,
        ),
        (
            "add rental_listings.contact_note",
            """
            ALTER TABLE rental_listings
            ADD COLUMN IF NOT EXISTS contact_note TEXT
            """,
        ),
        (
            "create idx_rental_listings_category_id",
            """
            CREATE INDEX IF NOT EXISTS idx_rental_listings_category_id
            ON rental_listings(category_id)
            """,
        ),
        (
            "create idx_rental_listings_status",
            """
            CREATE INDEX IF NOT EXISTS idx_rental_listings_status
            ON rental_listings(status)
            """,
        ),
        (
            "create idx_rental_listings_created_at",
            """
            CREATE INDEX IF NOT EXISTS idx_rental_listings_created_at
            ON rental_listings(created_at DESC)
            """,
        ),
        (
            "seed rental categories",
            """
            INSERT INTO categories (name, entity_type) VALUES
                ('Техника', 'product'),
                ('Инструменты', 'product'),
                ('Учеба', 'product'),
                ('Спорт', 'product'),
                ('Мебель', 'product'),
                ('Другое', 'product')
            ON CONFLICT (name, entity_type) DO NOTHING
            """,
        ),
        (
            "add news.calendar_start_at",
            """
            ALTER TABLE news
            ADD COLUMN IF NOT EXISTS calendar_start_at TIMESTAMP NULL
            """,
        ),
        (
            "add news.calendar_end_at",
            """
            ALTER TABLE news
            ADD COLUMN IF NOT EXISTS calendar_end_at TIMESTAMP NULL
            """,
        ),
        (
            "create idx_news_calendar_start_at",
            """
            CREATE INDEX IF NOT EXISTS idx_news_calendar_start_at
            ON news(calendar_start_at)
            """,
        ),
        (
            "create idx_news_dormitory_calendar_start_at",
            """
            CREATE INDEX IF NOT EXISTS idx_news_dormitory_calendar_start_at
            ON news(dormitory_id, calendar_start_at)
            """,
        ),
        (
            "add chk_news_calendar_dates",
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'chk_news_calendar_dates'
                ) THEN
                    ALTER TABLE news
                    ADD CONSTRAINT chk_news_calendar_dates
                    CHECK (
                        calendar_end_at IS NULL
                        OR calendar_start_at IS NULL
                        OR calendar_end_at >= calendar_start_at
                    );
                END IF;
            END
            $$;
            """,
        ),
        (
            "add calendar_events.related_event_id",
            """
            ALTER TABLE calendar_events
            ADD COLUMN IF NOT EXISTS related_event_id INTEGER REFERENCES events(id) ON DELETE SET NULL
            """,
        ),
        (
            "create idx_calendar_events_related_event_id",
            """
            CREATE INDEX IF NOT EXISTS idx_calendar_events_related_event_id
            ON calendar_events(related_event_id)
            """,
        ),
        (
            "ensure fk_calendar_events_related_event_id",
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'calendar_events'
                      AND column_name = 'related_event_id'
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint c
                    JOIN pg_attribute a
                      ON a.attrelid = c.conrelid
                     AND a.attnum = ANY(c.conkey)
                    WHERE c.conrelid = 'calendar_events'::regclass
                      AND c.contype = 'f'
                      AND a.attname = 'related_event_id'
                ) THEN
                    ALTER TABLE calendar_events
                    ADD CONSTRAINT fk_calendar_events_related_event_id
                    FOREIGN KEY (related_event_id)
                    REFERENCES events(id)
                    ON DELETE SET NULL;
                END IF;
            END
            $$;
            """,
        ),
        (
            "update chk_calendar_events_source",
            """
            ALTER TABLE calendar_events
            DROP CONSTRAINT IF EXISTS chk_calendar_events_source
            """,
        ),
        (
            "add chk_calendar_events_source",
            """
            ALTER TABLE calendar_events
            ADD CONSTRAINT chk_calendar_events_source
            CHECK (source_type IN ('manual', 'duty_generated', 'news_generated', 'event_generated'))
            """,
        ),
    ]

    last_error: Exception | None = None

    for source_name, database_url in _get_runtime_schema_patch_database_urls():
        patch_engine = _build_runtime_schema_patch_engine(database_url)
        try:
            for label, statement in statements:
                _execute_runtime_schema_statement(patch_engine, label, statement)

            _verify_runtime_schema_patches(patch_engine)
            print(f"[INFO] Runtime schema patches applied successfully via {source_name}.")
            return
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Runtime schema patches via %s failed. Trying next available connection strategy.",
                source_name,
                exc_info=True,
            )

            if _schema_supports_runtime_rental_features(patch_engine):
                print(
                    f"[WARN] Runtime schema patch execution via {source_name} failed, "
                    "but required rental schema is already present. Startup will continue."
                )
                return
        finally:
            patch_engine.dispose()

    if _schema_supports_runtime_rental_features(engine):
        print(
            "[WARN] Runtime schema patches were skipped because DDL connections were unavailable, "
            "but required rental schema is already present. Startup will continue."
        )
        return

    logger.exception("Failed to apply runtime schema patches.")
    if last_error is not None:
        raise RuntimeError("Runtime schema patches failed for all connection strategies.") from last_error
    raise RuntimeError("Runtime schema patches failed before any connection strategy could complete.")

# Зависимость для FastAPI: предоставляет сессию для каждого запроса
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        if db.in_transaction():
            try:
                db.rollback()
            except SQLAlchemyError:
                logger.exception("Failed to rollback DB session.")
                _invalidate_session_safely(db, reason="rollback failure after request exception")
        raise
    finally:
        session_invalidated = False
        try:
            if db.in_transaction():
                if _session_has_pending_writes(db):
                    logger.warning(
                        "DB session finished with uncommitted changes. Rolling back pending transaction."
                    )
                    try:
                        db.rollback()
                    except SQLAlchemyError:
                        logger.exception("Failed to rollback DB session during finalization.")
                        _invalidate_session_safely(
                            db,
                            reason="rollback failure during finalization",
                        )
                        session_invalidated = True
                else:
                    _invalidate_session_safely(
                        db,
                        reason="read-only transaction finalization",
                    )
                    session_invalidated = True

            if not session_invalidated:
                db.close()
        except SQLAlchemyError:
            # Broken DB connection should not crash HTTP response finalization.
            logger.exception("Failed to close DB session cleanly; invalidating session.")
            _invalidate_session_safely(db, reason="close failure")

# Экспорт для использования в других модулях
__all__ = ["engine", "SessionLocal", "get_db", "Base", "init_db"]
