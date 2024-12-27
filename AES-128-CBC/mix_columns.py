# mix_columns.py

__all__ = [
    "mix_columns",
    "inverse_mix_columns"
]

# Finite field multiplication in GF(2^8) using integers only
def g_mul(a: int, b: int) -> int:
    p = 0
    while b > 0:
        if b & 1:  # If the lowest bit of b is 1
            p ^= a  # Add a to p
        a <<= 1  # Multiply a by 2
        if a & 0x100:  # If a is greater than 255, reduce by the AES irreducible polynomial
            a ^= 0x1b  # 0x1b is the AES irreducible polynomial (x^8 + x^4 + x^3 + x + 1)
        b >>= 1  # Shift b to the right to process the next bit
    return p & 0xFF  # Ensure result is within 8 bits

# MixColumns operation
def mix_columns(state: list[list[int]]) -> list[list[int]]:
    for i in range(4):
        a0, a1, a2, a3 = state[i][0], state[i][1], state[i][2], state[i][3]

        # Perform the matrix multiplication in GF(2^8)
        state[i][0] = g_mul(a0, 2) ^ g_mul(a1, 3) ^ a2 ^ a3
        state[i][1] = a0 ^ g_mul(a1, 2) ^ g_mul(a2, 3) ^ a3
        state[i][2] = a0 ^ a1 ^ g_mul(a2, 2) ^ g_mul(a3, 3)
        state[i][3] = g_mul(a0, 3) ^ a1 ^ a2 ^ g_mul(a3, 2)

    return state

def inverse_mix_columns(state: list[list[int]]) -> list[list[int]]:
    for i in range(4):
        a0, a1, a2, a3 = state[i][0], state[i][1], state[i][2], state[i][3]

        # Perform the matrix multiplication using the inverse matrix in GF(2^8)
        # 0x0E -> 14, 0x0B -> 11, 0x0D -> 13, 0x09 -> 9
        state[i][0] = g_mul(a0, 14) ^ g_mul(a1, 11) ^ g_mul(a2, 13) ^ g_mul(a3, 9)
        state[i][1] = g_mul(a0, 9) ^ g_mul(a1, 14) ^ g_mul(a2, 11) ^ g_mul(a3, 13)
        state[i][2] = g_mul(a0, 13) ^ g_mul(a1, 9) ^ g_mul(a2, 14) ^ g_mul(a3, 11)
        state[i][3] = g_mul(a0, 11) ^ g_mul(a1, 13) ^ g_mul(a2, 9) ^ g_mul(a3, 14)

    return state

def main():

    # Example state matrix (4x4 matrix in AES) in integers
    state = [
        [135, 242, 77, 151],  # [0x87, 0xF2, 0x4D, 0x97]
        [110, 76, 144, 236],  # [0x6E, 0x4C, 0x90, 0xEC]
        [70, 231, 74, 195],   # [0x46, 0xE7, 0x4A, 0xC3]
        [166, 140, 216, 149]  # [0xA6, 0x8C, 0xD8, 0x95]
    ]

    # Apply the MixColumns transformation
    mixed_state = mix_columns(state)

    # Print the result in integers
    for row in mixed_state:
        print([x for x in row])

    print()

    inverse_state = inverse_mix_columns(mixed_state)

    # Print the result in integers
    for row in inverse_state:
        print([x for x in row])

    print(state == inverse_state)

if __name__ == '__main__':
    main()