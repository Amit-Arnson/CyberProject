import json
from dataclasses import dataclass
from typing import Any

methods = [
    "post",
    "get",
    "respond",
    "initiate",
]


class InputError(Exception):
    pass


@dataclass
class ServerMessage:
    """
    status: {"code": int, "message": str}
    method: post | get | respond | initiate
    endpoint: endpoint
    payload: json
    """
    status: dict[str, int | str] = None
    method: str = None
    endpoint: str = None
    payload: dict[str, Any] = None

    encoded: bytes = None

    def __post_init__(self):
        # if any of the following attributes are NOT none, it means the message isn't encoded. flipping this by adding a not
        # creates us a variable that checks if the message was **built** as encoded

        # no attribute should ever be none. due to this reason, it is safe to assume that if all of them are none it means
        # that the message is meant to be encoded
        has_all_attributes = any((self.status, self.method, self.endpoint, self.payload))
        should_be_encoded = not has_all_attributes

        if not self.encoded and should_be_encoded:
            raise AttributeError(f"expected encoded bytes but got {self.encoded} ({type(self.encoded)}) instead")

    def dictionary(self):
        return {
            "status": self.status,
            "method": self.method,
            "endpoint": self.endpoint,
            "payload": self.payload
        }

    def encode(self) -> bytes:
        """
        encodes the dumped values (in a json format) and returns the bytes
        """
        self.encoded = self.__str__().encode()
        return self.encoded

    def decode(self) -> dict[str, Any]:
        """
        returns the loaded json gotten from self.encoded.
        in addition, it replaces all the other attributes with the ones gotten from the loaded json.
        """
        if not self.encoded or not isinstance(self.encoded, bytes):
            raise AttributeError(f"expected encoded bytes but got {self.encoded} ({type(self.encoded)}) instead")

        decoded = self.encoded.decode()
        loaded_json = json.loads(decoded)

        self.status = loaded_json.get("status")
        self.endpoint = loaded_json.get("endpoint")
        self.method = loaded_json.get("method")
        self.payload = loaded_json.get("payload")

        return loaded_json

    def __str__(self) -> str:
        """
        returns a dumped json of all the values (with regard for ascii)
        """
        return json.dumps(self.dictionary(), ensure_ascii=False)
