import os

from dotenv import load_dotenv

from Caches.user_cache import UserCache
from Caches.client_cache import Address, ClientPackage

from pseudo_http_protocol import ClientMessage, ServerMessage
from Endpoints.server_endpoints import EndPoints, EndPoint

import asyncio
from asyncio import transports

load_dotenv("secrets.env")
PEPPER = os.getenv("PEPPER")

# The IP and PORT of the server.
IP = "127.0.0.1"
PORT = 5555

# cache's a user's auth information such as user ID, aes key and session token.
cached_authorization = UserCache()


# note that read/write using asyncio's protocol adds its own buffer, so we don't need to manually add one.
class ServerProtocol(asyncio.Protocol):
    def __init__(self):
        self.client_package: ClientPackage | None = None
        self.endpoints = EndPoints()

        self.event_loop = asyncio.get_event_loop()

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
        print(data)
        client_message = ClientMessage.from_bytes(data)

        requested_endpoint = client_message.endpoint
        given_method = client_message.method
        client_session_token = client_message.authentication

        if EndPoint(endpoint=requested_endpoint, method=given_method, authentication=client_session_token) in self.endpoints:
            # all functions will accept both the package and the message
            server_function = self.endpoints[requested_endpoint]

            self.event_loop.create_task(server_function(self.client_package, client_message))
        else:
            pass
            # todo: add error function to return an error to the client


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
