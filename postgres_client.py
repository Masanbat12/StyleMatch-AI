from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

try:
    from psycopg import OperationalError, connect, sql
    from psycopg.errors import InvalidCatalogName, UniqueViolation
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - handled gracefully at runtime
    class OperationalError(Exception):
        pass

    class InvalidCatalogName(Exception):
        pass

    class UniqueViolation(Exception):
        pass

    connect = None
    dict_row = None
    Jsonb = lambda value: value  # type: ignore[assignment]
    sql = None


class PostgresConfigurationError(RuntimeError):
    pass


_resolved_conninfo: str | None = None
_schema_ready = False
DEFAULT_POSTGRES_PORT = "5432"


def _is_wsl_runtime() -> bool:
    release = platform.uname().release.lower()
    return "microsoft" in release or "wsl" in release


def _get_wsl_host_candidates() -> list[str]:
    candidates: list[str] = []
    resolv_conf = Path("/etc/resolv.conf")
    if resolv_conf.exists():
        try:
            for line in resolv_conf.read_text(encoding="utf-8").splitlines():
                if not line.startswith("nameserver "):
                    continue
                _, ip_address = line.split(maxsplit=1)
                ip_address = ip_address.strip()
                if ip_address and ip_address not in candidates:
                    candidates.append(ip_address)
        except OSError:
            pass

    for host in ("host.docker.internal",):
        if host not in candidates:
            candidates.append(host)

    return candidates


def _build_conninfo(host: str, port: str, dbname: str, user: str, password: str | None) -> str:
    credentials = quote(user)
    if password:
        credentials = f"{credentials}:{quote(password)}"
    return f"postgresql://{credentials}@{host}:{port}/{quote(dbname)}"


def _build_candidate_conninfos() -> list[str]:
    explicit_conninfo = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    if explicit_conninfo:
        return [explicit_conninfo]

    configured_host = os.getenv("POSTGRES_HOST")
    if configured_host:
        host_candidates = [configured_host]
    elif _is_wsl_runtime():
        host_candidates = _get_wsl_host_candidates() + ["localhost"]
    else:
        host_candidates = ["localhost"]

    port = os.getenv("POSTGRES_PORT", DEFAULT_POSTGRES_PORT)
    dbname = os.getenv("POSTGRES_DB", "stylematch_ai")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD")

    unique_conninfos: list[str] = []
    for host in host_candidates:
        conninfo = _build_conninfo(host, port, dbname, user, password)
        if conninfo not in unique_conninfos:
            unique_conninfos.append(conninfo)
    return unique_conninfos


def coerce_account_id(user_id: str | int) -> int:
    try:
        return int(str(user_id))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Authenticated persistence requires a numeric account id, got {user_id!r}.") from exc


def _host_from_conninfo(conninfo: str) -> str:
    parsed = urlparse(conninfo)
    return parsed.hostname or "localhost"


def _port_from_conninfo(conninfo: str) -> int:
    parsed = urlparse(conninfo)
    return parsed.port or int(DEFAULT_POSTGRES_PORT)


def _database_from_conninfo(conninfo: str) -> str:
    parsed = urlparse(conninfo)
    return parsed.path.lstrip("/") or "stylematch_ai"


def _maintenance_conninfo(conninfo: str) -> str:
    parsed = urlparse(conninfo)
    return parsed._replace(path="/postgres").geturl()


def _format_connection_error(conninfo: str, exc: Exception) -> str:
    host = _host_from_conninfo(conninfo)
    port = _port_from_conninfo(conninfo)
    database_name = _database_from_conninfo(conninfo)
    base_message = f"Could not connect to PostgreSQL at {host}:{port} for database '{database_name}'."

    if _is_wsl_runtime() and host in {"localhost", "127.0.0.1"}:
        return (
            f"{base_message} WSL may not be able to reach the Windows PostgreSQL service through localhost "
            "in the current setup. Configure POSTGRES_DSN/DATABASE_URL or expose PostgreSQL to the WSL host."
        )

    return f"{base_message} {exc}"


def _create_database_if_missing(conninfo: str) -> bool:
    if connect is None or sql is None:
        return False

    database_name = _database_from_conninfo(conninfo)
    maintenance_conninfo = _maintenance_conninfo(conninfo)

    try:
        with connect(maintenance_conninfo, autocommit=True, row_factory=dict_row, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
                if cursor.fetchone():
                    return True
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
                return True
    except Exception:
        return False


def get_connection():
    global _resolved_conninfo

    if connect is None:
        raise PostgresConfigurationError(
            "PostgreSQL support requires the 'psycopg' package. Install requirements.txt first."
        )

    candidate_conninfos = [_resolved_conninfo] if _resolved_conninfo else []
    candidate_conninfos.extend(
        conninfo
        for conninfo in _build_candidate_conninfos()
        if conninfo not in candidate_conninfos
    )

    last_error: Exception | None = None
    for conninfo in candidate_conninfos:
        try:
            connection = connect(conninfo, autocommit=True, row_factory=dict_row, connect_timeout=3)
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            _resolved_conninfo = conninfo
            return connection
        except InvalidCatalogName as exc:
            if _create_database_if_missing(conninfo):
                try:
                    connection = connect(conninfo, autocommit=True, row_factory=dict_row, connect_timeout=3)
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                    _resolved_conninfo = conninfo
                    return connection
                except OperationalError as retry_exc:
                    last_error = retry_exc
                    continue
            last_error = exc
        except OperationalError as exc:
            last_error = exc

    attempted = ", ".join(candidate_conninfos)
    if last_error is None:
        raise PostgresConfigurationError("PostgreSQL connection failed before any DSN could be attempted.")

    raise PostgresConfigurationError(
        f"{_format_connection_error(candidate_conninfos[-1], last_error)} Attempted: {attempted}."
    ) from last_error


def ensure_schema() -> None:
    global _schema_ready

    if _schema_ready:
        return

    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            last_login_at TIMESTAMPTZ
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            username TEXT,
            current_inferred_skin_tone TEXT,
            current_inferred_undertone TEXT,
            skin_profile_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
            skin_analysis_count INTEGER NOT NULL DEFAULT 0,
            historical_skin_tone_estimates JSONB NOT NULL DEFAULT '[]'::jsonb,
            historical_undertone_estimates JSONB NOT NULL DEFAULT '[]'::jsonb,
            preferred_color_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
            disliked_color_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
            slot_color_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
            preferred_style_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
            preferred_occasion_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
            interaction_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
            confidence_signals JSONB NOT NULL DEFAULT '{}'::jsonb,
            insights JSONB NOT NULL DEFAULT '{}'::jsonb,
            last_updated_at TIMESTAMPTZ NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS user_feedback (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            username TEXT,
            action TEXT NOT NULL,
            profile JSONB NOT NULL,
            outfit JSONB NOT NULL,
            source TEXT NOT NULL,
            original_outfit JSONB,
            refined_outfit JSONB,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS skin_analysis_history (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            username TEXT,
            skin_tone TEXT NOT NULL,
            undertone TEXT NOT NULL,
            confidence DOUBLE PRECISION NOT NULL,
            confidence_label TEXT,
            brightness DOUBLE PRECISION,
            dominant_skin_hex TEXT,
            sample_pixel_count INTEGER,
            quality_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
            warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
            note TEXT,
            analyzed_at TIMESTAMPTZ NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS saved_looks (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            username TEXT,
            profile JSONB NOT NULL,
            outfit JSONB NOT NULL,
            source TEXT NOT NULL,
            explanation TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            saved_at TIMESTAMPTZ NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_user_created_at ON user_feedback(user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_user_action ON user_feedback(user_id, action)",
        "CREATE INDEX IF NOT EXISTS idx_skin_analysis_history_user_analyzed_at ON skin_analysis_history(user_id, analyzed_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_saved_looks_user_saved_at ON saved_looks(user_id, saved_at DESC)",
    ]

    migration_statements = [
        """
        DELETE FROM user_preferences
        WHERE user_id IS NULL OR user_id::text !~ '^[0-9]+$'
        """,
        """
        DELETE FROM user_feedback
        WHERE user_id IS NULL OR user_id::text !~ '^[0-9]+$'
        """,
        """
        DELETE FROM skin_analysis_history
        WHERE user_id IS NULL OR user_id::text !~ '^[0-9]+$'
        """,
        """
        DELETE FROM saved_looks
        WHERE user_id IS NULL OR user_id::text !~ '^[0-9]+$'
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'user_preferences'
                  AND column_name = 'user_id'
                  AND data_type <> 'bigint'
            ) THEN
                ALTER TABLE user_preferences
                ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'user_feedback'
                  AND column_name = 'user_id'
                  AND data_type <> 'bigint'
            ) THEN
                ALTER TABLE user_feedback
                ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'skin_analysis_history'
                  AND column_name = 'user_id'
                  AND data_type <> 'bigint'
            ) THEN
                ALTER TABLE skin_analysis_history
                ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'saved_looks'
                  AND column_name = 'user_id'
                  AND data_type <> 'bigint'
            ) THEN
                ALTER TABLE saved_looks
                ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            ALTER TABLE user_preferences
            DROP CONSTRAINT IF EXISTS user_preferences_user_id_fkey;
            ALTER TABLE user_preferences
            ADD CONSTRAINT user_preferences_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """,
        """
        DO $$
        BEGIN
            ALTER TABLE user_feedback
            DROP CONSTRAINT IF EXISTS user_feedback_user_id_fkey;
            ALTER TABLE user_feedback
            ADD CONSTRAINT user_feedback_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """,
        """
        DO $$
        BEGIN
            ALTER TABLE skin_analysis_history
            DROP CONSTRAINT IF EXISTS skin_analysis_history_user_id_fkey;
            ALTER TABLE skin_analysis_history
            ADD CONSTRAINT skin_analysis_history_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """,
        """
        DO $$
        BEGIN
            ALTER TABLE saved_looks
            DROP CONSTRAINT IF EXISTS saved_looks_user_id_fkey;
            ALTER TABLE saved_looks
            ADD CONSTRAINT saved_looks_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """,
    ]

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
            for statement in migration_statements:
                cursor.execute(statement)

    _schema_ready = True
