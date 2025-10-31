from typing import Any

from fastapi import Request


class SessionService:
    def __init__(self, request: Request):
        self.session = request.session

    def set(self, key: str, value: Any) -> None:
        self.session[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.session.get(key, default)

    def pop(self, key: str, default: Any = None) -> Any:
        return self.session.pop(key, default)
