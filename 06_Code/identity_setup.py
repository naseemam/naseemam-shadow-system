#!/usr/bin/env python3
"""Create a canonical .ameer/identity.json, a sample memory note, and a one-time pairing token.

Usage:
    python 06_Code/identity_setup.py --founder "Naseem" --name "Ameer" --pairing-ttl 1440

The script prints a one-time pairing token (save it). The token's SHA256 is stored in
.ameer/pairing.json and can be used to verify a device during pairing.
"""
import os
import json
import uuid
import argparse
from datetime import datetime, timedelta, timezone
import secrets
import hashlib


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs(base):
    ameer = os.path.join(base, ".ameer")
    memory = os.path.join(ameer, "memory")
    os.makedirs(memory, exist_ok=True)
    return ameer, memory


def write_identity(path, name, founder):
    identity = {
        "id": str(uuid.uuid4()),
        "name": name,
        "founder": founder,
        "constitution_version": "0.1",
        "created_at": iso_now(),
        "version": 1
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(identity, f, indent=2, ensure_ascii=False)
    return identity


def write_sample_memory(memory_dir):
    sample_path = os.path.join(memory_dir, "0001_welcome.md")
    content = (
        "# Welcome to Ameer (sample memory)\n\n"
        "هذا ملف ذاكرة تجريبي؛ يمكنك حذفه أو استبداله.\n\n"
        "- created_at: " + iso_now() + "\n"
        "- note: This is an example memory item for Ameer."
    )
    with open(sample_path, "w", encoding="utf-8") as f:
        f.write(content)
    return sample_path


def create_pairing(ameer_dir, ttl_minutes=1440):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    pairing = {
        "pairing_id": str(uuid.uuid4()),
        "token_hash": token_hash,
        "created_at": iso_now(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat(),
        "used": False
    }
    pairing_path = os.path.join(ameer_dir, "pairing.json")
    with open(pairing_path, "w", encoding="utf-8") as f:
        json.dump(pairing, f, indent=2, ensure_ascii=False)
    return token, pairing_path


def main():
    p = argparse.ArgumentParser(description="Initialize Ameer identity, memory, and pairing token")
    p.add_argument("--founder", default="Naseem", help="Founder/owner name")
    p.add_argument("--name", default="Ameer", help="Agent name")
    p.add_argument("--repo", default=".", help="Repository root (default: current dir)")
    p.add_argument("--pairing-ttl", type=int, default=1440, help="Pairing token TTL in minutes (default 1440 = 24h)")
    args = p.parse_args()

    base = os.path.abspath(args.repo)
    ameer_dir, memory_dir = ensure_dirs(base)

    identity_path = os.path.join(ameer_dir, "identity.json")
    if os.path.exists(identity_path):
        print("Identity already exists at:", identity_path)
        print("If you want to recreate it, remove the file first or run with --force in a future version.")
        return

    identity = write_identity(identity_path, args.name, args.founder)
    sample = write_sample_memory(memory_dir)
    token, pairing_path = create_pairing(ameer_dir, ttl_minutes=args.pairing_ttl)

    print("Created identity:", identity_path)
    print("Sample memory file:", sample)
    print("Pairing metadata saved:", pairing_path)
    print()
    print("ONE-TIME PAIRING TOKEN (copy now — shown only once):")
    print(token)


if __name__ == "__main__":
    main()
