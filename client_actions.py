from asyncio.transports import Transport

from pseudo_http_protocol import ServerMessage, ClientMessage
from Caches.user_cache import ClientSideUserCache

from AES_128 import cbc
from DHE.dhe import DHE, generate_dhe_response


async def complete_authentication(transport: Transport, server_message: ServerMessage, user_cache: ClientSideUserCache):
    """
    this function is used to finish transferring the key using dhe.

    expected payload:
    {
        "base": int,
        "mod": int,
        "public": int,
        "iv": bytes
    }
    """

    payload = server_message.payload

    dhe_base = payload.get("base")
    dhe_mod = payload.get("mod")
    server_public_value = payload.get("public")

    aes_iv = payload.get("iv")

    client_dhe: DHE = generate_dhe_response(mod=dhe_mod, base=dhe_base)

    client_public_value = client_dhe.calculate_public()

    client_message = ClientMessage(
        authentication=None,
        method="respond",
        endpoint="authentication/key_exchange",
        payload={
            "public": client_public_value
        }
    )

    transport.write(client_message.encode())

    mutual_key_value = client_dhe.calculate_mutual(peer_public_value=server_public_value)

    aes_key = client_dhe.kdf_derive(mutual_key=mutual_key_value, iterations=10000, size=16)

    user_cache.iv = aes_iv
    user_cache.aes_key = aes_key
