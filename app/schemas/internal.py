from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

@dataclass
class ItemResponse[T]:
    message: str
    data: T
    success: bool = True
    meta: dict[str, Any] | None = None

@dataclass
class ListResponse[T]:
    message: str
    data: list[T]
    success: bool = True
    meta: dict[str, Any] | None = None

@dataclass
class ClientInfo:
    ip_address: str | None
    user_agent: str | None

class MessageType(StrEnum):
    Success = 'success'
    Info = 'info'
    Warning = 'warning'
    Error = 'error'

@dataclass
class AppMessage:
    type: MessageType
    message: str

    @classmethod
    def success(cls, text: str) -> 'AppMessage':
        return cls(type=MessageType.Success, message=text)

    @classmethod
    def info(cls, text: str) -> 'AppMessage':
        return cls(type=MessageType.Info, message=text)

    @classmethod
    def warning(cls, text: str) -> 'AppMessage':
        return cls(type=MessageType.Warning, message=text)

    @classmethod
    def error(cls, text: str) -> 'AppMessage':
        return cls(type=MessageType.Error, message=text)

    def dict(self) -> dict[str, Any]:
        return asdict(self)