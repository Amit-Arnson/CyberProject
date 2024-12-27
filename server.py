import threading
import socket
import os

from dotenv import load_dotenv
from Caches.user_cache import UserCache
from Caches.client_cache import Address, ClientPackage

import asyncio

load_dotenv("secrets.env")
PEPPER = os.getenv("PEPPER")

# The IP and PORT of the server.
IP = "127.0.0.1"
PORT = 5555

# cache's a user's auth information such as user ID, aes key and session token.
cached_authorization = UserCache()


async def connection(client_pack: ClientPackage):
    event_loop = asyncio.get_event_loop()


async def main() -> None:
    """Hosts a server to communicate with a client through sending and receiving string data."""

    # Creates the connection object.
    server = socket.socket()
    # Binds the connection to an address.
    server.bind((IP, PORT))

    server.setblocking(False)

    event_loop = asyncio.get_event_loop()

    # TODO: make async instead of thread
    while True:
        try:
            # Listens to clients trying to connect.
            server.listen()

            # Accepts a connection with one client and creates its connection object.
            client, client_address = await event_loop.sock_accept(server)

            client_address = Address(client_address)

            client_information = ClientPackage(
                address=client_address,
                client=client,
            )

            event_loop.create_task(connection(client_information))
        except Exception as e:
            print(f"in main: {e}")