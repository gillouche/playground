import uuid

import pytest
from auth.models import AuthenticatedUser
from auth.permissions import PermissionDeniedError, check_permission


def _make_user(**kwargs):
    defaults = {
        "sub": uuid.uuid4(),
        "username": "testuser",
        "roles": ["user"],
        "email": "test@example.com",
    }
    defaults.update(kwargs)
    return AuthenticatedUser(**defaults)


def _make_admin(**kwargs):
    defaults = {
        "sub": uuid.uuid4(),
        "username": "admin",
        "roles": ["user", "admin"],
        "email": "admin@example.com",
    }
    defaults.update(kwargs)
    return AuthenticatedUser(**defaults)


class TestAdminPermissions:
    def test_admin_can_read_books(self):
        admin = _make_admin()
        check_permission(admin, "book", uuid.uuid4(), "read")

    def test_admin_can_create_books(self):
        admin = _make_admin()
        check_permission(admin, "book", None, "create")

    def test_admin_can_update_books(self):
        admin = _make_admin()
        check_permission(admin, "book", uuid.uuid4(), "update")

    def test_admin_can_delete_books(self):
        admin = _make_admin()
        check_permission(admin, "book", uuid.uuid4(), "delete")

    def test_admin_can_create_reservations(self):
        admin = _make_admin()
        check_permission(admin, "reservation", None, "create")

    def test_admin_can_read_any_reservation(self):
        admin = _make_admin()
        check_permission(admin, "reservation", uuid.uuid4(), "read", owner_id=uuid.uuid4())

    def test_admin_can_update_any_reservation(self):
        admin = _make_admin()
        check_permission(admin, "reservation", uuid.uuid4(), "update", owner_id=uuid.uuid4())

    def test_admin_can_delete_any_reservation(self):
        admin = _make_admin()
        check_permission(admin, "reservation", uuid.uuid4(), "delete", owner_id=uuid.uuid4())


class TestUserBookPermissions:
    def test_user_can_read_books(self):
        user = _make_user()
        check_permission(user, "book", uuid.uuid4(), "read")

    def test_user_cannot_create_books(self):
        user = _make_user()
        with pytest.raises(PermissionDeniedError):
            check_permission(user, "book", None, "create")

    def test_user_cannot_update_books(self):
        user = _make_user()
        with pytest.raises(PermissionDeniedError):
            check_permission(user, "book", uuid.uuid4(), "update")

    def test_user_cannot_delete_books(self):
        user = _make_user()
        with pytest.raises(PermissionDeniedError):
            check_permission(user, "book", uuid.uuid4(), "delete")


class TestUserReservationPermissions:
    def test_user_can_create_reservation(self):
        user = _make_user()
        check_permission(user, "reservation", None, "create")

    def test_user_can_read_own_reservation(self):
        user = _make_user()
        check_permission(user, "reservation", uuid.uuid4(), "read", owner_id=user.sub)

    def test_user_can_update_own_reservation(self):
        user = _make_user()
        check_permission(user, "reservation", uuid.uuid4(), "update", owner_id=user.sub)

    def test_user_cannot_read_others_reservation(self):
        user = _make_user()
        with pytest.raises(PermissionDeniedError):
            check_permission(user, "reservation", uuid.uuid4(), "read", owner_id=uuid.uuid4())

    def test_user_cannot_update_others_reservation(self):
        user = _make_user()
        with pytest.raises(PermissionDeniedError):
            check_permission(user, "reservation", uuid.uuid4(), "update", owner_id=uuid.uuid4())

    def test_user_cannot_delete_own_reservation(self):
        user = _make_user()
        with pytest.raises(PermissionDeniedError):
            check_permission(user, "reservation", uuid.uuid4(), "delete", owner_id=user.sub)


class TestUnknownResourceType:
    def test_user_denied_for_unknown_resource(self):
        user = _make_user()
        with pytest.raises(PermissionDeniedError):
            check_permission(user, "unknown", uuid.uuid4(), "read")

    def test_admin_allowed_for_unknown_resource(self):
        admin = _make_admin()
        check_permission(admin, "unknown", uuid.uuid4(), "read")
