import logging
from typing import Callable
from client_actions import (
    complete_authentication,
    user_login,
    song_upload_finish,
    DownloadSong,
    buffer_audio,
    load_sheet_images,
    load_genre_browser,
    load_song_comments,
    upload_song_search_info,
    upload_user_statistics
)


class EndPoints:
    def __init__(self):
        download_song_state = DownloadSong()

        self.endpoints: dict[str, Callable] = {
            "authentication/key_exchange": complete_authentication,
            "user/login": user_login,
            "song/upload/finish": song_upload_finish,
            "song/download/preview": download_song_state.download_preview_details,
            "song/download/preview/file": download_song_state.download_preview_chunks,
            "song/download/audio": buffer_audio,
            "song/download/sheet": load_sheet_images,
            "song/genres": load_genre_browser,
            "song/comments": load_song_comments,
            "song/search": upload_song_search_info,
            "user/statistics": upload_user_statistics
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
