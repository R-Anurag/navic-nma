import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nma.tesla.keychain import KeyChain, hash_down
from nma.tesla.rootkey import sign_root, verify_root
from nma.tesla.safety import disclosure_time, key_not_yet_disclosed
from nma.tesla.tags import TagAccumulator, check_tag, hmac_trunc, make_tag
from nma.tesla.verify import KeyVerifier


def test_hmac_rfc4231_case2():
    full = "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
    assert hmac_trunc(b"Jefe", b"what do ya want for nothing?", 256) == int(full, 16)
    assert hmac_trunc(b"Jefe", b"what do ya want for nothing?", 32) == 0x5BDCC146
    assert hmac_trunc(b"Jefe", b"what do ya want for nothing?", 40) == 0x5BDCC146BF


def test_chain_relation():
    c = KeyChain(50, seed=1)
    assert len(c.root) == 16
    for i in range(50):
        assert c.key(i) == hashlib.sha256(c.key(i + 1)).digest()[:16]


def test_valid_chain_verifies_in_and_out_of_order():
    c = KeyChain(100, seed=2)
    v = KeyVerifier(c.root)
    assert v.verify(40, c.key(40))
    assert v.verify(10, c.key(10))  # out of order: earlier key after later one
    assert v.verify(41, c.key(41))


def test_flipped_bit_fails_everywhere():
    c = KeyChain(20, seed=3)
    for i in range(1, 21):
        for bit in (0, 63, 127):
            k = bytearray(c.key(i))
            k[bit // 8] ^= 1 << (bit % 8)
            assert not KeyVerifier(c.root).verify(i, bytes(k))


def test_wrong_root_fails():
    c, other = KeyChain(10, seed=4), KeyChain(10, seed=5)
    assert not KeyVerifier(other.root).verify(5, c.key(5))


def test_tags_and_accumulation():
    k = KeyChain(5, seed=6).key(3)
    t = make_tag(k, b"ephemeris", prn=7, interval=3, bits=40)
    assert check_tag(k, b"ephemeris", 7, 3, t, bits=40)
    assert not check_tag(k, b"ephemeriz", 7, 3, t, bits=40)
    assert not check_tag(k, b"ephemeris", 8, 3, t, bits=40)
    acc = TagAccumulator(80)
    assert not acc.add(True, 40) and acc.add(True, 40)
    assert not acc.add(False, 40)


def test_root_signature():
    sk, evil = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    c = KeyChain(5, seed=7)
    params = {"period": 12, "delay": 8, "tag_bits": 32}
    sig = sign_root(sk, c.root, params)
    assert verify_root(sk.public_key(), c.root, params, sig)
    assert not verify_root(sk.public_key(), c.root, params, sign_root(evil, c.root, params))
    assert not verify_root(sk.public_key(), c.root, {**params, "delay": 1}, sig)


def test_security_condition():
    d = disclosure_time(10, period=12, delay_intervals=8)  # key 10 public at t=216
    assert d == 216
    assert key_not_yet_disclosed(150, 30, d)
    assert not key_not_yet_disclosed(216.5, 0, d)  # arrived after disclosure
    assert not key_not_yet_disclosed(200, 20, d)  # clock error makes it unsafe
