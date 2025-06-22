from pydantic import EmailStr
from pydantic.dataclasses import dataclass

@dataclass(frozen=True)
class Command:
    ...


@dataclass(frozen=True)
class UserRegisterCommand(Command):
    username: str
    email: EmailStr
    password: str