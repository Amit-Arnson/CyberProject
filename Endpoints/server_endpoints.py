from typing import Callable
from server_actions import authenticate_client, user_signup, user_login

from dataclasses import dataclass


# todo: rewrite. dont over complicate this class.
class EndPointRequires:
    """a class to easily represent the method and authentication requirements of endpoints, as well as compare them"""

    def __init__(self, method: str, authentication: bool):
        # which method it requires
        self.method = method
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

            # song/upload is used to upload: the song file, description, tabs (images), artist, name and genre tags.
            "song/upload": (
                EndPointRequires(method="post", authentication=True),
                # todo: create function to handle uploading songs
            )
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
