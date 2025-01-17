import asyncio
from asyncio import transports

from Caches.user_cache import ClientSideUserCache
from pseudo_http_protocol import ClientMessage, ServerMessage, MalformedMessage

from Endpoints.client_endpoints import EndPoints

from encryptions import EncryptedTransport

# The IP and PORT of the server.
IP = "127.0.0.1"
PORT = 5555

# this is a cache that the client keeps in order to track their own keys and session tokens
client_user_cache = ClientSideUserCache()
client_endpoints = EndPoints()


# note that read/write using asyncio's protocol adds its own buffer, so we don't need to manually add one.
class ClientProtocol(asyncio.Protocol):
    def __init__(self, on_con_lost: asyncio.Future):
        self.transport: EncryptedTransport | None = None
        self.on_con_lost = on_con_lost

        self.endpoints = client_endpoints
        self.event_loop = asyncio.get_event_loop()

        # a list of status codes that the server sends which count as "ok" (no errors raised)
        self.acceptable_status_codes: tuple[int, ...] = (
            000, 200
        )

    def connection_made(self, transport: transports.Transport) -> None:
        self.transport = EncryptedTransport(transport=transport)
        pass

    def connection_lost(self, exc: Exception | None) -> None:
        print("lost connection")
        self.on_con_lost.set_result(True)

    def data_received(self, data: bytes) -> None:
        # decrypts the data
        print(data)
        data = self.transport.read(data)
        print(data)

        try:
            server_message = ServerMessage.from_bytes(data)
        except MalformedMessage:
            # todo: add error handling for malformed message form a server (unlikely to happen though, maybe only fabricated messages)
            # todo: think of a way for the client to communicate the error to the server (check server-side todo list for explanation)
            return

        print(server_message)

        status_code = server_message.status.get("code")
        requested_endpoint = server_message.endpoint

        if self.transport.key and self.transport.iv:
            self.transport.write(
                ClientMessage(
                    authentication=None,
                    method="post",
                    endpoint="user/signup",
                    payload={
                        "username": "amit1234",
                        "display_name": "amit",
                        "password": "1234!"
                    }
                ).encode()
            )
            print("sent to server :)")

        # currently we don't really care about the method. ill decide whether we even need a method from the server to
        # the client later on.

        # given_method = server_message.method

        if requested_endpoint in self.endpoints and status_code in self.acceptable_status_codes:
            client_action_function = self.endpoints[requested_endpoint]

            # client action functions are any function that is related to an endpoint (meaning the server specifically
            # asks for it). Other functions that may not be related to a specific endpoint will not be in this
            # pile of functions.
            self.event_loop.create_task(client_action_function(self.transport, server_message, client_user_cache))
        else:
            pass
            # todo: implement "endpoint not found" logic


async def main():
    event_loop = asyncio.get_event_loop()

    # we use asyncio.Future to check for a connection loss so that the client will keep on running
    # after the initial creation of the connection.
    on_con_lost = event_loop.create_future()

    transport, protocol = await event_loop.create_connection(
        lambda: ClientProtocol(on_con_lost=on_con_lost),
        host=IP,
        port=PORT
    )

    try:
        await on_con_lost
    finally:
        transport.close()

if __name__ == "__main__":
    asyncio.run(main())
