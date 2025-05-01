import json
from dataclasses import dataclass
from typing import Any

from base64 import b64encode, b64decode

methods = [
    "post",
    "get",
    "respond",
    "initiate",
]


class MalformedMessage(Exception):
    """en error that is raised when an invalid message format is sent [raised in Class.from_bytes(...)]"""
    def __init__(self, message: str):
        super().__init__(message)

        # the status message of the error
        self.message = message

        # the status code of this error
        self.code = 400


def serialize_data(data: Any):
    """
    recursively encodes the data of a payload in order for it to be usable with JSON.
    only bytes are actually encoded, any other type is left as it is.
    """

    if isinstance(data, bytes):
        # Serialize bytes into a dictionary with the Base64 encoding and the type info
        return {"__bytes__": b64encode(data).decode('utf-8'), "__type__": "bytes"}
    # If it's a dictionary or list or tuple, recurse through its items to see if they also need encoding.
    elif isinstance(data, dict):
        return {key: serialize_data(value) for key, value in data.items()}
    # the syntax for iterating through a list and through a tuple are the same, so we can combine them
    elif isinstance(data, list | tuple):
        return [serialize_data(item) for item in data]
    else:
        # For other types (int, bool, str, etc.), leave them as they are
        return data


# recursively decode the data of a payload
def deserialize_data(data: Any):
    """
    recursively decodes the data of a payload. this should be used when creating an object .from_bytes(...).
    """

    if isinstance(data, dict):
        # Check if it's the special bytes indicator (which is added when serializing the initial data)
        if "__bytes__" in data and "__type__" in data and data["__type__"] == "bytes":
            # Decode from Base64 and return as bytes
            return b64decode(data["__bytes__"])
        # Recurse through the dictionary
        return {key: deserialize_data(value) for key, value in data.items()}
    elif isinstance(data, list | tuple):
        # Recurse through the list/tuple
        return [deserialize_data(item) for item in data]
    else:
        # For other types, just return the value as is
        return data


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

        try:
            message_dict = json.loads(decoded_message)
        except json.JSONDecodeError:
            raise MalformedMessage("malformed information")

        authentication = message_dict.get("authentication")
        endpoint = message_dict.get("endpoint")
        method = message_dict.get("method")

        # if its in byte form, it means the payload is b64 encoded (see serialize_data())
        # since payloads are allowed to be empty, if the payload doesn't exist we replace it with an empty dict
        payload = message_dict.get("payload", {})

        # payload IS allowed to be empty.

        # decode the b64 values of the bytes.
        deserialized_payload = deserialize_data(payload)

        if not all((endpoint, method, payload)):
            raise MalformedMessage("missing information")

        return ClientMessage(
            authentication=authentication,
            endpoint=endpoint,
            method=method,
            payload=deserialized_payload
        )

    def __bytes__(self) -> bytes:
        """alternative method for ClientMessage(...).encode()"""
        return self.encode()

    def __str__(self) -> str:
        """
        returns a dumped json of all the values (with regard for ascii)
        """
        message_dictionary = self._dictionary()
        message_payload = message_dictionary.get("payload", {})

        # we b64 encode all the bytes in the payload, so that we can json.dumps() the payload dict.
        json_serialized_payload = serialize_data(message_payload)

        message_dictionary["payload"] = json_serialized_payload

        return json.dumps(message_dictionary, ensure_ascii=False)

    def __getitem__(self, item: str) -> str | dict:
        """
        returns the gotten item from the dictionary.
        raises KeyError if item is not found
        """

        return self._dictionary()[item]


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

        try:
            message_dict = json.loads(decoded_message)
        except json.JSONDecodeError:
            raise MalformedMessage("malformed information")

        status = message_dict.get("status")
        endpoint = message_dict.get("endpoint")
        method = message_dict.get("method")

        # if its in byte form, it means the payload is b64 encoded (see serialize_data())
        # since payloads are allowed to be empty, if the payload doesn't exist we replace it with an empty dict
        payload = message_dict.get("payload", {})

        # payload IS allowed to be empty.
        if not all((status, endpoint, method)):
            raise MalformedMessage("missing information")

        # decode the b64 values of the bytes.
        deserialized_payload = deserialize_data(payload)

        return ServerMessage(
            status=status,
            endpoint=endpoint,
            method=method,
            payload=deserialized_payload
        )

    def __bytes__(self) -> bytes:
        """alternative method for ServerMessage(...).encode()"""
        return self.encode()

    def __str__(self) -> str:
        """
        returns a dumped json of all the values (with regard for ascii).

        values are b64url_safe encoded inside of payload
        """
        message_dictionary = self._dictionary()
        message_payload = message_dictionary.get("payload", {})

        # we b64 encode all the bytes in the payload, so that we can json.dumps() the payload dict.
        json_serialized_payload = serialize_data(message_payload)

        message_dictionary["payload"] = json_serialized_payload
        return json.dumps(message_dictionary, ensure_ascii=False)

    def __getitem__(self, item: str) -> str | dict:
        """
        returns the gotten item from the dictionary.
        raises KeyError if item is not found
        """

        return self._dictionary()[item]
