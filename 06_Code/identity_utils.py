import hashlib
import os
import base64
import secrets
from typing import Dict

def hash_password(password: str, iterations: int = 200_000) -> Dict:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return {
        'algorithm': 'pbkdf2_sha256',
        'iterations': iterations,
        'salt': base64.b64encode(salt).decode('ascii'),
        'hash': base64.b64encode(dk).decode('ascii')
    }

def verify_password(password: str, hashdict: Dict) -> bool:
    if not hashdict or 'algorithm' not in hashdict:
        return False
    if hashdict.get('algorithm') != 'pbkdf2_sha256':
        return False
    iterations = int(hashdict.get('iterations', 200_000))
    salt = base64.b64decode(hashdict['salt'])
    expected = base64.b64decode(hashdict['hash'])
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return secrets.compare_digest(dk, expected)
