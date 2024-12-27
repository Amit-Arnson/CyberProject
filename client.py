import asyncio
from asyncio import transports

# The IP and PORT of the server.
IP = "127.0.0.1"
PORT = 5555

class ClientProtocol(asyncio.Protocol):
    def connection_made(self, transport: transports.BaseTransport) -> None:
        pass

    def connection_lost(self, exc: Exception | None) -> None:
        pass

    def data_received(self, data: bytes) -> None:
        pass


async def main():
    event_loop = asyncio.get_event_loop()

    on_con_lost = event_loop.create_future()

    transport, protocol = await event_loop.create_connection(
        ClientProtocol,
        host=IP, port=PORT)

    # Wait until the protocol signals that the connection
    # is lost and close the transport.
    try:
        await on_con_lost
    finally:
        transport.close()


if __name__ == "__main__":
    asyncio.run(main())
