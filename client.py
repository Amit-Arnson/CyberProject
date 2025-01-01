import asyncio
from asyncio import transports


# The IP and PORT of the server.
IP = "127.0.0.1"
PORT = 5555


# note that read/write using asyncio's protocol adds its own buffer, so we don't need to manually add one.
class ClientProtocol(asyncio.Protocol):
    def __init__(self):
        self.transport: transports.Transport | None = None

    def connection_made(self, transport: transports.Transport) -> None:
        self.transport = transport
        pass

    def connection_lost(self, exc: Exception | None) -> None:
        self.transport.close()

    def data_received(self, data: bytes) -> None:
        pass


async def main():
    event_loop = asyncio.get_event_loop()

    transport, protocol = await event_loop.create_connection(
        ClientProtocol,
        host=IP,
        port=PORT
    )

if __name__ == "__main__":
    asyncio.run(main())
