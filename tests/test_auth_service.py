from __future__ import annotations

from auth_service import AuthService, AuthenticationError
from user_repository import DuplicateUserError


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[str, dict] = {}

    def ensure_indexes(self) -> None:
        return

    def find_by_username(self, username: str):
        return self.users.get(username)

    def find_by_id(self, user_id: str):
        for user in self.users.values():
            if user["id"] == user_id:
                return user
        return None

    def create_user(self, username: str, password_hash: str, password_salt: str):
        if username in self.users:
            raise DuplicateUserError("duplicate")
        user = {
            "id": f"user-{len(self.users) + 1}",
            "username": username,
            "password_hash": password_hash,
            "password_salt": password_salt,
        }
        self.users[username] = user
        return user

    def update_last_login(self, user_id: str) -> None:
        return


def test_register_and_authenticate_user():
    service = AuthService(user_repository=FakeUserRepository())

    created = service.register_user("StyleUser", "securepass123")
    authenticated = service.authenticate_user("styleuser", "securepass123")

    assert created["username"] == "styleuser"
    assert authenticated["username"] == "styleuser"
    assert authenticated["password_hash"] != "securepass123"


def test_authenticate_rejects_bad_password():
    service = AuthService(user_repository=FakeUserRepository())
    service.register_user("styleuser", "securepass123")

    try:
        service.authenticate_user("styleuser", "wrongpass")
    except AuthenticationError as exc:
        assert "Incorrect username or password." in str(exc)
    else:
        raise AssertionError("AuthenticationError was expected for an incorrect password.")
