"""
all error classes here are built like this:

class ErrorName(Exception):
    "doc-string explaining what this does"

    def __init__(self, argument: str):
        super().__init__(argument)

        # the passed message to be sent to the client post-error
        self.message = argument

        # the status code the error represents
        self.code = # an integer code
"""


class InvalidPayload(Exception):
    """Error that is thrown when the client passes an invalid payload"""

    # view docstring at the top of the file to see comments.
    def __init__(self, argument: str):
        super().__init__(argument)

        self.message = argument
        self.code = 400


class TooLong(Exception):
    """Error that is thrown when the client's input is "too long" (eg: username with many characters)"""

    # view docstring at the top of the file to see comments.
    def __init__(self, argument: str):
        super().__init__(argument)

        self.message = argument
        self.code = 400


class TooShort(Exception):
    """Error that is thrown when the client's input is "too short" (eg: username with many characters)"""

    # view docstring at the top of the file to see comments.
    def __init__(self, argument: str):
        super().__init__(argument)

        self.message = argument
        self.code = 400


class UserExists(Exception):
    """Error that is thrown if a user that is created already exists"""

    # view docstring at the top of the file to see comments.
    def __init__(self, argument: str):
        super().__init__(argument)

        self.message = argument
        self.code = 409


class InvalidCredentials(Exception):
    """Error that is thrown when the user provides invalid login credentials"""

    # view docstring at the top of the file to see comments.
    def __init__(self, argument: str):
        super().__init__(argument)

        self.message = argument
        self.code = 401


class NoEncryption(Exception):
    """Error that is raised when the client *should* have an encrypted message and the key & IV saved in the cache, yet dont"""

    # view docstring at the top of the file to see comments.
    def __init__(self, argument: str):
        super().__init__(argument)

        self.message = argument
        self.code = 500


class InvalidExtension(Exception):
    """Use this class to throw errors when an unacceptable extension is used"""

    # view docstring at the top of the file to see comments.
    def __init__(self, argument: str):
        super().__init__(argument)

        self.message = argument
        self.code = 400
