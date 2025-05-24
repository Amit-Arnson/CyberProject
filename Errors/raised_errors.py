class BaseError(Exception):
    """Base class for all custom exceptions."""

    def __init__(self, argument: str, code: int, extra: dict = None):
        super().__init__(argument)

        # Initialize common attributes
        self.message = argument
        self.code = code
        self.extra = extra if extra else {}


class InvalidPayload(BaseError):
    """Error that is thrown when the client passes an invalid payload."""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=400, extra=extra)


class InvalidDataType(BaseError):
    """Error that is thrown when the client passes an invalid type for an expected input."""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=400, extra=extra)


class TooLong(BaseError):
    """Error that is thrown when the client's input is 'too long' (e.g., username with too many characters)."""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=400, extra=extra)


class TooShort(BaseError):
    """Error that is thrown when the client's input is 'too short' (e.g., username with too few characters)."""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=400, extra=extra)


class UserExists(BaseError):
    """Error that is thrown if a user that is created already exists."""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=409, extra=extra)


class InvalidCredentials(BaseError):
    """Error that is thrown when the user provides invalid login credentials."""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=401, extra=extra)


class NoEncryption(BaseError):
    """Error that is raised when the client *should* have an encrypted message but doesn't."""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=500, extra=extra)


class InvalidCodec(BaseError):
    """Error that is thrown when an unacceptable file format/codec is used."""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=400, extra=extra)


class InvalidFile(BaseError):
    """Error that is thrown when a file fails an FFprobe for any reason"""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=400, extra=extra)


class InvalidValue(BaseError):
    """A general error that is thrown when a client sends over a value that is not valid (e.g., a value that is "too big/small" (such
    as an integer that is over/under the value that the server expects)"""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=400, extra=extra)


class InvalidMessage(BaseError):
    """A general error that is thrown when a client sends over a message's bytes that do not properly form a ClientMessage"""
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=400, extra=extra)


class NotFound(BaseError):
    """
    An error that is shown when a specific combination of endpoint+method is not found
    """
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=404, extra=extra)


class Forbidden(BaseError):
    """
    An error that is shown when an invalid session token is passed, or a user with a session token that doesn't have
    the correct authority tries to do something that requires a higher authority
    """
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=403, extra=extra)


class RateLimitReached(BaseError):
    def __init__(self, argument: str, extra: dict = None):
        super().__init__(argument, code=429, extra=extra)
