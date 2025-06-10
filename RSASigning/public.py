import asyncio
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP


# Load public key once
with open("RSASigning/public_key.pem", "rb") as f:
    public_key = RSA.import_key(f.read())


def rsa_encrypt(plaintext: bytes) -> bytes:
    cipher = PKCS1_OAEP.new(public_key)
    return cipher.encrypt(plaintext)


def rsa_decrypt(ciphertext: bytes) -> bytes:
    cipher = PKCS1_OAEP.new(public_key)
    return cipher.decrypt(ciphertext)


async def async_rsa_encrypt(plaintext: bytes) -> bytes:
    loop: asyncio.ProactorEventLoop = asyncio.get_event_loop()

    return await loop.run_in_executor(None, rsa_encrypt, plaintext)


async def async_rsa_decrypt(plaintext: bytes):
    loop: asyncio.ProactorEventLoop = asyncio.get_event_loop()

    return await loop.run_in_executor(None, rsa_decrypt, plaintext)


async def verify_async(content: bytes, signature: bytes) -> bool:
    loop: asyncio.ProactorEventLoop = asyncio.get_event_loop()

    return await loop.run_in_executor(None, _verify_sync, content, signature)


def _verify_sync(content: bytes, signature: bytes) -> bool:
    hashed_content = SHA256.new(content)
    try:
        pkcs1_15.new(public_key).verify(hashed_content, signature)
        return True
    except (ValueError, TypeError):
        return False
