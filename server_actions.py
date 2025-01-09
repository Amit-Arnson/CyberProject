from pseudo_http_protocol import ClientMessage
from Caches.client_cache import ClientPackage
from Caches.user_cache import UserCache, UserCacheItem

from AES_128 import cbc


async def authenticate_client(client_package: ClientPackage, client_message: ClientMessage, user_cache: UserCache):
    client = client_package.client

    client_session_token = client_message.authentication
    client_user_cache: UserCacheItem = user_cache[client_session_token]

