"""Ed25519 signature over the root key and chain parameters (NavIC proposal uses EdDSA)."""
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def _payload(root: bytes, params: dict) -> bytes:
    return root + json.dumps(params, sort_keys=True).encode()


def sign_root(sk: Ed25519PrivateKey, root: bytes, params: dict) -> bytes:
    return sk.sign(_payload(root, params))


def verify_root(pk: Ed25519PublicKey, root: bytes, params: dict, sig: bytes) -> bool:
    try:
        pk.verify(sig, _payload(root, params))
        return True
    except InvalidSignature:
        return False
