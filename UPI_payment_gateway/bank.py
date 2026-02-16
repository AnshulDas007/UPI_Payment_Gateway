"""
bank.py
=======
Centralized Bank Server for the UPI Payment Gateway.

Features:
  - Multi-bank support: HDFC, ICICI, SBI — 3 branches each (9 IFSC codes)
  - Merchant registration  → 16-digit MID via SHA-256
  - User registration      → 16-digit UID + MMID via SHA-256
  - Transaction processing → PIN / MMID / balance validation
  - Blockchain ledger      → immutable transaction log
  - Socket server          → listens on port 9000 for UPI machine connections
"""

import socket
import threading
import json
import time
import sys
import os

# Add parent directory to path so crypto_utils can be imported when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crypto_utils import generate_id, sha256_hash, Blockchain

# ========================== Bank Database ==========================

# Supported banks and their branches (IFSC codes)
BANKS = {
    "HDFC": ["HDFC001", "HDFC002", "HDFC003"],
    "ICICI": ["ICIC001", "ICIC002", "ICIC003"],
    "SBI":  ["SBIN001", "SBIN002", "SBIN003"],
}

# In-memory stores  (keyed by MID / MMID)
merchants = {}   # { mid: { name, ifsc, password_hash, balance, mid } }
users = {}       # { mmid: { name, mobile, pin_hash, balance, uid, mmid, ifsc } }
blockchain = Blockchain()

# ========================== Registration ==========================

def register_merchant(name: str, password: str, ifsc: str, balance: float) -> dict:
    """
    Register a merchant with the bank.

    MID = SHA-256(name + timestamp + password) truncated to 16 hex digits.
    """
    if ifsc not in sum(BANKS.values(), []):
        return {"status": "failure", "reason": f"Invalid IFSC code: {ifsc}"}

    timestamp = str(time.time())
    mid = generate_id(name + timestamp + password)
    password_hash = sha256_hash(password)

    merchants[mid] = {
        "name": name,
        "ifsc": ifsc,
        "password_hash": password_hash,
        "balance": balance,
        "mid": mid,
    }
    return {"status": "success", "mid": mid, "name": name, "ifsc": ifsc}


def register_user(name: str, mobile: str, pin: str, password: str,
                   ifsc: str, balance: float) -> dict:
    """
    Register a user with the bank.

    UID  = SHA-256(name + mobile + pin + timestamp)  →  16 hex digits
    MMID = SHA-256(UID + mobile)                      →  16 hex digits
    """
    if ifsc not in sum(BANKS.values(), []):
        return {"status": "failure", "reason": f"Invalid IFSC code: {ifsc}"}

    timestamp = str(time.time())
    uid = generate_id(name + mobile + pin + timestamp)
    mmid = generate_id(uid + mobile)
    pin_hash = sha256_hash(pin)
    password_hash = sha256_hash(password)

    users[mmid] = {
        "name": name,
        "mobile": mobile,
        "pin_hash": pin_hash,
        "password_hash": password_hash,
        "balance": balance,
        "uid": uid,
        "mmid": mmid,
        "ifsc": ifsc,
    }
    return {"status": "success", "uid": uid, "mmid": mmid,
            "name": name, "ifsc": ifsc}


# ========================== Sample Data ==========================

def register_sample_data():
    """Pre-register sample merchants and users across different banks."""
    samples_merchants = [
        ("ShopMart",   "merchant123", "HDFC001", 50000),
        ("FreshMart",  "fresh456",    "ICIC001", 30000),
        ("QuickStore", "quick789",    "SBIN001", 20000),
    ]
    samples_users = [
        ("Alice",  "9876543210", "1234", "alice@123",  "HDFC002", 15000),
        ("Bob",    "8765432109", "5678", "bob@456",    "ICIC002", 10000),
        ("Charlie","7654321098", "9012", "charlie@789","SBIN002",  8000),
    ]

    print("\n" + "=" * 60)
    print("  REGISTERING SAMPLE DATA")
    print("=" * 60)

    for args in samples_merchants:
        result = register_merchant(*args)
        print(f"\n  [Merchant] {result['name']}")
        print(f"    MID  : {result['mid']}")
        print(f"    IFSC : {result['ifsc']}")

    for args in samples_users:
        result = register_user(*args)
        print(f"\n  [User] {result['name']}")
        print(f"    UID  : {result['uid']}")
        print(f"    MMID : {result['mmid']}")
        print(f"    IFSC : {result['ifsc']}")

    print("\n" + "=" * 60 + "\n")


# ========================== Transaction Processing ==========================

def process_transaction(merchant_mid: str, user_mmid: str,
                        amount: float, user_pin: str) -> dict:
    """
    Validate and process a UPI transaction.

    Checks:
      1. User exists (MMID lookup)
      2. PIN matches (SHA-256 comparison)
      3. Sufficient balance
      4. Merchant exists

    On success: debit user, credit merchant, add to blockchain.
    """
    # 1. Validate user
    if user_mmid not in users:
        return {"status": "failure", "reason": "User MMID not registered"}

    user = users[user_mmid]

    # 2. Validate PIN
    if sha256_hash(user_pin) != user["pin_hash"]:
        return {"status": "failure", "reason": "Invalid PIN"}

    # 3. Check balance
    if user["balance"] < amount:
        return {"status": "failure",
                "reason": f"Insufficient balance (available: ₹{user['balance']:.2f})"}

    # 4. Validate merchant
    if merchant_mid not in merchants:
        return {"status": "failure", "reason": "Merchant MID not registered"}

    merchant = merchants[merchant_mid]

    # 5. Process fund transfer
    user["balance"] -= amount
    merchant["balance"] += amount

    # 6. Record in blockchain
    block = blockchain.add_transaction(user_mmid, merchant_mid, amount)

    return {
        "status": "success",
        "tx_id": block.tx_id,
        "block_hash": block.block_hash[:16],
        "user_balance": user["balance"],
        "merchant_name": merchant["name"],
        "amount": amount,
    }


# ========================== Socket Server ==========================

def handle_client(conn, addr):
    """Handle an incoming JSON transaction request from the UPI Machine."""
    print(f"\n  [CONN] UPI Machine connected from {addr}")
    try:
        data = conn.recv(4096)
        if not data:
            return

        request = json.loads(data.decode())
        print(f"  [REQ]  {json.dumps(request, indent=2)}")

        merchant_mid = request.get("merchant_id", "")
        user_mmid = request.get("user_mmid", "")
        amount = float(request.get("amount", 0))
        user_pin = request.get("user_pin", "")

        response = process_transaction(merchant_mid, user_mmid, amount, user_pin)
        print(f"  [RESP] {response['status'].upper()} — "
              f"{response.get('reason', response.get('tx_id', ''))}")

        conn.send(json.dumps(response).encode())

    except Exception as e:
        error_resp = {"status": "failure", "reason": str(e)}
        conn.send(json.dumps(error_resp).encode())
        print(f"  [ERR]  {e}")
    finally:
        conn.close()


def bank_server(host: str = "0.0.0.0", port: int = 9000):
    """Start the bank TCP server, listening for UPI Machine connections."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)

    print(f"\n{'=' * 60}")
    print(f"  BANK SERVER — listening on {host}:{port}")
    print(f"{'=' * 60}")
    print("  Waiting for connections from UPI Machine…\n")

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr),
                                 daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n  Bank server shutting down.")
    finally:
        server.close()


# ========================== Interactive CLI ==========================

def interactive_menu():
    """Interactive bank management menu."""
    while True:
        print("\n" + "─" * 50)
        print("  BANK MANAGEMENT MENU")
        print("─" * 50)
        print("  1. Register Merchant")
        print("  2. Register User")
        print("  3. View All Merchants")
        print("  4. View All Users")
        print("  5. View Blockchain Ledger")
        print("  6. Start Bank Server (port 9000)")
        print("  7. Exit")
        print("─" * 50)

        choice = input("  Select option: ").strip()

        if choice == "1":
            print("\n  — Register Merchant —")
            name = input("  Merchant Name : ").strip()
            password = input("  Password      : ").strip()
            print(f"  Available IFSC codes: {sum(BANKS.values(), [])}")
            ifsc = input("  IFSC Code     : ").strip()
            balance = float(input("  Initial Balance: ₹ ").strip())
            result = register_merchant(name, password, ifsc, balance)
            if result["status"] == "success":
                print(f"\n  ✓ Merchant registered! MID: {result['mid']}")
            else:
                print(f"\n  ✗ Failed: {result['reason']}")

        elif choice == "2":
            print("\n  — Register User —")
            name = input("  User Name     : ").strip()
            mobile = input("  Mobile Number : ").strip()
            pin = input("  UPI PIN       : ").strip()
            password = input("  Password      : ").strip()
            print(f"  Available IFSC codes: {sum(BANKS.values(), [])}")
            ifsc = input("  IFSC Code     : ").strip()
            balance = float(input("  Initial Balance: ₹ ").strip())
            result = register_user(name, mobile, pin, password, ifsc, balance)
            if result["status"] == "success":
                print(f"\n  ✓ User registered!")
                print(f"    UID  : {result['uid']}")
                print(f"    MMID : {result['mmid']}")
            else:
                print(f"\n  ✗ Failed: {result['reason']}")

        elif choice == "3":
            print("\n  — Registered Merchants —")
            if not merchants:
                print("  (none)")
            for mid, m in merchants.items():
                print(f"\n  {m['name']}  |  MID: {mid}  |  "
                      f"IFSC: {m['ifsc']}  |  Balance: ₹{m['balance']:.2f}")

        elif choice == "4":
            print("\n  — Registered Users —")
            if not users:
                print("  (none)")
            for mmid, u in users.items():
                print(f"\n  {u['name']}  |  MMID: {mmid}  |  "
                      f"Mobile: {u['mobile']}  |  Balance: ₹{u['balance']:.2f}")

        elif choice == "5":
            blockchain.print_chain()

        elif choice == "6":
            bank_server()

        elif choice == "7":
            print("  Goodbye!")
            break
        else:
            print("  Invalid option. Try again.")


# ========================== Main ==========================

if __name__ == "__main__":
    register_sample_data()
    interactive_menu()
