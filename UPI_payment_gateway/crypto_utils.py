"""
crypto_utils.py
===============
Shared cryptographic utilities for the Centralized UPI Payment Gateway.

Includes:
  - SHA-256 based ID generation (MID, UID, MMID)
  - SPECK64/128 Lightweight Cipher (encrypt / decrypt)
  - Blockchain ledger classes (Block + Blockchain)
"""

import hashlib
import time
import json

# ========================== SHA-256 Utilities ==========================

def generate_id(input_str: str, length: int = 16) -> str:
    """
    Generate a fixed-length hex ID by SHA-256 hashing the input string
    and truncating to `length` hex digits.
    Used for MID (Merchant ID), UID (User ID), and MMID generation.
    """
    full_hash = hashlib.sha256(input_str.encode()).hexdigest()
    return full_hash[:length]


def sha256_hash(data: str) -> str:
    """Return the full SHA-256 hex digest of the input string."""
    return hashlib.sha256(data.encode()).hexdigest()


# ===================== SPECK64/128 Lightweight Cipher =====================
#
# SPECK is a family of lightweight block ciphers designed by the NSA.
# SPECK64/128 operates on a 64-bit block with a 128-bit key.
# The block is split into two 32-bit words and processed over 27 rounds.
#
# Reference:  "The Simon and Speck Families of Lightweight Block Ciphers"
#             Ray Beaulieu et al., 2013  (NSA / ePrint 2013/404)

SPECK_ROUNDS = 27
SPECK_WORD_SIZE = 32
SPECK_MOD = 1 << SPECK_WORD_SIZE  # 2^32

# Default 128-bit key represented as four 32-bit words
SPECK_KEY = (0x19181110, 0x11100908, 0x03020100, 0x0B0A0908)


def _rotr32(val: int, r: int) -> int:
    """Right-rotate a 32-bit value by r bits."""
    return ((val >> r) | (val << (SPECK_WORD_SIZE - r))) & (SPECK_MOD - 1)


def _rotl32(val: int, r: int) -> int:
    """Left-rotate a 32-bit value by r bits."""
    return ((val << r) | (val >> (SPECK_WORD_SIZE - r))) & (SPECK_MOD - 1)


def _speck_key_schedule(key: tuple) -> list:
    """
    Expand a 128-bit key (4 × 32-bit words) into 27 round keys.
    key = (k0, k1, k2, k3)  where k0 is the rightmost word.
    """
    m = len(key) - 1  # m = 3 for SPECK64/128
    round_keys = [0] * SPECK_ROUNDS
    round_keys[0] = key[0]

    l = list(key[1:])  # l[0..m-1]

    for i in range(SPECK_ROUNDS - 1):
        # l[i+m-1] = (ROR(l[i], 8) + round_keys[i]) XOR i
        l_idx = i % m
        new_l = (_rotr32(l[l_idx], 8) + round_keys[i]) & (SPECK_MOD - 1)
        new_l ^= i
        # round_keys[i+1] = ROL(round_keys[i], 3) XOR new_l
        round_keys[i + 1] = _rotl32(round_keys[i], 3) ^ new_l
        l[l_idx] = new_l

    return round_keys


def speck_encrypt(plaintext_hex: str, key: tuple = SPECK_KEY) -> str:
    """
    Encrypt a 16-hex-digit plaintext (64-bit block) using SPECK64/128.

    Parameters
    ----------
    plaintext_hex : str
        16 hex characters representing the 64-bit plaintext block.
    key : tuple of 4 ints
        128-bit key as four 32-bit words.

    Returns
    -------
    str : 16 hex characters representing the ciphertext.
    """
    plaintext_hex = plaintext_hex.lower().ljust(16, '0')[:16]

    # Split into two 32-bit words (big-endian)
    x = int(plaintext_hex[:8], 16)
    y = int(plaintext_hex[8:], 16)

    rk = _speck_key_schedule(key)

    for i in range(SPECK_ROUNDS):
        x = (_rotr32(x, 8) + y) & (SPECK_MOD - 1)
        x ^= rk[i]
        y = _rotl32(y, 3) ^ x

    return f"{x:08x}{y:08x}"


def speck_decrypt(ciphertext_hex: str, key: tuple = SPECK_KEY) -> str:
    """
    Decrypt a 16-hex-digit ciphertext (64-bit block) using SPECK64/128.

    Parameters
    ----------
    ciphertext_hex : str
        16 hex characters representing the 64-bit ciphertext block.
    key : tuple of 4 ints
        128-bit key as four 32-bit words.

    Returns
    -------
    str : 16 hex characters representing the recovered plaintext.
    """
    ciphertext_hex = ciphertext_hex.lower().ljust(16, '0')[:16]

    x = int(ciphertext_hex[:8], 16)
    y = int(ciphertext_hex[8:], 16)

    rk = _speck_key_schedule(key)

    for i in range(SPECK_ROUNDS - 1, -1, -1):
        y = _rotr32(y ^ x, 3)
        x = _rotl32(((x ^ rk[i]) - y) & (SPECK_MOD - 1), 8)

    return f"{x:08x}{y:08x}"


# ======================== Blockchain Ledger ========================

class Block:
    """
    A single block in the centralized blockchain ledger.

    Attributes
    ----------
    index         : int   – position in the chain
    tx_id         : str   – transaction ID (SHA-256 truncated to 16 hex)
    previous_hash : str   – hash of the previous block
    timestamp     : float – Unix epoch timestamp
    details       : dict  – transaction payload (user_mmid, merchant_mid, amount, …)
    block_hash    : str   – SHA-256 hash of *this* block's content
    """

    def __init__(self, index: int, tx_id: str, previous_hash: str,
                 timestamp: float, details: dict):
        self.index = index
        self.tx_id = tx_id
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.details = details
        self.block_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute the SHA-256 hash of the block contents."""
        block_string = json.dumps({
            "index": self.index,
            "tx_id": self.tx_id,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "details": self.details
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "tx_id": self.tx_id,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "details": self.details,
            "block_hash": self.block_hash
        }

    def __repr__(self):
        return (f"Block(idx={self.index}, tx_id={self.tx_id[:12]}…, "
                f"hash={self.block_hash[:12]}…)")


class Blockchain:
    """
    A simple centralized blockchain ledger.

    The genesis block is created automatically.  Each subsequent block
    references the hash of the preceding block, ensuring immutability.
    """

    def __init__(self):
        self.chain: list[Block] = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = Block(
            index=0,
            tx_id="0" * 16,
            previous_hash="0" * 64,
            timestamp=time.time(),
            details={"info": "Genesis Block"}
        )
        self.chain.append(genesis)

    def add_transaction(self, user_mmid: str, merchant_mid: str,
                        amount: float) -> Block:
        """
        Create a new transaction block and append it to the chain.

        Returns the newly created Block.
        """
        timestamp = time.time()
        tx_data = f"{user_mmid}{merchant_mid}{timestamp}{amount}"
        tx_id = generate_id(tx_data)  # 16 hex digits from SHA-256
        previous_hash = self.chain[-1].block_hash

        block = Block(
            index=len(self.chain),
            tx_id=tx_id,
            previous_hash=previous_hash,
            timestamp=timestamp,
            details={
                "user_mmid": user_mmid,
                "merchant_mid": merchant_mid,
                "amount": amount
            }
        )
        self.chain.append(block)
        return block

    def is_valid(self) -> bool:
        """Verify the integrity of the entire chain."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.block_hash != current._compute_hash():
                return False
            if current.previous_hash != previous.block_hash:
                return False
        return True

    def print_chain(self):
        """Pretty-print the blockchain."""
        print("\n" + "=" * 70)
        print("  BLOCKCHAIN LEDGER")
        print("=" * 70)
        for block in self.chain:
            print(f"\n  Block #{block.index}")
            print(f"  ├─ Tx ID         : {block.tx_id}")
            print(f"  ├─ Prev Hash     : {block.previous_hash[:32]}…")
            print(f"  ├─ Block Hash    : {block.block_hash[:32]}…")
            print(f"  ├─ Timestamp     : {time.ctime(block.timestamp)}")
            print(f"  └─ Details       : {block.details}")
        print("\n" + "=" * 70)
        print(f"  Chain valid: {self.is_valid()}")
        print("=" * 70 + "\n")
