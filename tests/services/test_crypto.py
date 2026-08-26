import base64

import pytest

from app.services import crypto

_KEY = b'0' * 32
_IV = b'\x00' * 16


@pytest.mark.parametrize('plaintext', ['', 'a' * 15, 'a' * 16, 'a' * 17, 'texto en español ñ'])
def test_encrypt_decrypt_round_trip(plaintext):
    ciphertext = crypto.encrypt(plaintext, _KEY, _IV)
    assert crypto.decrypt(ciphertext, _KEY, _IV) == plaintext


def test_decrypt_rejects_tampered_ciphertext():
    ciphertext = crypto.encrypt('hello world', _KEY, _IV)
    # Flip the last byte of the final ciphertext block (staying block-aligned,
    # so this exercises the padding check itself, not a block-size error).
    raw = bytearray(base64.b64decode(ciphertext))
    raw[-1] ^= 0xFF
    tampered = base64.b64encode(bytes(raw)).decode()

    with pytest.raises(ValueError, match='Invalid padding'):
        crypto.decrypt(tampered, _KEY, _IV)


def test_sha256hash_is_deterministic():
    assert crypto.sha256hash('abc') == crypto.sha256hash('abc')


def test_sha256hash_differs_for_different_input():
    assert crypto.sha256hash('abc') != crypto.sha256hash('abd')


def test_verify_hmac_accepts_valid_signature():
    signature = crypto.sha256hmac('payload', 'secret')
    assert crypto.verify_hmac('payload', signature, 'secret') is True


def test_verify_hmac_rejects_tampered_text():
    signature = crypto.sha256hmac('payload', 'secret')
    assert crypto.verify_hmac('tampered', signature, 'secret') is False


def test_verify_hmac_rejects_tampered_signature():
    signature = crypto.sha256hmac('payload', 'secret')
    assert crypto.verify_hmac('payload', signature[:-1] + ('0' if signature[-1] != '0' else '1'), 'secret') is False
