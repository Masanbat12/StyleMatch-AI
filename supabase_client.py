from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import streamlit as st

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover - handled gracefully at runtime
    Client = Any  # type: ignore[misc,assignment]
    create_client = None


class SupabaseConfigurationError(RuntimeError):
    pass


def _clean_secret_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
        cleaned = cleaned[1:-1].strip()

    return cleaned or None


def _normalize_supabase_url(url: str | None) -> str | None:
    url = _clean_secret_text(url)
    if not url:
        return None

    cleaned = url.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SupabaseConfigurationError(
            "SUPABASE_URL must look like https://your-project-id.supabase.co"
        )

    path = parsed.path.rstrip("/")
    if path in {"", "/"}:
        return f"{parsed.scheme}://{parsed.netloc}"

    if path in {"/auth/v1", "/rest/v1", "/storage/v1"}:
        return f"{parsed.scheme}://{parsed.netloc}"

    raise SupabaseConfigurationError(
        "SUPABASE_URL should be the project base URL only, for example "
        "https://your-project-id.supabase.co. Do not use a dashboard URL or an /auth/v1 endpoint."
    )


def _secret_value(name: str) -> str | None:
    env_value = os.getenv(name)
    if env_value:
        return _clean_secret_text(env_value)

    try:
        if name in st.secrets:
            value = st.secrets[name]
            return _clean_secret_text(str(value) if value else None)
    except Exception:
        pass

    return None


def _secret_section_value(section: str, key: str) -> str | None:
    try:
        section_data = st.secrets.get(section)
        if not section_data:
            return None
        value = section_data.get(key)
        return _clean_secret_text(str(value) if value else None)
    except Exception:
        return None


def get_supabase_url() -> str | None:
    raw_url = _secret_value("SUPABASE_URL") or _secret_section_value("supabase", "url")
    return _normalize_supabase_url(raw_url)


def get_supabase_key() -> str | None:
    return (
        _secret_value("SUPABASE_SERVICE_ROLE_KEY")
        or _secret_section_value("supabase", "service_role_key")
        or _secret_value("SUPABASE_SECRET_KEY")
        or _secret_section_value("supabase", "secret_key")
        or _secret_value("SUPABASE_KEY")
        or _secret_section_value("supabase", "key")
        or _secret_value("SUPABASE_PUBLISHABLE_KEY")
        or _secret_section_value("supabase", "publishable_key")
        or _secret_value("SUPABASE_ANON_KEY")
        or _secret_section_value("supabase", "anon_key")
    )


def get_supabase_auth_key() -> str | None:
    return (
        _secret_value("SUPABASE_KEY")
        or _secret_section_value("supabase", "key")
        or _secret_value("SUPABASE_PUBLISHABLE_KEY")
        or _secret_section_value("supabase", "publishable_key")
        or _secret_value("SUPABASE_ANON_KEY")
        or _secret_section_value("supabase", "anon_key")
        or _secret_value("SUPABASE_SERVICE_ROLE_KEY")
        or _secret_section_value("supabase", "service_role_key")
        or _secret_value("SUPABASE_SECRET_KEY")
        or _secret_section_value("supabase", "secret_key")
    )


def supabase_is_configured() -> bool:
    return bool(get_supabase_url() and get_supabase_key())


def get_supabase() -> Client:
    if create_client is None:
        raise SupabaseConfigurationError(
            "Supabase support requires the 'supabase' package. Install requirements.txt first."
        )

    url = get_supabase_url()
    key = get_supabase_key()
    if not url or not key:
        raise SupabaseConfigurationError(
            "Supabase is not configured yet. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
            "to Streamlit secrets or environment variables."
        )

    return create_client(url, key)


def get_supabase_auth_client() -> Client:
    if create_client is None:
        raise SupabaseConfigurationError(
            "Supabase support requires the 'supabase' package. Install requirements.txt first."
        )

    url = get_supabase_url()
    key = get_supabase_auth_key()
    if not url or not key:
        raise SupabaseConfigurationError(
            "Supabase auth is not configured yet. Add SUPABASE_URL and SUPABASE_KEY or SUPABASE_ANON_KEY "
            "to Streamlit secrets or environment variables."
        )

    return create_client(url, key)
