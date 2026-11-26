from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from supabase_client import SupabaseConfigurationError, get_supabase


PROFILE_TABLE = "user_profiles"


class ProfileTableMissingError(RuntimeError):
    pass


@dataclass(slots=True)
class DuplicateProfileError(RuntimeError):
    field: str


def normalize_profile_username(username: str) -> str:
    return " ".join(username.strip().split()).casefold()


def normalize_profile_email(email: str) -> str:
    return email.strip().lower()


def _error_text(exc: Exception) -> str:
    return str(exc).lower()


def _is_missing_profile_table(exc: Exception) -> bool:
    message = _error_text(exc)
    return PROFILE_TABLE in message and (
        "could not find the table" in message
        or "relation" in message
        or "does not exist" in message
    )


def _duplicate_field(exc: Exception) -> str | None:
    message = _error_text(exc)
    if "duplicate" not in message and "23505" not in message:
        return None
    if "username_lower" in message or "username" in message:
        return "username"
    if "email_lower" in message or "email" in message:
        return "email"
    return "profile"


class SupabaseProfileRepository:
    def __init__(self) -> None:
        self.client = get_supabase()

    def ensure_signup_ready(self) -> None:
        try:
            self.client.table(PROFILE_TABLE).select("user_id").limit(1).execute()
        except Exception as exc:
            if _is_missing_profile_table(exc):
                raise ProfileTableMissingError(
                    "Supabase profile storage is not configured yet. Create the public.user_profiles table from the README."
                ) from exc
            raise

    def username_exists(self, username: str) -> bool:
        normalized = normalize_profile_username(username)
        try:
            response = (
                self.client.table(PROFILE_TABLE)
                .select("user_id")
                .eq("username_lower", normalized)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            if _is_missing_profile_table(exc):
                raise ProfileTableMissingError(
                    "Supabase profile storage is not configured yet. Create the public.user_profiles table from the README."
                ) from exc
            raise

        return bool(response.data)

    def get_by_user_id(self, user_id: str) -> dict[str, Any] | None:
        try:
            response = (
                self.client.table(PROFILE_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            if _is_missing_profile_table(exc):
                raise ProfileTableMissingError(
                    "Supabase profile storage is not configured yet. Create the public.user_profiles table from the README."
                ) from exc
            raise

        if not response.data:
            return None
        return dict(response.data[0])

    def upsert_profile(self, user_id: str, email: str, username: str) -> dict[str, Any]:
        payload = {
            "user_id": user_id,
            "email": email.strip(),
            "email_lower": normalize_profile_email(email),
            "username": username.strip(),
            "username_lower": normalize_profile_username(username),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        try:
            response = (
                self.client.table(PROFILE_TABLE)
                .upsert(payload, on_conflict="user_id")
                .execute()
            )
        except Exception as exc:
            if _is_missing_profile_table(exc):
                raise ProfileTableMissingError(
                    "Supabase profile storage is not configured yet. Create the public.user_profiles table from the README."
                ) from exc
            duplicate_field = _duplicate_field(exc)
            if duplicate_field:
                raise DuplicateProfileError(duplicate_field) from exc
            raise

        if not response.data:
            return payload
        return dict(response.data[0])
