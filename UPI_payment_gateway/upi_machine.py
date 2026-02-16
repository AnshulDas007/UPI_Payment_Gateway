"""
upi_machine.py
==============
UPI Machine (Intermediary) for the Centralized UPI Payment Gateway.

Features:
  - Encrypts Merchant ID using SPECK64/128 (LWC) to produce VMID
  - Generates QR code image containing the encrypted VMID
  - Listens on port 8000 for User connections
  - Forwards transaction requests to the Bank server on port 9000
  - Relays bank responses back to the user
"""

import socket
import threading
import json
import sys
import os

# Add current directory to path for direct execution
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crypto_utils import speck_encrypt, speck_decrypt, SPECK_KEY

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("  [WARN] qrcode module not found. QR images will not be generated.")
    print("         Install with: pip install qrcode Pillow\n")


# ========================== LWC Encryption (SPECK) ==========================

def lwc_encrypt_mid(merchant_mid: str) -> str:
    """
    Encrypt a 16-hex-digit Merchant ID using SPECK64/128 to produce
    a Virtual Merchant ID (VMID) for embedding in the QR code.
    """
    return speck_encrypt(merchant_mid, SPECK_KEY)


def lwc_decrypt_vmid(vmid: str) -> str:
    """
    Decrypt a VMID back to the original Merchant ID using SPECK64/128.
    """
    return speck_decrypt(vmid, SPECK_KEY)


# ========================== QR Code Generation ==========================

def generate_qr_code(encrypted_mid: str, filename: str = "merchant_qr.png"):
    """
    Generate a QR code image that encodes the encrypted Merchant ID (VMID).
    Also writes the data to qr.txt as a backup.
    """
    # Save QR data to text file
    qr_dir = os.path.dirname(os.path.abspath(__file__))
    txt_path = os.path.join(qr_dir, "qr.txt")
    img_path = os.path.join(qr_dir, filename)

    with open(txt_path, "w") as f:
        f.write(f"QR Code Data (Encrypted Merchant VMID): {encrypted_mid}\n")

    # Generate QR code image
    if QR_AVAILABLE:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(encrypted_mid)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(img_path)
        print(f"  ✓ QR code image saved to: {img_path}")
    else:
        print(f"  ✓ QR data saved to: {txt_path}")

    return encrypted_mid


# ========================== Bank Communication ==========================

def forward_to_bank(request: dict, bank_host: str = "127.0.0.1",
                    bank_port: int = 9000) -> dict:
    """
    Forward a transaction request to the Bank server and return the response.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((bank_host, bank_port))
        s.send(json.dumps(request).encode())
        data = s.recv(4096)
        s.close()
        return json.loads(data.decode())
    except Exception as e:
        return {"status": "failure", "reason": f"Bank connection error: {e}"}


# ========================== User Connection Handler ==========================

def handle_user(conn, addr, merchant_mid: str, bank_host: str):
    """
    Handle an incoming connection from a User device.

    1. Receive user's transaction data (MMID, amount, PIN, scanned VMID)
    2. Decrypt VMID to recover original Merchant ID
    3. Forward complete request to Bank
    4. Relay bank response back to user
    """
    print(f"\n  [CONN] User connected from {addr}")
    try:
        data = conn.recv(4096)
        if not data:
            return

        request = json.loads(data.decode())
        print(f"  [USER] Received: {json.dumps(request, indent=2)}")

        user_mmid = request.get("mmid", "")
        amount = request.get("amount", 0)
        user_pin = request.get("pin", "")
        scanned_vmid = request.get("scanned_vmid", "")

        # Decrypt the scanned VMID to recover the original Merchant ID
        if scanned_vmid:
            decrypted_mid = lwc_decrypt_vmid(scanned_vmid)
            print(f"  [DEC]  VMID {scanned_vmid} → MID {decrypted_mid}")
        else:
            decrypted_mid = merchant_mid
            print(f"  [INFO] No VMID provided, using registered MID: {merchant_mid}")

        # Build the transaction request for the Bank
        tx_request = {
            "merchant_id": decrypted_mid,
            "user_mmid": user_mmid,
            "amount": amount,
            "user_pin": user_pin,
        }
        print(f"  [FWD]  Forwarding to Bank…")

        response = forward_to_bank(tx_request, bank_host=bank_host)
        status = response.get("status", "unknown").upper()
        detail = response.get("tx_id", response.get("reason", ""))
        print(f"  [BANK] {status} — {detail}")

        conn.send(json.dumps(response).encode())

    except Exception as e:
        error_resp = {"status": "failure", "reason": str(e)}
        conn.send(json.dumps(error_resp).encode())
        print(f"  [ERR]  {e}")
    finally:
        conn.close()


# ========================== UPI Machine Server ==========================

def upi_server(merchant_mid: str, bank_host: str = "127.0.0.1",
               host: str = "0.0.0.0", port: int = 8000):
    """
    Start the UPI Machine TCP server.

    Listens on `port` for User connections and processes transactions.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)

    print(f"\n{'=' * 60}")
    print(f"  UPI MACHINE SERVER — listening on {host}:{port}")
    print(f"{'=' * 60}")
    print(f"  Merchant MID : {merchant_mid}")
    print(f"  Bank address : {bank_host}:9000")
    print("  Waiting for user connections…\n")

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(
                target=handle_user,
                args=(conn, addr, merchant_mid, bank_host),
                daemon=True
            )
            t.start()
    except KeyboardInterrupt:
        print("\n  UPI Machine shutting down.")
    finally:
        server.close()


# ========================== Main ==========================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  UPI MACHINE — Lightweight Cryptography Gateway")
    print("=" * 60)

    # Step 1: Get Merchant ID
    merchant_mid = input("\n  Enter Merchant ID (16 hex digits): ").strip()
    if len(merchant_mid) != 16:
        print("  [WARN] MID should be 16 hex digits. Padding/truncating…")
        merchant_mid = merchant_mid.ljust(16, '0')[:16]

    # Step 2: Encrypt MID using SPECK (LWC) to generate VMID
    vmid = lwc_encrypt_mid(merchant_mid)
    print(f"\n  Original MID   : {merchant_mid}")
    print(f"  Encrypted VMID : {vmid}  (SPECK64/128)")

    # Step 3: Generate QR code containing the VMID
    generate_qr_code(vmid)

    # Step 4: Verify decryption round-trip
    decrypted = lwc_decrypt_vmid(vmid)
    print(f"  Decrypted MID  : {decrypted}  (verification)")
    if decrypted == merchant_mid:
        print("  ✓ SPECK round-trip verification PASSED\n")
    else:
        print("  ✗ SPECK round-trip verification FAILED\n")

    # Step 5: Configure Bank server address
    bank_host = input("  Bank server IP [127.0.0.1]: ").strip() or "127.0.0.1"

    # Step 6: Start UPI Machine server
    upi_server(merchant_mid, bank_host=bank_host)
