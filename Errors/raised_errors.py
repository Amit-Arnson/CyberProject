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
