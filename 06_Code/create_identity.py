#!/usr/bin/env python3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import argparse
import getpass

from identity_utils import hash_password


def create_identity(name: str, founder: str, password: str, out_path: Path) -> None:
    identity = {
        'id': str(uuid.uuid4()),
        'name': name,
        'founder': founder,
        'constitution_version': '0.1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'password_hash': hash_password(password)
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(identity, f, indent=2, ensure_ascii=False)
    print(f'Wrote identity to {out_path}')


def main():
    p = argparse.ArgumentParser(description='Create or update .ameer/identity.json with a salted password hash')
    p.add_argument('--name', default='Ameer', help='Identity name')
    p.add_argument('--founder', default='Naseem', help='Founder name')
    p.add_argument('--output', default='.ameer/identity.json', help='Output identity path')
    p.add_argument('--password', help='Password (if omitted, prompts securely)')
    args = p.parse_args()
    if args.password:
        pwd = args.password
    else:
        pwd = getpass.getpass('Enter a strong password for this identity: ')
        pwd2 = getpass.getpass('Confirm password: ')
        if pwd != pwd2:
            print('Passwords do not match')
            raise SystemExit(2)
    out = Path(args.output)
    create_identity(args.name, args.founder, pwd, out)


if __name__ == '__main__':
    main()
