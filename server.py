import logging
import os

import asqlite

from Caches.user_cache import UserCache, UserCacheItem
from Caches.client_cache import Address, ClientPackage

from pseudo_http_protocol import ClientMessage, ServerMessage, MalformedMessage
from Endpoints.server_endpoints import EndPoints, EndPoint

from Errors.raised_errors import (
    NotFound, Forbidden
)

import asyncio
from asyncio import transports, Task

from AES_128 import cbc
from encryptions import EncryptedTransport
from DHE.dhe import DHE, generate_initial_dhe

from FileSystem.base_file_system import System, BaseFile

from initiate_database import CreateTables
from Utils.sqlite3_ext import create_connection_pool

from RSASigning.private_key import sign_sync

# The IP and PORT of the server.
IP = "127.0.0.1"
PORT = 5555

# cache's a user's auth information such as user ID, aes key and session token.
cached_authorization = UserCache()
server_endpoints = EndPoints()

SIGNATURE = sign_sync(IP.encode())


# note that read/write using asyncio's protocol adds its own buffer, so we don't need to manually add one.
class ServerProtocol(asyncio.Protocol):
    def __init__(self, database_pool: asqlite.Pool):
        self.db_pool = database_pool

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
                "signature": SIGNATURE
            }
        )

        transport = EncryptedTransport(transport, iv=aes_iv)

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

        # todo: maybe add a signing feature to all server messages so that they cant be faked? (using asymmetric key)

        # asynchronously add the UserCacheItem to the global cache
        self.event_loop.create_task(self.user_cache.add(user_cache_item))

        if not self.client_package:
            self.client_package = client_information

    def data_received(self, data: bytes) -> None:
        # decrypts the data
        data = self.client_package.client.read(data)

        try:
            client_message = ClientMessage.from_bytes(data)
        except MalformedMessage:
            # todo: add a response for the error
            # todo: think of a way to communicate which error is related to which client message (as in, "respond" to the message)
            return

        # todo: validate that the message is actually built like ClientMessage (correct format)
        requested_endpoint = client_message.endpoint
        given_method = client_message.method
        client_session_token = client_message.authentication

        if not self.user_cache.is_valid_session(client_session_token):
            self._send_error(
                Forbidden("Invalid session token passed"),
                endpoint=requested_endpoint
            )

        if EndPoint(endpoint=requested_endpoint, method=given_method, authentication=client_session_token) in self.endpoints:
            server_action_function = self.endpoints[requested_endpoint]

            # server function actions are specifically tied to endpoints that a client asks for. Functions that are not
            # directly related to an endpoint will not be inside the action list.

            action = self.event_loop.create_task(
                server_action_function(
                    self.db_pool,
                    self.client_package,
                    client_message,
                    self.user_cache
                )
            )
            action.add_done_callback(self.on_complete)
            action.end_point = requested_endpoint
        else:
            self._send_error(
                NotFound(f"Requested endpoint ({given_method.upper()} {requested_endpoint}) not found"),
                endpoint=requested_endpoint
            )

    def _send_error(self, error: BaseException, endpoint: str):
        # if the error is not a custom error, then it is assumed that it is an internal server error.
        error_code = 500
        if hasattr(error, "code"):
            error_code = error.code

        error_message = "an internal server error occurred"
        if hasattr(error, "message"):
            error_message = error.message

        extra: dict = {}
        if hasattr(error, "extra"):
            extra = error.extra

        transport = self.client_package.client

        transport.write(
            ServerMessage(
                status={
                    "code": error_code,
                    "message": error_message,
                },
                method="respond",
                endpoint=f"{endpoint}/error",
                payload=extra
            ).encode(),
        )

    def on_complete(self, action: Task):
        """
            this is the callback function for the created tasks. once a task is finished (either normally or by error),
            this function will be called.

            Any error handling related to errors thrown inside of server actions should be done here.
        """
        if action.exception():
            # raise action.exception()
            error = action.exception()

            self._send_error(error, endpoint=action.end_point)
        else:
            print(f"Task completed successfully with result: {action.result()}")


async def main() -> None:
    """Hosts a server to communicate with a client through sending and receiving string data."""

    database_name = "database.db"

    # create all the tables in the database (this is not an async action, so it should only be used once)
    CreateTables(database_name).init()

    # creating an async database pool for all server-side database interactions. A db pool helps avoid race
    # conditions in async code.
    database_pool = await create_connection_pool(database_name)

    file_system = System(db_pool=database_pool)

    # create the directory (check doc-string for more info)
    file_system.initialize()
    event_loop = asyncio.get_event_loop()

    # event_loop.create_server() expects a Callable to create a new instance of the protocol class. I want to pass a database
    # pool into the protocol class, which obviously can only be created once. Due to this, I have to build a function that
    # creates an instance of the ServerProtocol that has the database pool inside of it.
    def protocol_factory():
        return ServerProtocol(database_pool)

    server = await event_loop.create_server(
        protocol_factory,
        host=IP,
        port=PORT,
    )

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
