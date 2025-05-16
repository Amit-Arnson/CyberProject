from typing import Callable
from client_server_errors import pre_message_error, login_error, signup_error, song_upload_error


class ErrorEndPoints:
    def __init__(self):
        self.endpoints: dict[str, Callable] = {
            # the "errors" endpoint sole purpose is for invalid ClientMessage formation from the client data bytes. this
            # is because we cant know the intended endpoint if we cant build the client message
            "errors": pre_message_error,
            "user/login/error": login_error,
            "user/signup/login/error": signup_error,
            "song/upload/finish/error": song_upload_error,
            "song/upload/error": song_upload_error,
            "song/upload/file/error": song_upload_error,
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
