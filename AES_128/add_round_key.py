# add_round_key.py

__all__ = [
    "add_round_key"
]

# Add round key (using XOR operation)
def add_round_key(state: list[list[int]], round_key: list[list[int]]) -> list[list[int]]:
    for row in range(4):
        for col in range(4):
            state[row][col] ^= round_key[row][col]

    return state

def main():

    import random

    state = [[random.randint(0, 255) for _ in range(4)] for _ in range(4)]
    key = [[random.randint(0, 255) for _ in range(4)] for _ in range(4)]

    for row in state:
        print(row)

    print()

    cipher = add_round_key(state, key)

    for row in cipher:
        print(row)

    print()

    inverse = add_round_key(cipher, key)

    for row in inverse:
        print(row)

if __name__ == '__main__':
    main()