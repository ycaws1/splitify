#!/usr/bin/env python3
"""
Generate VAPID public/private keys for Web Push Notifications.

Usage:
    python scripts/generate_vapid_keys.py
    python scripts/generate_vapid_keys.py --email you@example.com

Requires: cryptography (already installed as a dependency of pywebpush)
"""

import argparse
import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)


def main():
    parser = argparse.ArgumentParser(description="Generate VAPID keys for Web Push")
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="Email address for VAPID claims (e.g. you@example.com)",
    )
    args = parser.parse_args()

    # Generate a new ECDSA key pair on the P-256 curve
    private_key = ec.generate_private_key(ec.SECP256R1())

    # Private key: raw 32-byte scalar, base64url-encoded (no padding)
    private_numbers = private_key.private_numbers()
    priv_bytes = private_numbers.private_value.to_bytes(32, byteorder="big")
    private_key_b64 = base64.urlsafe_b64encode(priv_bytes).rstrip(b"=").decode("ascii")

    # Public key: 65-byte uncompressed point, base64url-encoded (no padding)
    pub_key = private_key.public_key()
    pub_bytes = pub_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    public_key_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode("ascii")

    # Determine email
    email = args.email
    if not email:
        email = input("Enter your email for VAPID claims (e.g. you@example.com): ").strip()

    # Ensure mailto: prefix
    if not email.startswith("mailto:"):
        email = f"mailto:{email}"

    print()
    print("=" * 60)
    print("  VAPID Keys Generated Successfully!")
    print("=" * 60)
    print()
    print("── Backend .env ─────────────────────────────────────")
    print(f"VAPID_PRIVATE_KEY={private_key_b64}")
    print(f"VAPID_PUBLIC_KEY={public_key_b64}")
    print(f"VAPID_CLAIMS_EMAIL={email}")
    print()
    print("── Frontend .env.local ──────────────────────────────")
    print(f"NEXT_PUBLIC_VAPID_PUBLIC_KEY={public_key_b64}")
    print()
    print("=" * 60)
    print("  Copy these values into your .env files above.")
    print("  Then restart both the backend and frontend servers.")
    print("=" * 60)


if __name__ == "__main__":
    main()
