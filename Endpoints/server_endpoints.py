from typing import Callable
from server_actions import (
    authenticate_client,
    user_signup,
    user_login,
    user_signup_and_login,
    UploadSong,
    send_song_previews,
    resend_song_preview,
    send_song_audio,
    send_song_sheets,
    send_recommended_song_previews,
    send_recent_song_previews,
    send_genre_list,
    send_songs_by_genre,
    send_song_comments,
    upload_song_comment,
    search_for_songs_by_name,
    get_user_statistics,
    delete_song_request,
    delete_user_request,
    delete_comment_request,
    edit_user_display_name,
    logout_user
)

from dataclasses import dataclass


# todo: rewrite. dont over complicate this class.
class EndPointRequires:
    """a class to easily represent the method and authentication requirements of endpoints, as well as compare them"""

    def __init__(self, method: str, authentication: bool):
        # which method it requires
        self.method = method.lower()
        # if it requires authentication beforehand
        self.authentication = authentication

    def __post_init__(self):
        self.method = self.method.lower()

    def __eq__(self, other) -> bool:
        if not isinstance(other, type(self)):
            return False

        return self.method == other.method and self.authentication == other.authentication


class EndPoints:
    """
    The paths of endpoints inside the SERVER, which methods they require, whether they require authentication
    (session token) and the function that is linked to the endpoint.
    """

    def __init__(self):
        # in order to easily gather all the chunks in the same location, we use a class that is created when we initialize
        # the EndPoint class and it stores all of the information in the class so that it is easily accessed across
        # different function calls.
        # due to the way im initializing this, it means that any new instance of EndPoints will also make a new instance
        # of the cache, this means we cannot create multiple instances of EndPoints to be used in the same application
        upload_song_cache: UploadSong = UploadSong()

        # these are the endpoints where the client sends to the server
        self.endpoints: dict[str, tuple["EndPointRequires", Callable]] = {
            # authentication/key_exchange is used to share the encryption key between the server and client.
            "authentication/key_exchange": (
                EndPointRequires(method="respond", authentication=False),
                authenticate_client
            ),

            # user/signup is used to create a new user account.
            "user/signup": (
                EndPointRequires(method="post", authentication=False),
                user_signup
            ),

            # user/login is used to log into an existing user account
            "user/login": (
                EndPointRequires(method="post", authentication=False),
                user_login,
            ),

            # user/signup/login is used to create a user account and automatically log it in
            "user/signup/login": (
                EndPointRequires(method="post", authentication=False),
                user_signup_and_login,
            ),

            # song/upload is used to upload: the song file, description, tabs (images), artist, name and genre tags.
            "song/upload": (
                EndPointRequires(method="post", authentication=True),
                upload_song_cache.upload_song
            ),

            # song/upload/file is used to actually gather the chunks that are sent (related to song/upload)
            "song/upload/file": (
                EndPointRequires(method="post", authentication=True),
                upload_song_cache.upload_song_file
            ),

            # song/upload/finish is used to indicate that all the files have been transferred, and that the server can
            # start saving to DB
            "song/upload/finish": (
                EndPointRequires(method="post", authentication=True),
                upload_song_cache.upload_song_finish
            ),

            # song/download/preview is used get the cover art + song info for the "preview boxes" in the client GUI
            "song/download/preview": (
                EndPointRequires(method="get", authentication=True),
                send_song_previews
            ),

            "song/recommended/download/preview": (
                EndPointRequires(method="get", authentication=True),
                send_recommended_song_previews
            ),

            "song/recent/download/preview": (
                EndPointRequires(method="get", authentication=True),
                send_recent_song_previews
            ),

            "song/download/preview/resend": (
                EndPointRequires(method="get", authentication=True),
                resend_song_preview,
            ),

            "song/download/audio": (
                EndPointRequires(method="get", authentication=True),
                send_song_audio
            ),

            "song/download/sheets": (
                EndPointRequires(method="get", authentication=True),
                send_song_sheets
            ),

            "song/genres": (
                EndPointRequires(method="get", authentication=True),
                send_genre_list
            ),

            "song/genres/download/preview": (
                EndPointRequires(method="get", authentication=True),
                send_songs_by_genre
            ),

            "song/comments": (
                EndPointRequires(method="get", authentication=True),
                send_song_comments
            ),

            "song/comments/upload": (
                EndPointRequires(method="post", authentication=True),
                upload_song_comment
            ),

            "song/search": (
                EndPointRequires(method="get", authentication=True),
                search_for_songs_by_name
            ),

            "song/comment/delete": (
                EndPointRequires(method="delete", authentication=True),
                delete_comment_request
            ),

            "song/delete": (
                EndPointRequires(method="delete", authentication=True),
                delete_song_request
            ),

            "user/statistics": (
                EndPointRequires(method="get", authentication=True),
                get_user_statistics
            ),

            "user/edit/display": (
                EndPointRequires(method="post", authentication=True),
                edit_user_display_name
            ),

            "user/logout": (
                EndPointRequires(method="post", authentication=True),
                logout_user
            ),

            "user/delete": (
                EndPointRequires(method="delete", authentication=True),
                delete_user_request
            ),
        }
        # endpoint -> (requirements, function)

    def __getitem__(self, item: str) -> Callable:
        """returns the function related to the endpoint"""
        _, action = self.endpoints[item]

        return action

    def __contains__(self, item: "EndPoint") -> bool:
        """
        :param item: checks if tuple[endpoint, method, authentication] is a valid endpoint with valid requirements
        """
        endpoint = item.endpoint
        method = item.method
        authentication = True if item.authentication else False

        given_requirement = EndPointRequires(method=method, authentication=authentication)
        endpoint_requirements, _ = self.endpoints.get(endpoint, (None, None))

        if not endpoint_requirements:
            return False

        return given_requirement == endpoint_requirements


@dataclass
class EndPoint:
    endpoint: str
    method: str
    authentication: str | None
