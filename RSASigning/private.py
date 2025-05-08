from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP


import asyncio

# Load private key for signing
with open("RSASigning/private_key.pem", "rb") as f:
    private_key = RSA.import_key(f.read())


def rsa_encrypt(plaintext: bytes) -> bytes:
    cipher = PKCS1_OAEP.new(private_key)
    return cipher.encrypt(plaintext)


def rsa_decrypt(ciphertext: bytes) -> bytes:
    cipher = PKCS1_OAEP.new(private_key)
    return cipher.decrypt(ciphertext)


async def async_rsa_encrypt(plaintext: bytes):
    loop: asyncio.ProactorEventLoop = asyncio.get_event_loop()

    return await loop.run_in_executor(None, rsa_encrypt, plaintext)


async def async_rsa_decrypt(plaintext: bytes):
    loop: asyncio.ProactorEventLoop = asyncio.get_event_loop()

    return await loop.run_in_executor(None, rsa_decrypt, plaintext)


async def sign_async(content: bytes):
    loop: asyncio.ProactorEventLoop = asyncio.get_event_loop()

    return await loop.run_in_executor(None, sign_sync, content, private_key)


def sign_sync(content: bytes):
    hashed_content = SHA256.new(content)
    return pkcs1_15.new(private_key).sign(hashed_content)


