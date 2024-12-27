from dataclasses import dataclass


@dataclass
class UserCacheItem:
    session_token: str
    user_id: str
    aes_key: bytes
    iv: bytes
    dhe_key: bytes | int


class UserCache:
    """
    Cache a UserCacheItem which contains:
    session token,
    user id,
    aes key,
    iv,
    dhe key,
    """
    def __init__(self):
        # a dictionary where the key is session_token, and it stores the cache item
        self._cache_dict: dict[str, UserCacheItem] = {}

    def add(self, cache_item: UserCacheItem):
        """Add a Cache Item to the UserCache dictionary"""
        user_session_token = cache_item.session_token
        self._cache_dict[user_session_token] = cache_item

    def __getitem__(self, item: str) -> UserCacheItem | None:
        """
        :param item: a user's session token
        :return: the cached item if found, else none
        """

        return self._cache_dict.get(item)

