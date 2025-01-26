import os

import asqlite

from Caches.user_cache import UserCache, UserCacheItem
from Caches.client_cache import Address, ClientPackage

from pseudo_http_protocol import ClientMessage, ServerMessage, MalformedMessage
from Endpoints.server_endpoints import EndPoints, EndPoint

import asyncio
from asyncio import transports, Task

from AES_128 import cbc
from encryptions import EncryptedTransport
from DHE.dhe import DHE, generate_initial_dhe

from FileSystem.base_file_system import System, BaseFile

# The IP and PORT of the server.
IP = "127.0.0.1"
PORT = 5555

# cache's a user's auth information such as user ID, aes key and session token.
cached_authorization = UserCache()
server_endpoints = EndPoints()


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

        if EndPoint(endpoint=requested_endpoint, method=given_method, authentication=client_session_token) in self.endpoints:
            server_action_function = self.endpoints[requested_endpoint]

            # server function actions are specifically tied to endpoints that a client asks for. Functions that are not
            # directly related to an endpoint will not be inside the action list.

            action = self.event_loop.create_task(server_action_function(self.db_pool, self.client_package, client_message, self.user_cache))
            action.add_done_callback(self.on_complete)
        else:
            pass
            # todo: add error function to return an error to the client

    # todo: find a way to tell the client the error in a way that can be graphically visualized
    def on_complete(self, action: Task):
        """
            this is the callback function for the created tasks. once a task is finished (either normally or by error),
            this function will be called.

            Any error handling related to errors thrown inside of server actions should be done here.
        """
        if action.exception():
            print(f"Task failed with exception: {action.exception()}")
        else:
            print(f"Task completed successfully with result: {action.result()}")


async def main() -> None:
    """Hosts a server to communicate with a client through sending and receiving string data."""

    # creating an async database pool for all server-side database interactions. A db pool helps avoid race
    # conditions in async code.
    database_pool = await asqlite.create_pool("database.db")

    file_system = System(db_pool=database_pool)

    # create the directory (check doc-string for more info)
    file_system.initialize()

    # test code:
    # temp = BaseFile(file_path="C:\\Users\\amita\OneDrive\Pictures\DuckOpng.png")
    # await temp.load()
    #
    # await file_system.save(temp, uploaded_by_id="testest")

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
