# shift_rows.py


__all__ = [
    "shift_rows",
    "inverse_shift_rows"
]


def shift_rows(state: list[list[int]]) -> list[list[int]]:
    # Second row shifts left by 1
    # Third row shifts left by 2
    # Fourth row shifts left by 3

    for i in range(1, 4):
        state[i][:] = state[i][i:] + state[i][:i]

    return state


# Inverse shift rows (shifting in the opposite direction)
def inverse_shift_rows(state: list[list[int]]) -> list[list[int]]:
    # Second row shifts right by 1
    # Third row shifts right by 2
    # Fourth row shifts right by 3

    for i in range(1, 4):
        state[i][:] = state[i][-i:] + state[i][:-i]

    return state

def main():

    import random

    state = [[random.randint(0, 255) for _ in range(4)] for _ in range(4)]

    for row in state:
        print(row)

    print()

    shift_rows(state)

    for row in state:
        print(row)

    print()

    inverse_shift_rows(state)

    for row in state:
        print(row)

if __name__ == '__main__':
    main()