import asyncio
from dataclasses import dataclass
from Caches.client_cache import Address


@dataclass
class UserCacheItem:
    address: Address
    aes_key: bytes | None = None
    iv: bytes | None = None

    dhe_base: int | None = None
    dhe_mod: int | None = None
    dhe_exponent: int | None = None

    session_token: str | None = None
    user_id: str | None = None


class UserCache:
    """
    Cache a UserCacheItem which contains:
    address
    - the client's ip-port pair

    session token,
    - the client's session token that is generated AFTER a client logs in

    user id,
    - the client's user ID

    aes key,
    - the AES key that is generated using DHE when the initial connection is made

    iv,
    - the IV that will be used for the CBC encryption
    """
    def __init__(self):
        # a dictionary where the key is session_token, and it stores the cache item
        self._cache_dict: dict[str, UserCacheItem] = {}
        self._cache_via_address: dict[Address, UserCacheItem] = {}

        self._lock = asyncio.Lock()

    async def add(self, cache_item: UserCacheItem):
        """Add a Cache Item to the UserCache dictionary"""
        user_session_token: str = cache_item.session_token
        user_address: Address = cache_item.address

        # using asyncio.lock() to ensure no race conditions happen with a shared mutable resource
        async with self._lock:
            if user_session_token:
                self._cache_dict[user_session_token] = cache_item

            # address is a requirement for UserCacheItem meaning we don't need to check for it
            self._cache_via_address[user_address] = cache_item

    def __getitem__(self, item: str | Address) -> UserCacheItem | None:
        """
        :param item: a user's session token or address
        :return: the cached item if found, else none
        """

        if isinstance(item, str):
            return self._cache_dict.get(item)

        if isinstance(item, Address):
            return self._cache_via_address.get(item)


# this is an object for the client-side, just to neatly keep track of crucial stuff
@dataclass
class ClientSideUserCache:
    """
    session_token: the current session token for the user login
    user_id: the ID of the logged-in user
    """

    session_token: str | None = None
    user_id: str | None = None
