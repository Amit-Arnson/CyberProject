import os

from dotenv import load_dotenv
from Caches.user_cache import UserCache
from Caches.client_cache import Address, ClientPackage

from dataclasses import dataclass

import asyncio
from asyncio import transports

load_dotenv("secrets.env")
PEPPER = os.getenv("PEPPER")

# The IP and PORT of the server.
IP = "127.0.0.1"
PORT = 5555

# cache's a user's auth information such as user ID, aes key and session token.
cached_authorization = UserCache()


class EndPoints:
    # these are the paths the sever gets from a client.
    # each path will have a method (get/post) and if it requires a valid session token
    @dataclass
    class EndPointRequires:
        # which method it requires
        method: str

        # if it requires authentication beforehand
        authentication: bool

        def __post_init__(self):
            self.method = self.method.lower()

    def __init__(self):
        # these are the endpoints where the client sends to the server
        self.endpoints = {
            "authentication/dhe": self.EndPointRequires(method="get", authentication=False),
            "authentication/aes": self.EndPointRequires(method="get", authentication=False)
        }


# note that read/write using asyncio's protocol adds its own buffer, so we don't need to manually add one.
class ServerProtocol(asyncio.Protocol):
    def __init__(self):
        self.client_package: ClientPackage | None = None

    def connection_made(self, transport: transports.Transport) -> None:
        # gets the ip-port pair as a tuple
        client_address = transport.get_extra_info("peername")
        address = Address(ip_port_tuple=client_address)
        client_information = ClientPackage(
            address=address,
            client=transport,
        )

        if not self.client_package:
            self.client_package = client_information

    def data_received(self, data: bytes) -> None:
        print(data.decode())


async def main() -> None:
    """Hosts a server to communicate with a client through sending and receiving string data."""

    event_loop = asyncio.get_event_loop()

    server = await event_loop.create_server(
        ServerProtocol,
        host=IP,
        port=PORT,
    )

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())