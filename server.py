import os

from dotenv import load_dotenv

from Caches.user_cache import UserCache, UserCacheItem
from Caches.client_cache import Address, ClientPackage

from pseudo_http_protocol import ClientMessage, ServerMessage
from Endpoints.server_endpoints import EndPoints, EndPoint

import asyncio
from asyncio import transports

from AES_128 import cbc
from DHE.dhe import DHE, generate_initial_dhe

load_dotenv("secrets.env")
PEPPER = os.getenv("PEPPER")


# The IP and PORT of the server.
IP = "127.0.0.1"
PORT = 5555

# cache's a user's auth information such as user ID, aes key and session token.
# todo: due to separating the action functions from server.py (which is practically main.py), i will have to refactor how i cache users.
cached_authorization = UserCache()
server_endpoints = EndPoints()


# note that read/write using asyncio's protocol adds its own buffer, so we don't need to manually add one.
class ServerProtocol(asyncio.Protocol):
    def __init__(self):
        self.client_package: ClientPackage | None = None

        # These just reference the shared instances, not creating new instances per protocol object
        self.endpoints = server_endpoints
        self.user_cache = cached_authorization

        self.event_loop = asyncio.get_event_loop()

    def connection_made(self, transport: transports.Transport) -> None:
        # gets the ip-port pair as a tuple
        client_address = transport.get_extra_info("peername")

        # here starts the process of getting a symmetric encryption key (using dhe)
        server_dhe: DHE = generate_initial_dhe()

        base = server_dhe.g
        prime_modulus = server_dhe.p
        secret_exponent = server_dhe.e

        aes_iv = cbc.generate_iv()

        shared_public = server_dhe.calculate_public()

        # here we build a server message that includes all the information needed for the
        # key exchange, as well as the IV for after the key exchange is completed (IV is sent with the DHE stuff
        # in order to not send multiple messages).
        dhe_key_exchange_message = ServerMessage(
            status={
                "code": 000,
                "message": "encryption key exchange"
            },
            method="initiate",
            endpoint="authentication/key_exchange",
            payload={
                "base": base,
                "mod": prime_modulus,
                "public": shared_public,
                "iv": aes_iv,
            }
        )

        transport.write(dhe_key_exchange_message.encode())

        address = Address(ip_port_tuple=client_address)
        client_information = ClientPackage(
            address=address,
            client=transport,
        )

        user_cache_item = UserCacheItem(
            address=address,
            dhe_base=base,
            dhe_mod=prime_modulus,
            dhe_exponent=secret_exponent,
            iv=aes_iv
        )

        # asynchronously add the UserCacheItem to the global cache
        self.event_loop.create_task(self.user_cache.add(user_cache_item))

        if not self.client_package:
            self.client_package = client_information

    def data_received(self, data: bytes) -> None:
        client_message = ClientMessage.from_bytes(data)

        # todo: validate body of request here
        requested_endpoint = client_message.endpoint
        given_method = client_message.method
        client_session_token = client_message.authentication

        if EndPoint(endpoint=requested_endpoint, method=given_method, authentication=client_session_token) in self.endpoints:
            server_action_function = self.endpoints[requested_endpoint]

            # server function actions are specifically tied to endpoints that a client asks for. Functions that are not
            # directly related to an endpoint will not be inside the action list.
            self.event_loop.create_task(server_action_function(self.client_package, client_message, self.user_cache))
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
