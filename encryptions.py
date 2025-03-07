import base64

import asyncio
from typing import Optional

import pyaes

from AES_128 import cbc


from Crypto.Cipher import AES


def pad(plaintext):
    """Pads the plaintext to make its length a multiple of 16 bytes (block size)."""
    padding_length = 16 - (len(plaintext) % 16)
    padding = chr(padding_length) * padding_length
    return plaintext + padding.encode()

def unpad(plaintext):
    """Removes the padding from the plaintext."""
    padding_length = plaintext[-1]  # The last byte represents the padding length
    return plaintext[:-padding_length]

def aes_cbc_encrypt(plaintext, key, iv):
    """Encrypts plaintext using AES CBC mode."""

    # Create AES cipher in CBC mode
    cipher = AES.new(key, AES.MODE_CBC, iv)

    # Encrypt the padded plaintext
    ciphertext = cipher.encrypt(pad(plaintext))

    # Return the IV and ciphertext (both are needed for decryption)
    return base64.b64encode(iv + ciphertext)  # Encode as Base64 for easier storage/transmission

def aes_cbc_decrypt(ciphertext, key):
    """Decrypts ciphertext using AES CBC mode."""
    # Decode the Base64 encoded ciphertext
    ciphertext = base64.b64decode(ciphertext)

    iv = ciphertext[:16]
    # Extract the IV (first 16 bytes) and the encrypted message
    actual_ciphertext = ciphertext[16:]

    # Create AES cipher in CBC mode with the extracted IV
    cipher = AES.new(key, AES.MODE_CBC, iv)

    # Decrypt and unpad the plaintext
    plaintext = cipher.decrypt(actual_ciphertext)
    return unpad(plaintext)


# todo: fix my cbc code and not use pycryptodome
# issue: when sending over large data or data in general very fast, it breaks the padding and unpadding for some reason
class EncryptedTransport(asyncio.Transport):
    def __init__(self, transport: asyncio.Transport, key: Optional[bytes] = None, iv: Optional[bytes] = None):
        super().__init__()
        self._transport = transport
        self.key = key
        self.iv = iv

        if key and len(key) != 16:
            raise ValueError(f"expected 16 byte key, got {len(key)} bytes instead")

        if iv and len(iv) != 16:
            raise ValueError(f"expected 16 byte IV, got {len(iv)} bytes instead")

    def write(self, data: bytes) -> None:
        """
        uses asyncio.Transport's write() whilst also encrypting using AES-128-CBC.
        data is only encrypted if a key and iv are passed
        """
        if self.key and self.iv:
            data = pad(data)

            data = aes_cbc_encrypt(data, key=self.key, iv=self.iv)

            #data = cbc.cbc_encrypt(data, key=self.key, iv=self.iv)
            #data = aes.encrypt(data)

        self._transport.write(data)

    def read(self, data: bytes) -> bytes:
        """
        decrypts the data using the key and iv that were initially passed.
        data is only decrypted if a key and iv are passed
        """

        if self.key and self.iv:
            data = aes_cbc_decrypt(data, key=self.key)
            data = unpad(data)

            #data = cbc.cbc_decrypt(data, key=self.key, iv=self.iv)
            #data = aes.decrypt(data)

        return data

    def can_write_eof(self) -> bool:
        """
        Returns whether the transport can send an EOF (end of file).
        """
        return self._transport.can_write_eof()

    def write_eof(self) -> None:
        """
        Writes an EOF (end of file) marker to the transport.
        """
        self._transport.write_eof()

    def get_extra_info(self, name: str, default: Optional[None] = None) -> Optional[None]:
        """
        Returns extra information about the transport (such as peername, sockname, etc.).
        """
        return self._transport.get_extra_info(name, default)

    def close(self) -> None:
        """
        Closes the underlying transport.
        """
        self._transport.close()

    def is_closing(self) -> bool:
        """
        Checks if the transport is closing.
        """
        return self._transport.is_closing()

    def set_protocol(self, protocol: asyncio.Protocol) -> None:
        """
        Sets the protocol that the transport is associated with.
        """
        self._transport.set_protocol(protocol)

    def get_write_buffer_size(self) -> int:
        """
        Returns the current write buffer size of the transport.
        """
        return self._transport.get_write_buffer_size()

    def __del__(self):
        """
        Cleanup when the object is deleted.
        """
        self.close()