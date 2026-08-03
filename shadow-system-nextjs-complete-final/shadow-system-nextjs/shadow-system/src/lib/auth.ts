/**
 * Authentication utilities for the Ameer system.
 * Uses Web Crypto API (PBKDF2-SHA256) — works in Cloudflare Workers and Node.js.
 */

const PBKDF2_ITERATIONS = 100_000;
const HASH_BYTES = 32; // 256 bits

/**
 * Hash a password using PBKDF2-SHA256.
 * Returns the format: "v1:<base64-salt>:<base64-hash>"
 */
export async function hashPassword(password: string): Promise<string> {
  const enc = new TextEncoder();
  const salt = crypto.getRandomValues(new Uint8Array(16));

  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    enc.encode(password),
    'PBKDF2',
    false,
    ['deriveBits']
  );

  const derivedBits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt, iterations: PBKDF2_ITERATIONS, hash: 'SHA-256' },
    keyMaterial,
    HASH_BYTES * 8
  );

  const saltB64 = btoa(String.fromCharCode(...salt));
  const hashB64 = btoa(String.fromCharCode(...new Uint8Array(derivedBits)));
  return `v1:${saltB64}:${hashB64}`;
}

/**
 * Verify a plaintext password against a stored hash string.
 */
export async function verifyPassword(password: string, stored: string): Promise<boolean> {
  try {
    const parts = stored.split(':');
    if (parts.length !== 3 || parts[0] !== 'v1') return false;

    const [, saltB64, expectedHashB64] = parts;
    const salt = new Uint8Array(
      atob(saltB64).split('').map((c) => c.charCodeAt(0))
    );
    const expectedHash = atob(expectedHashB64);

    const enc = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      enc.encode(password),
      'PBKDF2',
      false,
      ['deriveBits']
    );

    const derivedBits = await crypto.subtle.deriveBits(
      { name: 'PBKDF2', salt, iterations: PBKDF2_ITERATIONS, hash: 'SHA-256' },
      keyMaterial,
      HASH_BYTES * 8
    );

    const actualHash = String.fromCharCode(...new Uint8Array(derivedBits));

    // Constant-time comparison to prevent timing attacks
    if (actualHash.length !== expectedHash.length) return false;
    let diff = 0;
    for (let i = 0; i < actualHash.length; i++) {
      diff |= actualHash.charCodeAt(i) ^ expectedHash.charCodeAt(i);
    }
    return diff === 0;
  } catch {
    return false;
  }
}

/**
 * Returns the JWT secret from the environment.
 * Throws if the variable is missing so callers fail fast.
 */
export function getJwtSecret(): string {
  const secret = process.env.JWT_SECRET;
  if (!secret) throw new Error('JWT_SECRET environment variable is not set');
  return secret;
}
