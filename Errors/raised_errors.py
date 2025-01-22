class InvalidPayload(Exception):
    """Error that is thrown when the client passes an invalid payload"""

    def __init__(self, argument: str):
        super().__init__(argument)

        # the passed message to be sent to the client post-error
        self.message = argument

        # the status code the error represents
        self.code = 400


class TooLong(Exception):
    """Error that is thrown when the client's input is "too long" (eg: username with many characters)"""

    def __init__(self, argument: str):
        super().__init__(argument)

        # the passed message to be sent to the client post-error
        self.message = argument

        # the status code the error represents
        self.code = 400


class UserExists(Exception):
    """Error that is thrown if a user that is created already exists"""

    def __init__(self, argument: str):
        super().__init__(argument)

        # the passed message to be sent to the client post-error
        self.message = argument

        # the status code the error represents
        self.code = 409


class InvalidCredentials(Exception):
    """Error that is thrown when the user provides invalid login credentials"""

    def __init__(self, argument: str):
        super().__init__(argument)

        # the passed message to be sent to the client post-error
        self.message = argument

        # the status code the error represents
        self.code = 401


class NoEncryption(Exception):
    """Error that is raised when the client *should* have an encrypted message and the key & IV saved in the cache, yet dont"""

    def __init__(self, argument: str):
        super().__init__(argument)

        # the passed message to be sent to the client post-error
        self.message = argument

        # the status code the error represents
        self.code = 500