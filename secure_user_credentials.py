from dotenv import load_dotenv

import os
import secrets

from uuid import uuid4
from hashlib import sha256

load_dotenv("secrets.env")
PEPPER: str = os.getenv("PEPPER")


def generate_salt(salt_length: int = 16) -> bytes:
    return secrets.token_bytes(salt_length)


def generate_hashed_password(password: str, salt: bytes = None) -> tuple[str, bytes]:
    """
    generates a securely hashed password, using pepper, randomly generated salt and sha256.
    returns: tuple[hashed_password (str), pepper (bytes)]

    you can use this function as part of the password authentication by passing your own salt.
    under normal circumstances (such as creating a new hash) DO NOT pass your own salt.
    """

    if not salt:
        salt = generate_salt()

    encoded_password = password.encode()
    encoded_pepper = PEPPER.encode()

    hashed_password = sha256(encoded_pepper + encoded_password + salt).hexdigest()

    return (
        hashed_password,
        salt
    )


def authenticate_password(password: str, salt: bytes, hashed_password: str) -> bool:
    """checks if the given password matches up with the stored password in the database"""

    given_password_hash, _ = generate_hashed_password(password=password, salt=salt)

    return hashed_password == given_password_hash


def generate_user_id(username: str) -> str:
    """creates a random user ID based on the username and a random uuid4"""

    random_user_id = sha256(uuid4().bytes).digest()
    encoded_username = sha256(username.encode()).digest()

    user_id = sha256(encoded_username + random_user_id).hexdigest()

    return user_id


# the pepper in secrets.env was created using this script
"""
import secrets
import string

def generate_pepper(length=32):
    characters = string.ascii_letters + string.digits + string.punctuation
    pepper = ''.join(secrets.choice(characters) for i in range(length))
    return pepper

# Example usage:
pepper = generate_pepper(32)
print(f"Generated Pepper: {pepper}")  # Keep this pepper secret!
"""