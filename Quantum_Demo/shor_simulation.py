#!/usr/bin/env python3
"""
shor_simulation.py
==================
Quantum Cryptography Vulnerability Demonstration.

Simulates Shor's Algorithm (via classical trial division) to demonstrate
the vulnerability of RSA-encrypted UPI credentials (PIN and MMID)
in a post-quantum computing scenario.

This module is part of the Centralized UPI Payment Gateway project and
highlights why quantum-resistant cryptography is needed for future
payment security.
"""

import math
import sys


# ========================== RSA Utilities ==========================

def factorize(n: int) -> tuple:
    """
    Classical factorization via trial division.

    In a real quantum computer, Shor's Algorithm would factor n in
    polynomial time O((log n)^3), making RSA fundamentally insecure.
    Here we simulate this with trial division for educational purposes.
    """
    if n <= 1:
        return n, 1
    if n % 2 == 0:
        return 2, n // 2
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return i, n // i
    return n, 1  # n is prime


def extended_gcd(a: int, b: int) -> tuple:
    """Extended Euclidean Algorithm: returns (gcd, x, y) where a*x + b*y = gcd."""
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    return gcd, y1 - (b // a) * x1, x1


def mod_inverse(a: int, m: int) -> int:
    """Compute modular inverse of a mod m using Extended Euclidean Algorithm."""
    gcd, x, _ = extended_gcd(a % m, m)
    if gcd != 1:
        raise ValueError(f"Modular inverse does not exist for a={a}, m={m}")
    return x % m


def rsa_keygen(p: int, q: int, e: int = 7) -> dict:
    """
    Generate RSA key pair from two primes p and q.

    Returns dict with: p, q, n, phi, e (public exponent), d (private exponent)
    """
    n = p * q
    phi = (p - 1) * (q - 1)
    d = mod_inverse(e, phi)
    return {"p": p, "q": q, "n": n, "phi": phi, "e": e, "d": d}


def rsa_encrypt(message: int, e: int, n: int) -> int:
    """RSA encryption: ciphertext = message^e mod n"""
    return pow(message, e, n)


def rsa_decrypt(ciphertext: int, d: int, n: int) -> int:
    """RSA decryption: message = ciphertext^d mod n"""
    return pow(ciphertext, d, n)


# ========================== Shor's Algorithm Simulation ==========================

def simulate_shors_attack():
    """
    Full demonstration of Shor's Algorithm vulnerability on UPI credentials.

    Scenario:
      1. A bank stores a user's PIN and MMID encrypted with RSA
      2. A quantum attacker uses Shor's Algorithm to factor the RSA modulus
      3. The attacker recovers the private key and decrypts the credentials
      4. The demonstration proves RSA is vulnerable to quantum attacks
    """
    print("\n" + "=" * 70)
    print("  QUANTUM CRYPTOGRAPHY VULNERABILITY DEMONSTRATION")
    print("  Shor's Algorithm Simulation — RSA Attack on UPI Credentials")
    print("=" * 70)

    # ─── Step 1: RSA Key Generation ─────────────────────────
    print("\n" + "─" * 60)
    print("  STEP 1: RSA Key Generation (Bank's Security)")
    print("─" * 60)

    p, q = 61, 53  # Two prime numbers (small for demonstration)
    keys = rsa_keygen(p, q, e=17)

    print(f"  Prime p          = {keys['p']}")
    print(f"  Prime q          = {keys['q']}")
    print(f"  Modulus n = p×q  = {keys['n']}")
    print(f"  Euler's φ(n)     = {keys['phi']}")
    print(f"  Public key (e)   = {keys['e']}")
    print(f"  Private key (d)  = {keys['d']}")

    # ─── Step 2: Encrypting UPI Credentials ──────────────────
    print("\n" + "─" * 60)
    print("  STEP 2: Encrypting UPI Credentials")
    print("─" * 60)

    pin = 1234          # User's UPI PIN
    mmid_numeric = 42   # Simplified numeric MMID (for demo)

    pin_encrypted = rsa_encrypt(pin, keys['e'], keys['n'])
    mmid_encrypted = rsa_encrypt(mmid_numeric, keys['e'], keys['n'])

    print(f"  Original PIN     = {pin}")
    print(f"  Encrypted PIN    = {pin_encrypted}")
    print(f"  Original MMID    = {mmid_numeric}")
    print(f"  Encrypted MMID   = {mmid_encrypted}")

    # ─── Step 3: Normal RSA Decryption (Bank) ────────────────
    print("\n" + "─" * 60)
    print("  STEP 3: Normal Decryption (Bank with private key)")
    print("─" * 60)

    pin_decrypted = rsa_decrypt(pin_encrypted, keys['d'], keys['n'])
    mmid_decrypted = rsa_decrypt(mmid_encrypted, keys['d'], keys['n'])

    print(f"  Decrypted PIN    = {pin_decrypted}  {'✓' if pin_decrypted == pin else '✗'}")
    print(f"  Decrypted MMID   = {mmid_decrypted}  {'✓' if mmid_decrypted == mmid_numeric else '✗'}")

    # ─── Step 4: Quantum Attack (Shor's Algorithm) ───────────
    print("\n" + "─" * 60)
    print("  STEP 4: QUANTUM ATTACK — Shor's Algorithm")
    print("─" * 60)

    print(f"\n  Attacker only knows:")
    print(f"    Public key (e)    = {keys['e']}")
    print(f"    Modulus (n)       = {keys['n']}")
    print(f"    Encrypted PIN     = {pin_encrypted}")
    print(f"    Encrypted MMID    = {mmid_encrypted}")

    print(f"\n  Running Shor's Algorithm to factor n = {keys['n']}…")

    # Simulate Shor's factorization
    factor1, factor2 = factorize(keys['n'])
    print(f"  ✓ Factors found: p = {factor1}, q = {factor2}")

    # Reconstruct the private key
    recovered_phi = (factor1 - 1) * (factor2 - 1)
    recovered_d = mod_inverse(keys['e'], recovered_phi)
    print(f"  ✓ Recovered φ(n)   = {recovered_phi}")
    print(f"  ✓ Recovered d      = {recovered_d}")

    # ─── Step 5: Decrypting with Recovered Key ───────────────
    print("\n" + "─" * 60)
    print("  STEP 5: Decrypting Credentials with Recovered Key")
    print("─" * 60)

    recovered_pin = rsa_decrypt(pin_encrypted, recovered_d, keys['n'])
    recovered_mmid = rsa_decrypt(mmid_encrypted, recovered_d, keys['n'])

    print(f"  Recovered PIN    = {recovered_pin}")
    print(f"  Recovered MMID   = {recovered_mmid}")

    pin_match = recovered_pin == pin
    mmid_match = recovered_mmid == mmid_numeric

    # ─── Step 6: Verdict ─────────────────────────────────────
    print("\n" + "=" * 70)
    if pin_match and mmid_match:
        print("  ⚠  VULNERABILITY CONFIRMED")
        print("  Shor's Algorithm successfully broke RSA encryption and")
        print("  recovered both the UPI PIN and MMID from ciphertext alone.")
        print()
        print("  IMPLICATIONS FOR UPI SECURITY:")
        print("  • Classical RSA is NOT quantum-safe")
        print("  • User PINs and MMIDs can be compromised by quantum computers")
        print("  • Post-quantum cryptographic algorithms (e.g., lattice-based,")
        print("    code-based) should be adopted for future UPI systems")
    else:
        print("  Simulation encountered an error — results do not match.")
    print("=" * 70 + "\n")


# ========================== Main ==========================

if __name__ == "__main__":
    simulate_shors_attack()
