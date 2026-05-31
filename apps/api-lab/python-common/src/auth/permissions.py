import uuid

from auth.models import AuthenticatedUser


class PermissionDeniedError(Exception):
    def __init__(self, user: AuthenticatedUser, resource: str, action: str):
        self.user = user
        self.resource = resource
        self.action = action
        super().__init__(f"User {user.username} cannot {action} {resource}")


def check_permission(
    user: AuthenticatedUser,
    resource_type: str,
    _resource_id: uuid.UUID | None,
    action: str,
    owner_id: uuid.UUID | None = None,
) -> None:
    if user.is_admin:
        return

    if resource_type == "book":
        if action == "read":
            return
        raise PermissionDeniedError(user, resource_type, action)

    if resource_type == "reservation":
        if action == "create":
            return
        if action in ("read", "update") and owner_id == user.sub:
            return
        raise PermissionDeniedError(user, resource_type, action)

    raise PermissionDeniedError(user, resource_type, action)
