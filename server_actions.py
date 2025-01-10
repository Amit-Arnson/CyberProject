from pseudo_http_protocol import ClientMessage
from Caches.client_cache import ClientPackage
from Caches.user_cache import UserCache, UserCacheItem

from AES_128 import cbc
from DHE.dhe import DHE


class InvalidPayload(Exception):
    """Error that is thrown when the client passes an invalid payload"""


async def authenticate_client(client_package: ClientPackage, client_message: ClientMessage, user_cache: UserCache):
    """
    this function is used to finish transferring the key using dhe.

    expected payload:
    {
        "public": int
    }
    """

    # client = client_package.client
    address = client_package.address

    client_user_cache: UserCacheItem = user_cache[address]

    payload = client_message.payload

    try:
        client_public_value = payload["public"]
    except KeyError:
        payload_keys = " ".join(f"\"{key}\"" for key in payload.keys())
        raise InvalidPayload(f"Invalid payload passed. expected key \"public\", instead got {payload_keys}")

    server_dhe = DHE(
        e=client_user_cache.dhe_exponent,
        g=client_user_cache.dhe_base,
        p=client_user_cache.dhe_mod
    )

    mutual_key_number: int = server_dhe.calculate_mutual(client_public_value)

    aes_key = server_dhe.kdf_derive(mutual_key=mutual_key_number, iterations=10000, size=16)

    client_user_cache.aes_key = aes_key

    print(aes_key)

