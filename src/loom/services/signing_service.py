"""SigningService: ed25519 cryptographic signing for skill provenance."""

import hashlib

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey


def _canonical_hash(
    *, content: str, version: str, dependencies_json: str, eval_spec_json: str
) -> bytes:
    """Build the canonical SHA-256 hash of the signing payload."""
    message = f"{content}\n{version}\n{dependencies_json}\n{eval_spec_json}"
    return hashlib.sha256(message.encode("utf-8")).digest()


def generate_keypair() -> tuple[str, str]:
    """Generate an ed25519 keypair.

    Returns:
        (private_key_hex, public_key_hex) where:
        - private_key_hex = seed (32 bytes) + verify_key (32 bytes) = 128 hex chars
        - public_key_hex = verify_key (32 bytes) = 64 hex chars
    """
    signing_key = SigningKey.generate()
    seed_hex = bytes(signing_key).hex()
    verify_hex = bytes(signing_key.verify_key).hex()
    private_key_hex = seed_hex + verify_hex
    return private_key_hex, verify_hex


def sign(
    *,
    content: str,
    version: str,
    dependencies_json: str,
    eval_spec_json: str,
    private_key_hex: str,
) -> str:
    """Sign the canonical message hash with ed25519.

    Returns the signature as a hex string.
    """
    seed_bytes = bytes.fromhex(private_key_hex[:64])  # first 32 bytes
    signing_key = SigningKey(seed_bytes)
    digest = _canonical_hash(
        content=content,
        version=version,
        dependencies_json=dependencies_json,
        eval_spec_json=eval_spec_json,
    )
    signed = signing_key.sign(digest)
    return signed.signature.hex()


def verify(
    *,
    content: str,
    version: str,
    dependencies_json: str,
    eval_spec_json: str,
    signature_hex: str,
    public_key_hex: str,
) -> bool:
    """Verify an ed25519 signature against the canonical message hash.

    Returns False on any signature or value error.
    """
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key_hex))
        digest = _canonical_hash(
            content=content,
            version=version,
            dependencies_json=dependencies_json,
            eval_spec_json=eval_spec_json,
        )
        verify_key.verify(digest, bytes.fromhex(signature_hex))
        return True
    except (BadSignatureError, ValueError):
        return False


def fingerprint(public_key_hex: str) -> str:
    """Compute the SHA-256 fingerprint of a public key.

    Returns "sha256:" + hex digest (64 chars).
    """
    raw_bytes = bytes.fromhex(public_key_hex)
    return "sha256:" + hashlib.sha256(raw_bytes).hexdigest()
