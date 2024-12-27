from api import encrypt, decrypt
import os


def pad(data: str | bytes) -> bytes:
    if isinstance(data, str):
        data = data.encode()

    original_data_length = str(len(data)).encode()
    data_list = split_data_to_block(data=data)

    # this is so that we will always have 16 byte blocks
    data_list[-1] = data_list[-1].ljust(16, b"0")
    data = b"".join(data_list)

    original_data_length = original_data_length.rjust(16, b"0")

    return data + original_data_length


def unpad(data: bytes) -> bytes:
    original_length = int(data[-16:])
    original_data = data[0:original_length]
    return original_data


def split_data_to_block(data: bytes) -> list[bytes]:
    return [data[i:i+16] for i in range(0, len(data), 16)]


def block_to_data(data: list[bytes]) -> bytes:
    return b"".join(data)


def generate_iv() -> bytes:
    return os.urandom(16)


def add_iv(data_list: list[bytes], iv: bytes) -> list[bytes]:
    first_block = bytearray(data_list[0])

    for i in range(16):
        first_block[i] ^= iv[i]

    data_list[0] = bytes(first_block)

    return data_list


def xor_at_position(data_list: list[bytes], xor: bytes, position: int) -> list[bytes]:
    block = bytearray(data_list[position])

    for i in range(16):
        block[i] ^= xor[i]

    data_list[position] = bytes(block)

    return data_list


def cbc_encrypt(plaintext: str | bytes, key: bytes, iv: bytes) -> bytes:
    if isinstance(plaintext, str):
        plaintext = plaintext.encode()

    padded_data = pad(data=plaintext)
    data_blocks = split_data_to_block(data=padded_data)

    # the first case of XOR is with the iv, but since i need to use it in the for-loop at the start, the name doesnt match
    latest_cipher = iv

    cipher_list = []
    for i, block in enumerate(data_blocks):
        xor_at_position(data_list=data_blocks, xor=latest_cipher, position=i)
        latest_cipher = encrypt(plaintext=block, key=key)
        cipher_list.append(latest_cipher)

    return block_to_data(cipher_list)


def cbc_decrypt(cipher: bytes, key: bytes, iv: bytes) -> bytes:
    data_blocks = split_data_to_block(data=cipher)

    # the first case of XOR is with the iv, but since i need to use it in the for-loop at the start, the name doesnt match
    latest_cipher = iv

    plain_list = []
    for i, block in enumerate(data_blocks):
        decrypted_block = decrypt(cipher=block, key=key)
        xor_at_position(data_list=data_blocks, xor=latest_cipher, position=i)
        latest_cipher = block
        plain_list.append(decrypted_block)

    plain_data = block_to_data(plain_list)

    return unpad(plain_data)


def main():
    data = "abcdabcdabvcabcaafawfawfawfawfafafsegsdgasgaaSGSDHSAFDRHgda"

    key = bytes([0x20, 0x65, 0x0f, 0xb3] * 4)

    iv = generate_iv()
    cipher = cbc_encrypt(plaintext=data, key=key, iv=iv)
    print(cipher)
    plaintext = cbc_decrypt(cipher=cipher, key=key, iv=iv)
    print(plaintext)


if __name__ == "__main__":
    main()