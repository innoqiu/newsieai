from solders.keypair import Keypair
import base58


kp = Keypair()


pubkey = str(kp.pubkey())


secret_bytes = bytes(kp)
secret_base58 = base58.b58encode(secret_bytes).decode("utf-8")


print(f"PublicKey:{pubkey}")
print(f"SecretKey:{secret_base58}")
