from pseudo_http_protocol import ClientMessage
from Caches.client_cache import ClientPackage


async def authenticate_client(client_package: ClientPackage, client_message: ClientMessage):
    client = client_package.client
    print(client_package.address.ip + " :)")
