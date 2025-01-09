import json
from dataclasses import dataclass
from typing import Any

methods = [
    "post",
    "get",
    "respond",
    "initiate",
]


@dataclass
class ClientMessage:
    """
    authentication: session token
    method: post | get | respond
    endpoint: endpoint route
    payload: json
    """

    authentication: str | None = None
    method: str = None
    endpoint: str = None
    payload: dict[str, Any] = None

    _encoded: bytes = None

    def _dictionary(self):
        return {
            "authentication": self.authentication,
            "method": self.method,
            "endpoint": self.endpoint,
            "payload": self.payload
        }

    def encode(self) -> bytes:
        """
        encodes the dumped values (in a json format) and returns the bytes
        """
        self._encoded = self.__str__().encode()
        return self._encoded

    def decode(self) -> dict[str, Any]:
        """
        returns the loaded json gotten from self.encoded.
        in addition, it replaces all the other attributes with the ones gotten from the loaded json.
        """
        if not self._encoded or not isinstance(self._encoded, bytes):
            raise AttributeError(f"expected encoded bytes but got {self._encoded} ({type(self._encoded)}) instead")

        decoded = self._encoded.decode()
        loaded_json = json.loads(decoded)

        self.authentication = loaded_json.get("authentication")
        self.endpoint = loaded_json.get("endpoint")
        self.method = loaded_json.get("method")
        self.payload = loaded_json.get("payload")

        return loaded_json

    @staticmethod
    def from_bytes(client_message: bytes) -> "ClientMessage":
        """this is the same process as ClientMessage(...).decode() but it creates a different instance"""
        decoded_message = client_message.decode()
        message_dict = json.loads(decoded_message)

        authentication = message_dict.get("authentication")
        endpoint = message_dict.get("endpoint")
        method = message_dict.get("method")
        payload = message_dict.get("payload")

        return ClientMessage(
            authentication=authentication,
            endpoint=endpoint,
            method=method,
            payload=payload
        )

    def __bytes__(self) -> bytes:
        """alternative method for ClientMessage(...).encode()"""
        return self.encode()

    def __str__(self) -> str:
        """
        returns a dumped json of all the values (with regard for ascii)
        """
        return json.dumps(self._dictionary(), ensure_ascii=False)

    def __getitem__(self, item: str) -> str | dict:
        """
        returns the gotten item from the dictionary.
        raises KeyError if item is not found
        """

        return self._dictionary()[item]


# todo: change complicated encoded/normal syntax into Class.from_bytes(...) like i did with ClientMessage
@dataclass
class ServerMessage:
    """
    status: {"code": int, "message": str}
    method: post | get | respond | initiate
    endpoint: endpoint route
    payload: json
    """
    status: dict[str, int | str] = None
    method: str = None
    endpoint: str = None
    payload: dict[str, Any] = None

    _encoded: bytes = None


    def _dictionary(self):
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
        self._encoded = self.__str__().encode()
        return self._encoded

    def decode(self) -> dict[str, Any]:
        """
        returns the loaded json gotten from self.encoded.
        in addition, it replaces all the other attributes with the ones gotten from the loaded json.
        """
        if not self._encoded or not isinstance(self._encoded, bytes):
            raise AttributeError(f"expected encoded bytes but got {self._encoded} ({type(self._encoded)}) instead")

        decoded = self._encoded.decode()
        loaded_json = json.loads(decoded)

        self.status = loaded_json.get("status")
        self.endpoint = loaded_json.get("endpoint")
        self.method = loaded_json.get("method")
        self.payload = loaded_json.get("payload")

        return loaded_json

    @staticmethod
    def from_bytes(server_message: bytes) -> "ServerMessage":
        """this is the same process as ServerNessage(...).decode() but it creates a different instance"""
        decoded_message = server_message.decode()
        message_dict = json.loads(decoded_message)

        status = message_dict.get("status")
        endpoint = message_dict.get("endpoint")
        method = message_dict.get("method")
        payload = message_dict.get("payload")

        return ServerMessage(
            status=status,
            endpoint=endpoint,
            method=method,
            payload=payload
        )

    def __bytes__(self) -> bytes:
        """alternative method for ServerMessage(...).encode()"""
        return self.encode()

    def __str__(self) -> str:
        """
        returns a dumped json of all the values (with regard for ascii)
        """
        return json.dumps(self._dictionary(), ensure_ascii=False)

    def __getitem__(self, item: str) -> str | dict:
        """
        returns the gotten item from the dictionary.
        raises KeyError if item is not found
        """

        return self._dictionary()[item]
