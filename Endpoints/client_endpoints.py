from typing import Callable
from client_actions import complete_authentication, user_login


class EndPoints:
    def __init__(self):
        self.endpoints: dict[str, Callable] = {
            "authentication/key_exchange": complete_authentication,
            "user/login": user_login,
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
