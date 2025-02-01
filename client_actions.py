from asyncio.transports import Transport

from pseudo_http_protocol import ServerMessage, ClientMessage
from Caches.user_cache import ClientSideUserCache

from encryptions import EncryptedTransport
from DHE.dhe import DHE, generate_dhe_response

from flet import Page

from gui_testing import MainPage


async def complete_authentication(_: Page, transport: EncryptedTransport, server_message: ServerMessage, __: ClientSideUserCache):
    """
    this function is used to finish transferring the key using dhe.
    it sends the client's public key back to the server.

    this function also saves the IV and full key to the transport

    tied to authentication/key_exchange

    expected payload:
    {
        "base": int,
        "mod": int,
        "public": int,
        "iv": bytes
    }

    expected output:
    {
        "public": str
    }
    """

    payload = server_message.payload

    try:
        dhe_base = payload["base"]
        dhe_mod = payload["mod"]
        server_public_value = payload["public"]

        aes_iv = payload["iv"]
    except KeyError:
        raise # todo: figure out what to do with malformed server messages (likely being faked messages)

    client_dhe: DHE = generate_dhe_response(mod=dhe_mod, base=dhe_base)

    client_public_value = client_dhe.calculate_public()

    transport.write(
        ClientMessage(
            authentication=None,
            method="respond",
            endpoint="authentication/key_exchange",
            payload={
                "public": client_public_value
            }
        ).encode()
    )

    mutual_key_value = client_dhe.calculate_mutual(peer_public_value=server_public_value)

    aes_key = client_dhe.kdf_derive(mutual_key=mutual_key_value, iterations=10000, size=16)

    transport.iv = aes_iv
    transport.key = aes_key


async def user_login(page: Page, transport: EncryptedTransport, server_message: ServerMessage, user_cache: ClientSideUserCache):
    """
    this function expects the login result from requesting a login from the server.
    it then saves the session token and the user ID to the ClientSideUserCache.

    tied to user/login

    expected payload:
    {
        "session_token": str,
        "user_id": str
    }

    expected output:
    None
    """

    payload = server_message.payload

    try:
        session_token = payload["session_token"]
        user_id = payload["user_id"]
    except KeyError:
        raise # todo: figure out what to do with malformed server messages (likely being faked messages)

    user_cache.session_token = session_token
    user_cache.user_id = user_id

    # this is a temporary MainPage for testing purposes only
    MainPage(page).start()

    # todo: figure out how to log in the user client side, as in, GUI.