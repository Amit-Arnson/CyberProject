from key_expand import expand_key
from mix_columns import mix_columns, inverse_mix_columns
from add_round_key import add_round_key
from state import state_to_bytes, bytes_to_state
from shift_rows import inverse_shift_rows, shift_rows
from substitute import substitute, inverse_substitute


def encrypt(plaintext: str | bytes, key: bytes) -> bytes:
    if isinstance(plaintext, str):
        plaintext = plaintext.encode()

    if len(plaintext) != 16:
        raise AttributeError("data must be 16 bytes long")

    round_keys = expand_key(main_key=key)
    data_state = bytes_to_state(data=plaintext)

    # add the first round key
    round_key_state = bytes_to_state(round_keys[0])
    add_round_key(state=data_state, round_key=round_key_state)

    for round_key in round_keys[1:-1]:
        substitute(state=data_state)
        shift_rows(state=data_state)
        mix_columns(state=data_state)
        round_key_state = bytes_to_state(data=round_key)
        add_round_key(state=data_state, round_key=round_key_state)

    # Final round (no mix_columns)
    substitute(state=data_state)
    shift_rows(state=data_state)
    round_key_state = bytes_to_state(data=round_keys[-1])
    add_round_key(state=data_state, round_key=round_key_state)

    cipher = state_to_bytes(state=data_state)

    return cipher


def decrypt(cipher: bytes, key: bytes) -> bytes:
    if len(cipher) != 16:
        raise AttributeError("data must be 16 bytes long")

    round_keys = expand_key(main_key=key)

    # since we start with the last key when we decrypt, we need to reverse the expanded keys gotten from the main key
    round_keys.reverse()

    data_state = bytes_to_state(data=cipher)

    # add the first round key
    round_key_state = bytes_to_state(round_keys[0])
    add_round_key(state=data_state, round_key=round_key_state)

    for round_key in round_keys[1:-1]:
        inverse_shift_rows(state=data_state)
        inverse_substitute(state=data_state)
        round_key_state = bytes_to_state(data=round_key)
        add_round_key(state=data_state, round_key=round_key_state)
        inverse_mix_columns(state=data_state)

    # Final round (no inverse_mix_columns)
    inverse_shift_rows(state=data_state)
    inverse_substitute(state=data_state)
    round_key_state = bytes_to_state(data=round_keys[-1])
    add_round_key(state=data_state, round_key=round_key_state)

    text = state_to_bytes(state=data_state)

    return text


def main():
    data = "1234567890123456"
    key = bytes([0x20, 0x65, 0x0f, 0xb3] * 4)

    cipher = encrypt(plaintext=data, key=key)
    print(cipher)
    text = decrypt(cipher=cipher, key=key)
    print(text.decode())


if __name__ == "__main__":
    main()