from __future__ import annotations

from typing import Any

from supabase_client import SupabaseConfigurationError, get_supabase_auth_client


MIN_PASSWORD_LENGTH = 8
MIN_DISPLAY_NAME_LENGTH = 2


class AuthenticationError(ValueError):
    pass


def _normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if not cleaned:
        raise AuthenticationError("Email is required.")
    if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
        raise AuthenticationError("Enter a valid email address.")
    return cleaned


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthenticationError("Password must be at least 8 characters long.")


def _normalize_display_name(display_name: str) -> str:
    cleaned = display_name.strip()
    if len(cleaned) < MIN_DISPLAY_NAME_LENGTH:
        raise AuthenticationError("Nickname must be at least 2 characters long.")
    return cleaned


def _user_display_name(user: Any, fallback_email: str) -> str:
    metadata = getattr(user, "user_metadata", {}) or {}
    if isinstance(metadata, dict):
        display_name = metadata.get("display_name") or metadata.get("nickname")
        if display_name:
            return str(display_name)

    email = getattr(user, "email", None)
    if email:
        local_part = str(email).split("@", 1)[0].strip()
        if local_part:
            return local_part

    return fallback_email.split("@", 1)[0]


def _response_user(response: Any) -> Any:
    user = getattr(response, "user", None)
    if user is not None:
        return user

    session = getattr(response, "session", None)
    if session is not None:
        return getattr(session, "user", None)

    return None


class SupabaseAuthService:
    def __init__(self) -> None:
        self.client = get_supabase_auth_client()

    def register_user(self, email: str, password: str, display_name: str) -> dict[str, str]:
        normalized_email = _normalize_email(email)
        _validate_password(password)
        normalized_display_name = _normalize_display_name(display_name)

        try:
            response = self.client.auth.sign_up(
                {
                    "email": normalized_email,
                    "password": password,
                    "options": {
                        "data": {
                            "display_name": normalized_display_name,
                        }
                    },
                }
            )
        except Exception as exc:
            message = str(exc)
            if "Invalid path specified in request URL" in message:
                raise AuthenticationError(
                    "SUPABASE_URL is not set correctly. Use the Project URL from Supabase Settings -> API, "
                    "for example https://your-project-id.supabase.co"
                ) from exc
            if "User already registered" in message:
                raise AuthenticationError("That email is already registered.") from exc
            raise AuthenticationError(message) from exc

        user = _response_user(response)
        if user is None:
            raise AuthenticationError("The account could not be created.")

        if getattr(response, "session", None) is None:
            raise AuthenticationError(
                "Account created. Confirm the email in Supabase Auth settings or disable email confirmation for local testing."
            )

        return {
            "id": str(user.id),
            "username": _user_display_name(user, normalized_email),
        }

    def authenticate_user(self, email: str, password: str) -> dict[str, str]:
        normalized_email = _normalize_email(email)
        _validate_password(password)

        try:
            response = self.client.auth.sign_in_with_password(
                {
                    "email": normalized_email,
                    "password": password,
                }
            )
        except Exception as exc:
            message = str(exc)
            if "Invalid path specified in request URL" in message:
                raise AuthenticationError(
                    "SUPABASE_URL is not set correctly. Use the Project URL from Supabase Settings -> API, "
                    "for example https://your-project-id.supabase.co"
                ) from exc
            if "Email not confirmed" in message:
                raise AuthenticationError(
                    "This email is not confirmed yet. Open the confirmation email from Supabase, or disable email confirmation for local testing."
                ) from exc
            raise AuthenticationError("Incorrect email or password.") from exc

        user = _response_user(response)
        if user is None:
            raise AuthenticationError("Incorrect email or password.")

        return {
            "id": str(user.id),
            "username": _user_display_name(user, normalized_email),
        }


def auth_is_available() -> tuple[bool, str | None]:
    try:
        get_supabase_auth_client()
        return True, None
    except SupabaseConfigurationError as exc:
        return False, str(exc)
