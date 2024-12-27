# structure.py


__all__ = [
	"state_to_bytes",
	"bytes_to_state"
]

# Helper function: Convert byte data to a list of integers for simplicity
def bytes_to_state(data: bytes) -> list[list[int]]:
	return [list(data)[i:i + 4] for i in range(0, 16, 4)]

# Helper function: Convert a list of integers back to bytes
def state_to_bytes(state: list[list[int]]) -> bytes:

	flat_state: list[int] = []  # we used it cus there is a method to convert list[int] to bytes

	for i in range(4):
		flat_state.extend(state[i][j] for j in range(4))

	return bytes(flat_state)