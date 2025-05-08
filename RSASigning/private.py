from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

from Crypto.PublicKey import RSA

import asyncio

# Load private key for signing
with open("RSASigning/private_key.pem", "rb") as f:
    private_key = RSA.import_key(f.read())


async def sign_async(content: bytes):
    loop: asyncio.ProactorEventLoop = asyncio.get_event_loop()

    return await loop.run_in_executor(None, sign_sync, content, private_key)


def sign_sync(content: bytes):
    hashed_content = SHA256.new(content)
    return pkcs1_15.new(private_key).sign(hashed_content)
