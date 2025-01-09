import typing

from sympy import prime, sieve
from Crypto.Util import number
import random
import hashlib

import sympy
import random


def generate_prime(length) -> int:
    while True:
        candidate = random.getrandbits(length)
        if sympy.isprime(candidate):
            return candidate



# TODO: replace the PyCryptoDome dependency with sympy
# TODO: create "generate prime based on length" function using sympy isprime
class KDF:
    def __init__(self, data: bytes, size: int, iterations: int = 10000, salt: bytes = None):
        self.data = data
        self.size = size
        self.iterations = iterations
        self.salt = salt

    def hash(self):
        return hashlib.sha256(self.data).digest()

    def derive_key(self) -> bytes:
        # note: while I am altering the original data (here and in the loop), im not using the original anywhere else in the class, so it's probably fine
        if self.salt:
            self.data += self.salt

        derived_key = self.data

        for _ in range(self.iterations):
            self.data = self.hash()

            # XOR the hash output with the accumulated derived key
            derived_key = self._xor(derived_key, self.data)

        return derived_key[:self.size]

    @staticmethod
    def _xor(a: bytes, b: bytes) -> bytes:
        return bytes(x ^ y for x, y in zip(a, b))


class DHE:
    def __init__(self, p: int, g: int = 5, e: int = None):
        """
        :param e: (private) exponent, never shared. used in all calculations
        :param p: (publicly shared) prime number modulus, both sides must have the same p
        :param g: (publicly shared) base, both sides must have the same g
        """

        # will generate the secret exponent if you don't provide one.
        self.e = e if e else self._generate_secret_exponent()
        self.g = g
        self.p = p

    def _generate_secret_exponent(self) -> int:
        """generates your secret exponent"""
        return random.randint(2, self.p - 2)

    def calculate_public(self):
        """
        :return: calculates the public value: (g^e) % p
        """
        return pow(self.g, self.e, self.p)

    def calculate_mutual(self, peer_public_value: int) -> int:
        """
        :param peer_public_value: the public value given by the other side
        :return: calculates the mutual key: ((public_value)^e) % p
        """
        return pow(peer_public_value, self.e, self.p)

    @staticmethod
    def kdf_derive(mutual_key: int, size: int = 16, iterations: int = 10000, salt: bytes = None):
        """
        :param mutual_key: the public mutual key calculated in self.calculate_mutual()
        :param size: the final size of the key
        :param iterations: how many times it will iteratively hash the key material with XOR
        :param salt: added to the data before the iterations start
        :return:
        """
        mutual_key_bytes = str(mutual_key).encode()
        kdf = KDF(mutual_key_bytes, size=size, iterations=iterations, salt=salt)
        return kdf.derive_key()


def generate_initial_dhe(mod_length: int = 200, base: int = typing.Literal[3, 5]) -> DHE:
    prime_mod = generate_prime(mod_length)

    server_secret_exponent = random.randint(2, prime_mod - 2)

    return DHE(e=server_secret_exponent, p=prime_mod, g=base)


def generate_dhe_response(mod: int, base: int) -> DHE:
    # client_secret_key_prime = number.getRandomRange(base, prime_mod-1)
    client_secret_exponent = random.randint(2, mod - 2)

    return DHE(e=client_secret_exponent, p=mod, g=base)


# todo: check about the exponent https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange
def main():
    # SERVER
    prime_mod = generate_prime(200)

    base = 3

    server_secret_exponent = random.randint(2, prime_mod - 2)

    server_dhe = DHE(e=server_secret_exponent, p=prime_mod, g=base)
    public_server_val = server_dhe.calculate_public()

    # CLIENT
    # the client is given:
    # 1) base
    # 2) mod
    # 3) public value

    # client_secret_key_prime = number.getRandomRange(base, prime_mod-1)
    client_secret_exponent = random.randint(2, prime_mod - 2)

    client_dhe = DHE(e=client_secret_exponent, p=prime_mod, g=base)

    public_client_val = client_dhe.calculate_public()

    # SERVER

    server_mutual = server_dhe.calculate_mutual(peer_public_value=public_client_val)

    # CLIENT

    client_mutual = client_dhe.calculate_mutual(peer_public_value=public_server_val)

    print(server_mutual)
    print(client_mutual)

    # test to see that they are all the same
    salt = b"abcdefghijkl"
    # yes, I know salt is meant to be random but this is just a test, so I think it's alright to use a none-random salt.

    # server with server_mutual
    print(server_dhe.kdf_derive(server_mutual, size=32, iterations=1000, salt=salt))

    # server with client mutual
    print(server_dhe.kdf_derive(client_mutual, size=32, iterations=1000, salt=salt))

    # client with server mutual
    print(client_dhe.kdf_derive(server_mutual, size=32, iterations=1000, salt=salt))

    # if it all works correctly, it should output the same result.


if __name__ == "__main__":
    main()