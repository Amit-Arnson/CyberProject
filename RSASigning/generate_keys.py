from Crypto.PublicKey import RSA

# Generate a 4096-bit RSA key pair
key = RSA.generate(4096)

# Export private key in PEM format (unencrypted)
private_key_pem = key.export_key()
with open("../RSASigning/private_key.pem", "wb") as f:
    f.write(private_key_pem)

# Export public key in PEM format
public_key_pem = key.publickey().export_key()
with open("../RSASigning/public_key.pem", "wb") as f:
    f.write(public_key_pem)
