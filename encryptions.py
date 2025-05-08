import base64

import asyncio
from typing import Optional

from AES_128 import cbc

from Crypto.Cipher import AES

from hashlib import sha256
from hmac import compare_digest


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


# todo: fix my cbc code and not use pycryptodome, currently it seems that my code is simply too slow
# issue: when sending over large data or data in general very fast, it breaks the padding and unpadding for some reason
class EncryptedTransport(asyncio.Transport):
    def __init__(
            self,
            transport: asyncio.Transport,
            key: Optional[bytes] = None,
            iv: Optional[bytes] = None,
            hmac_key: Optional[bytes] = None,
    ):
        super().__init__()
        self._transport = transport
        self.key = key
        self.iv = iv

        # used to protect against bit flipping attacks
        self.hmac_key = hmac_key

        self._buffer = b""  # Buffer for incoming fragmented data
        self._expected_data_length = None

        if key and len(key) != 16:
            raise ValueError(f"expected 16 byte key, got {len(key)} bytes instead")

        if iv and len(iv) != 16:
            raise ValueError(f"expected 16 byte IV, got {len(iv)} bytes instead")

    def _hmac_digest(self, content: bytes) -> bytes:
        return sha256(self.hmac_key + sha256(self.hmac_key + content).digest()).digest()

    def _implement_hmac(self, data: bytes) -> bytes:
        """adds a 32 byte HMAC using a given key and sha256"""

        if not self.hmac_key:
            return data

        added_hmac = self._hmac_digest(data)

        return data + added_hmac

    def _verify_hmac(self, data: bytes) -> bytes:
        if not self.hmac_key:
            return data

        added_hmac, original_data = data[-32:], data[:-32]

        expected_hmac = self._hmac_digest(original_data)

        # i use compare_digest instead of == to prevent timing attacks. Unlike ==, compare_digest performs a constant-time comparison,
        # preventing attackers from inferring information based on comparison timing.
        if not compare_digest(expected_hmac, added_hmac):
            raise ValueError("HMAC verification failed")

        return original_data

    def write(self, data: bytes) -> None:
        """
        Uses asyncio.Transport's write() while encrypting using AES-128-CBC.
        Data is only encrypted if a key and IV are passed.
        """

        if self.key and self.iv:
            encrypted_data = aes_cbc_encrypt(data, key=self.key, iv=self.iv)
            encrypted_data = self._implement_hmac(encrypted_data)

            # Calculate and include the length prefix (16 bytes), this is practically a buffer protocol
            data_length_block = str(len(encrypted_data)).rjust(16, "0").encode()

            data = data_length_block + encrypted_data

        # Write the data to the transport
        self._transport.write(data)

    def _is_valid_length_prefix(self, prefix: bytes) -> bool:
        """Validates whether the prefix contains a valid numeric length."""
        try:
            int(prefix.decode())
            return True
        except ValueError:
            return False

    def read(self, data: bytes) -> bytes:
        """
        Decrypts the incoming data using the key and IV that were initially passed, using AES-128-CBC.
        Buffers fragmented data until it forms full blocks.
        """

        if self.key and self.iv:
            self._buffer += data

            # Check if we have enough data for the length prefix (16 bytes)
            if len(self._buffer) < 16:
                return b""  # Wait for more data

            # If we don't have an expected length yet, read the first 16 bytes.
            if not self._expected_data_length:
                if self._is_valid_length_prefix(self._buffer[:16]):
                    self._expected_data_length = int(self._buffer[:16].decode())
                    self._buffer = self._buffer[16:]  # Remove the length prefix
                else:
                    print("Invalid length prefix, clearing buffer.")
                    self._buffer = b""  # Clear invalid data
                    return b""

            # Wait until the full payload has been received
            if len(self._buffer) < self._expected_data_length:
                return b""  # Wait for more data

            # Extract the full payload
            cipher = self._buffer[:self._expected_data_length]
            self._buffer = self._buffer[self._expected_data_length:]  # Remove processed data

            # now that we have the whole cipher, we can finally check that the HMAC matches before decrypting
            cipher = self._verify_hmac(cipher)

            decrypted_data = aes_cbc_decrypt(cipher, key=self.key)

            # Clear buffer and reset state
            self._clear_buffer()
            self._expected_data_length = None

            return decrypted_data

        return data

    def _clear_buffer(self, leeway: int = 0):
        """clears the current buffer so that we don't accumulate tons of data on the memory"""
        if len(self._buffer) > self._expected_data_length + leeway:
            self._buffer = b""

    def can_write_eof(self) -> bool:
        return self._transport.can_write_eof()

    def write_eof(self) -> None:
        self._transport.write_eof()

    def get_extra_info(self, name: str, default: Optional[None] = None) -> ...:
        return self._transport.get_extra_info(name, default)

    def close(self) -> None:
        self._transport.close()

    def is_closing(self) -> bool:
        return self._transport.is_closing()

    def set_protocol(self, protocol: asyncio.Protocol) -> None:
        self._transport.set_protocol(protocol)

    def get_write_buffer_size(self) -> int:
        return self._transport.get_write_buffer_size()

    def __del__(self):
        self.close()
