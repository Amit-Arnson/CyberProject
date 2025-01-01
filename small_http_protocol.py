from dataclasses import dataclass
from typing import Any

methods = [
    "post",
    "get",
    "respond",
    "initiate",
]


@dataclass
class ServerMessage:
    """
    status: {"code": int, "message": str}
    method: post | get | respond | initiate
    route: endpoint
    payload: json
    """
    status: dict[str, int | str]
    method: str
    route: str
    payload: dict[str, Any]

    def dictionary(self):
        return {
            "status": {
                "code": self.status["code"],
                "message": self.status["message"]
            },
            "method": self.method,
            "route": self.route,
            "payload": self.payload
        }
    def __str__(self):
        pass
