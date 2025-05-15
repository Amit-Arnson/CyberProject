import base64
import time

from dotenv import load_dotenv
import secrets
import string

import os

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

    random_unique_id = sha256(uuid4().bytes).digest()
    encoded_username = sha256(username.encode()).digest()

    user_id = sha256(encoded_username + random_unique_id).hexdigest()

    return user_id


def generate_session_token(user_id: str) -> str:
    # we add the time when the token is created into the first part of the token. this is so that we can easily
    # track when the token was created without needing a different variable for it.
    current_time = time.time().hex().encode()
    b64_encoded_time = base64.b64encode(current_time).decode()

    # to get the float time back
    # 1) b64decode(bytes)
    # 2) .decode(bytes)
    # 3) float.fromhex(str)

    # generates an uuid4
    random_unique_id = uuid4().bytes
    user_id_bytes = user_id.encode()

    # hashes the randomly generated uuid4 with the user's ID
    random_token = sha256(random_unique_id + user_id_bytes).hexdigest()

    # random bytes to add at the end of the token just so that there is 0% chance for collisions
    end_bytes = os.urandom(8).hex()

    # todo: see if you need to use hmac to sign the token in order to stop tempering and spoofing
    session_token = f"{b64_encoded_time}#{random_token}{end_bytes}"

    return session_token


if __name__ == "__main__":
    # the pepper in secrets.env was created using this script


    def generate_pepper(length=32):
        characters = string.ascii_letters + string.digits + string.punctuation
        generated_pepper = ''.join(secrets.choice(characters) for i in range(length))
        return generated_pepper


    # Example usage:
    pepper = generate_pepper(32)
    print(f"Generated Pepper: {pepper}")  # Keep this pepper secret!