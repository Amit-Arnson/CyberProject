import traceback

import asyncio
from asyncio import transports, Task

from Caches.user_cache import ClientSideUserCache
from pseudo_http_protocol import ClientMessage, ServerMessage, MalformedMessage

from Endpoints.client_endpoints import EndPoints
from Endpoints.client_error_endpoints import ErrorEndPoints

from encryptions import EncryptedTransport

import flet as ft

from GUI.login import LoginPage
from GUI.page_error import PageError

# The IP and PORT of the server.
IP = "127.0.0.1"
PORT = 5555

# this is a cache that the client keeps in order to track their own keys and session tokens
client_user_cache = ClientSideUserCache()
client_endpoints = EndPoints()
client_error_endpoints = ErrorEndPoints()


# note that read/write using asyncio's protocol adds its own buffer, so we don't need to manually add one.
class ClientProtocol(asyncio.Protocol):
    def __init__(self, on_con_lost: asyncio.Future, page: ft.Page):
        self.transport: EncryptedTransport | None = None
        self.on_con_lost = on_con_lost

        self.endpoints = client_endpoints
        self.error_endpoints = client_error_endpoints
        self.event_loop = asyncio.get_event_loop()

        # a list of status codes that the server sends which count as "ok" (no errors raised)
        self.acceptable_status_codes: tuple[int, ...] = (
            000,
            200
        )

        self.page = page
        self.page.transport = self.transport

    def connection_made(self, transport: transports.Transport) -> None:
        self.transport = EncryptedTransport(transport=transport)

        self.page.transport = self.transport
        self.page.user_cache = ClientSideUserCache

        LoginPage(page=self.page).show()

    def connection_lost(self, exc: Exception | None) -> None:
        print("lost connection")
        self.on_con_lost.set_result(True)

    def data_received(self, data: bytes) -> None:
        # decrypts the data
        data = self.transport.read(data)

        try:
            server_message = ServerMessage.from_bytes(data)
        except MalformedMessage:
            # todo: add error handling for malformed message form a server (unlikely to happen though, maybe only fabricated messages)
            # todo: think of a way for the client to communicate the error to the server (check server-side todo list for explanation)
            return

        # print(server_message)

        status_code = server_message.status.get("code")
        requested_endpoint = server_message.endpoint

        # currently we don't really care about the method. ill decide whether we even need a method from the server to
        # the client later on.

        # given_method = server_message.method

        if requested_endpoint in self.endpoints and status_code in self.acceptable_status_codes:
            client_action_function = self.endpoints[requested_endpoint]

            # client action functions are any function that is related to an endpoint (meaning the server specifically
            # asks for it). Other functions that may not be related to a specific endpoint will not be in this
            # pile of functions.
            action = self.event_loop.create_task(client_action_function(self.page, self.transport, server_message, client_user_cache))
            action.add_done_callback(self.on_complete)
        elif requested_endpoint in self.error_endpoints:
            client_error_action_function = self.error_endpoints[requested_endpoint]

            # these are all the functions to graphically display errors (as in, GUI)
            error_action = self.event_loop.create_task(client_error_action_function(self.page, self.transport, server_message, client_user_cache))
            error_action.add_done_callback(self.on_complete)
        else:
            # this is activated when an endpoint is not found
            # for other error handling, go to on_complete
            # todo: add on_complete error handling.

            if status_code in self.acceptable_status_codes:
                return

            status_message = server_message.status.get("message")
            self.page.server_error(
                ft.Text(
                    f"{status_message}\n\nstatus: {status_code}"
                )
            )

    def on_complete(self, action: Task):
        """
            this is the callback function for the created tasks. once a task is finished (either normally or by error),
            this function will be called.

            Any error handling related to errors thrown inside of server actions should be done here.
        """
        if action.exception():
            traceback.print_exc()
            raise action.exception()
            print(f"Task failed with exception: {action.exception()}")
        else:
            print(f"Task completed successfully with result: {action.result()}")


async def main(page: ft.Page):
    page.server_error = PageError(page).error

    page.window.min_width = 1000
    page.window.min_height = 600

    event_loop = asyncio.get_event_loop()

    # we use asyncio.Future to check for a connection loss so that the client will keep on running
    # after the initial creation of the connection.
    on_con_lost = event_loop.create_future()

    transport, protocol = await event_loop.create_connection(
        lambda: ClientProtocol(on_con_lost=on_con_lost, page=page),
        host=IP,
        port=PORT
    )

    try:
        await on_con_lost
    finally:
        transport.close()

# todo: figure out if i need the following flet extensions: flet-audio-recorder
if __name__ == "__main__":
    # flet natively supports async environment, for this reason we do not need to use asyncio.run() and only use flet.app().
    ft.app(main, assets_dir="GUI/Assets")
