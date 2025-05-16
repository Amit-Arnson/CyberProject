import socket
from dataclasses import dataclass
from encryptions import EncryptedTransport


@dataclass
class Address:
    """a representation of the ip, port tuple as a class"""
    ip: str = None
    port: int = None
    ip_port_tuple: tuple[str, int] = None

    def __post_init__(self):
        if not any((self.ip, self.port)) and not self.ip_port_tuple:
            raise AttributeError("missing information in Address (ip, port, or both)")

        if not self.ip_port_tuple or len(self.ip_port_tuple) != 2:
            raise AttributeError(f"expected tuple[ip, port] got {self.ip_port_tuple} instead")

        if self.ip_port_tuple:
            self.ip = self.ip_port_tuple[0]
            self.port = self.ip_port_tuple[1]

        if not isinstance(self.ip, str) or not isinstance(self.port, int):
            raise AttributeError(f"expects ip as str, port as int. got ip as {type(self.ip)}, port as {type(self.port)}")

    def __hash__(self) -> int:
        """returns the hash of tuple[ip, port]"""

        return hash((self.ip, self.port))


@dataclass
class ClientPackage:
    """an object with all the necessary information about a client socket"""
    address: Address
    client: socket.socket | EncryptedTransport
