"""Tests for SigningService: ed25519 signing and verification."""

import re

from loom.services.signing_service import (
    fingerprint,
    generate_keypair,
    sign,
    verify,
)


def _sample_payload() -> dict:
    return {
        "content": "print('hello world')",
        "version": "1.0.0",
        "dependencies_json": "[]",
        "eval_spec_json": "{}",
    }


class TestGenerateKeypair:
    def test_returns_valid_hex_strings(self) -> None:
        private_key_hex, public_key_hex = generate_keypair()
        assert len(private_key_hex) == 128  # 64 bytes = seed + verify key
        assert len(public_key_hex) == 64  # 32 bytes = verify key
        # Validate they are valid hex
        bytes.fromhex(private_key_hex)
        bytes.fromhex(public_key_hex)

    def test_private_key_contains_public_key(self) -> None:
        private_key_hex, public_key_hex = generate_keypair()
        assert private_key_hex[64:] == public_key_hex

    def test_generates_unique_keys(self) -> None:
        k1 = generate_keypair()
        k2 = generate_keypair()
        assert k1[0] != k2[0]
        assert k1[1] != k2[1]


class TestSignAndVerify:
    def test_roundtrip_succeeds(self) -> None:
        private_key_hex, public_key_hex = generate_keypair()
        payload = _sample_payload()
        sig = sign(**payload, private_key_hex=private_key_hex)
        assert verify(**payload, signature_hex=sig, public_key_hex=public_key_hex)

    def test_signature_is_hex(self) -> None:
        private_key_hex, _ = generate_keypair()
        sig = sign(**_sample_payload(), private_key_hex=private_key_hex)
        assert len(sig) == 128  # ed25519 signature = 64 bytes = 128 hex chars
        bytes.fromhex(sig)

    def test_tampered_content_fails(self) -> None:
        private_key_hex, public_key_hex = generate_keypair()
        payload = _sample_payload()
        sig = sign(**payload, private_key_hex=private_key_hex)
        payload["content"] = "print('tampered')"
        assert not verify(**payload, signature_hex=sig, public_key_hex=public_key_hex)

    def test_tampered_version_fails(self) -> None:
        private_key_hex, public_key_hex = generate_keypair()
        payload = _sample_payload()
        sig = sign(**payload, private_key_hex=private_key_hex)
        payload["version"] = "2.0.0"
        assert not verify(**payload, signature_hex=sig, public_key_hex=public_key_hex)

    def test_tampered_dependencies_fails(self) -> None:
        private_key_hex, public_key_hex = generate_keypair()
        payload = _sample_payload()
        sig = sign(**payload, private_key_hex=private_key_hex)
        payload["dependencies_json"] = '[{"slug": "evil"}]'
        assert not verify(**payload, signature_hex=sig, public_key_hex=public_key_hex)

    def test_tampered_eval_spec_fails(self) -> None:
        private_key_hex, public_key_hex = generate_keypair()
        payload = _sample_payload()
        sig = sign(**payload, private_key_hex=private_key_hex)
        payload["eval_spec_json"] = '{"tampered": true}'
        assert not verify(**payload, signature_hex=sig, public_key_hex=public_key_hex)

    def test_wrong_public_key_fails(self) -> None:
        private_key_hex, _ = generate_keypair()
        _, wrong_public_key = generate_keypair()
        payload = _sample_payload()
        sig = sign(**payload, private_key_hex=private_key_hex)
        assert not verify(**payload, signature_hex=sig, public_key_hex=wrong_public_key)

    def test_invalid_signature_hex_fails(self) -> None:
        _, public_key_hex = generate_keypair()
        payload = _sample_payload()
        assert not verify(**payload, signature_hex="not_hex", public_key_hex=public_key_hex)

    def test_invalid_public_key_hex_fails(self) -> None:
        private_key_hex, _ = generate_keypair()
        payload = _sample_payload()
        sig = sign(**payload, private_key_hex=private_key_hex)
        assert not verify(**payload, signature_hex=sig, public_key_hex="not_hex")


class TestFingerprint:
    def test_format(self) -> None:
        _, public_key_hex = generate_keypair()
        fp = fingerprint(public_key_hex)
        assert fp.startswith("sha256:")
        hex_part = fp[len("sha256:") :]
        assert len(hex_part) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", hex_part)

    def test_deterministic(self) -> None:
        _, public_key_hex = generate_keypair()
        assert fingerprint(public_key_hex) == fingerprint(public_key_hex)

    def test_different_keys_different_fingerprints(self) -> None:
        _, pk1 = generate_keypair()
        _, pk2 = generate_keypair()
        assert fingerprint(pk1) != fingerprint(pk2)
