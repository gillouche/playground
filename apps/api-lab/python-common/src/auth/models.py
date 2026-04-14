import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthenticatedUser:
    sub: uuid.UUID
    username: str
    roles: list[str] = field(default_factory=list)
    email: str | None = None

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles
