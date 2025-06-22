from pydantic import EmailStr, Field
from pydantic.dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.core.correlation.context import get_correlation_id


@dataclass(kw_only=True)
class Event:
    source_service: str = "user"
    event_id: UUID = Field(default_factory=uuid4)
    correlation_id: str = Field(default_factory=get_correlation_id)
    timestamp: float = Field(default_factory=lambda: datetime.now(tz=timezone.utc).timestamp())


@dataclass(kw_only=True)
class IncomingEvent(Event):
    ...


@dataclass(kw_only=True)
class OutgoingEvent(Event):
    ...


@dataclass(kw_only=True)
class  UserEmailVerificationRequested(OutgoingEvent):
    userid: str
    username: str
    email: EmailStr
    event_type: str = "user.email_verification_requested"
