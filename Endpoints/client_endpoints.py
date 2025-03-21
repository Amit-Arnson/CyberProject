import logging
from typing import Callable
from client_actions import (
    complete_authentication,
    user_login,
    DownloadSong
)

async def test(*args):
    print("NOT IMPLEMENTED")
    logging.error("NOT IMPLEMENTED (download/preview)")
    pass


class EndPoints:
    def __init__(self):
        download_song_state = DownloadSong()

        self.endpoints: dict[str, Callable] = {
            "authentication/key_exchange": complete_authentication,
            "user/login": user_login,
            "song/download/preview": test,
            "song/download/preview/file": download_song_state.download_preview_chunks
        }
        # endpoint -> function

    def __getitem__(self, item: str):
        """
        returns the function related to the endpoint

        :param item: endpoint name
        """
        return self.endpoints[item]

    def __contains__(self, item: str):
        """
        checks if an endpoint exists in the client

        :param item: endpoint name
        """
        return item in self.endpoints
