"""
user.py
=======
User Client for the Centralized UPI Payment Gateway.

Features:
  - Simulates QR code scanning (user enters encrypted VMID)
  - Collects MMID, transaction amount, and PIN
  - Connects to UPI Machine (port 8000) and sends transaction data
  - Displays transaction response (success/failure)
"""

import socket
import json
import sys


def user_transaction(mmid: str, amount: float, pin: str,
                     scanned_vmid: str,
                     upi_host: str = "127.0.0.1", upi_port: int = 8000) -> dict:
    """
    Connect to the UPI Machine, send user transaction details,
    and return the bank's response.

    Parameters
    ----------
    mmid         : User's Mobile Money Identifier (16 hex digits)
    amount       : Transaction amount in INR
    pin          : User's UPI PIN
    scanned_vmid : Encrypted Merchant VMID from QR code scan
    upi_host     : UPI Machine IP address
    upi_port     : UPI Machine port (default 8000)
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((upi_host, upi_port))

        request = {
            "mmid": mmid,
            "amount": amount,
            "pin": pin,
            "scanned_vmid": scanned_vmid,
        }
        s.send(json.dumps(request).encode())

        data = s.recv(4096)
        response = json.loads(data.decode())
        s.close()
        return response

    except Exception as e:
        return {"status": "failure", "reason": str(e)}


# ========================== Main ==========================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  UPI USER — Payment Client")
    print("=" * 60)

    # Step 1: Simulate QR code scanning
    print("\n  [Step 1] Scan the merchant QR code.")
    scanned_vmid = input("  Enter scanned VMID (from QR code): ").strip()

    # Step 2: Enter user credentials
    print("\n  [Step 2] Enter your payment details.")
    mmid = input("  Your MMID (16 hex digits): ").strip()
    amount = input("  Transaction Amount (₹)   : ").strip()
    pin = input("  Your UPI PIN             : ").strip()

    try:
        amount = float(amount)
    except ValueError:
        print("  ✗ Invalid amount. Please enter a number.")
        sys.exit(1)

    # Step 3: Configure UPI Machine address
    upi_host = input("\n  UPI Machine IP [127.0.0.1]: ").strip() or "127.0.0.1"

    # Step 4: Send transaction
    print(f"\n  Connecting to UPI Machine ({upi_host}:8000)…")
    response = user_transaction(mmid, amount, pin, scanned_vmid,
                                upi_host=upi_host)

    # Step 5: Display result
    print("\n" + "─" * 50)
    if response.get("status") == "success":
        print("  ✓ TRANSACTION SUCCESSFUL")
        print(f"    Transaction ID  : {response.get('tx_id', 'N/A')}")
        print(f"    Block Hash      : {response.get('block_hash', 'N/A')}")
        print(f"    Amount Paid     : ₹{response.get('amount', 0):.2f}")
        print(f"    Merchant        : {response.get('merchant_name', 'N/A')}")
        print(f"    Remaining Bal   : ₹{response.get('user_balance', 0):.2f}")
    else:
        print("  ✗ TRANSACTION FAILED")
        print(f"    Reason: {response.get('reason', 'Unknown error')}")
    print("─" * 50 + "\n")
