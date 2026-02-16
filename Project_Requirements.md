# Project Requirements — Centralized UPI Payment Gateway

> **Domain:** Cryptography & Network Security

---

## 1. Project Overview

Design and implement a **Centralized UPI Payment Gateway** that simulates real-world digital transactions secured by:
- **Blockchain** — immutable transaction ledger
- **SHA-256** — secure ID generation and hashing
- **Lightweight Cryptography (SPECK)** — fast encryption for resource-constrained environments
- **Quantum Cryptography (Shor's Algorithm)** — vulnerability demonstration

The system operates across **three physical devices** (simulated via separate processes):
1. **Bank Laptop** — Central server managing accounts and the blockchain
2. **UPI Machine** — Intermediary gateway for encryption and payment relay
3. **User Laptop** — Client device for initiating payments

---

## 2. Functional Requirements

### 2.1 Bank Registration

| Requirement | Description |
|---|---|
| **FR-01** | System supports 3 banks: HDFC, ICICI, SBI |
| **FR-02** | Each bank has 3 branches with unique IFSC codes |
| **FR-03** | Merchants and users open accounts at any branch |

### 2.2 Merchant Registration

| Requirement | Description |
|---|---|
| **FR-04** | Merchant provides: Name, Password, IFSC Code, Initial Balance |
| **FR-05** | Bank generates 16-digit MID = SHA-256(name + timestamp + password)[:16] |
| **FR-06** | MID is unique to each merchant and must not be shared |

### 2.3 User Registration

| Requirement | Description |
|---|---|
| **FR-07** | User provides: Name, Mobile Number, PIN, Password, IFSC Code, Balance |
| **FR-08** | Bank generates 16-digit UID = SHA-256(name + mobile + pin + timestamp)[:16] |
| **FR-09** | MMID = SHA-256(UID + mobile)[:16] — used for UPI transactions |
| **FR-10** | PIN is stored as SHA-256 hash (never in plaintext) |

### 2.4 QR Code Generation

| Requirement | Description |
|---|---|
| **FR-11** | Merchant enters MID into UPI Machine |
| **FR-12** | UPI Machine encrypts MID using SPECK64/128 → produces VMID |
| **FR-13** | QR code image is generated containing the encrypted VMID |
| **FR-14** | Scanning QR code reveals only the encrypted VMID (not original MID) |

### 2.5 Payment Process

| Requirement | Description |
|---|---|
| **FR-15** | User scans QR code to obtain encrypted VMID |
| **FR-16** | User provides MMID, transaction amount, and PIN |
| **FR-17** | Data is sent to UPI Machine via socket connection |
| **FR-18** | UPI Machine decrypts VMID → original MID |
| **FR-19** | UPI Machine forwards complete request to Bank |

### 2.6 Transaction Processing

| Requirement | Description |
|---|---|
| **FR-20** | Bank validates: MMID exists, PIN matches, balance sufficient |
| **FR-21** | On success: debit user, credit merchant |
| **FR-22** | Transaction recorded in blockchain ledger |
| **FR-23** | Success/failure response sent back through UPI Machine to User |

### 2.7 Blockchain Ledger

| Requirement | Description |
|---|---|
| **FR-24** | Each valid transaction creates a new block |
| **FR-25** | Block contains: Transaction ID, Previous Block Hash, Timestamp, Details |
| **FR-26** | Transaction ID = SHA-256(UID + MID + Timestamp + Amount)[:16] |
| **FR-27** | Chain integrity verifiable via hash comparison |

### 2.8 Quantum Cryptography Demo

| Requirement | Description |
|---|---|
| **FR-28** | Simulate Shor's Algorithm to factor RSA modulus |
| **FR-29** | Demonstrate PIN and MMID vulnerability under quantum attack |
| **FR-30** | Highlight need for post-quantum cryptographic methods |

---

## 3. Non-Functional Requirements

| ID | Requirement |
|---|---|
| **NFR-01** | Python 3.6+ compatibility |
| **NFR-02** | Minimal dependencies (qrcode, Pillow only) |
| **NFR-03** | Socket-based communication (TCP) between components |
| **NFR-04** | Interactive CLI for bank management |
| **NFR-05** | All cryptographic operations implemented from scratch (no external crypto libraries for core algorithms) |
| **NFR-06** | Clear, well-documented source code |
| **NFR-07** | Modular architecture with shared crypto utilities |

---

## 4. Entity Descriptions

### 4.1 Bank
- Central governing body managing merchant and user accounts
- Validates all transactions (MMID, PIN, balance checks)
- Maintains the blockchain ledger for immutable transaction records
- Exposed as TCP server on port 9000

### 4.2 Merchant
- Business entity accepting UPI payments
- Registers with bank and receives a unique MID
- MID is encrypted by UPI Machine and embedded in QR code
- Receives transaction confirmations via UPI Machine

### 4.3 User
- Individual initiating payments by scanning QR codes
- Provides MMID, PIN, and transaction amount
- Receives success/failure confirmation after transaction

### 4.4 UPI Machine
- Intermediary device between User, Merchant, and Bank
- Encrypts Merchant ID using SPECK cipher (LWC) for QR codes
- Decrypts scanned VMID to recover original MID
- Forwards requests to Bank and relays responses
- Exposed as TCP server on port 8000

---

## 5. Security Requirements

| Technology | Usage |
|---|---|
| **SHA-256** | ID generation (MID, UID, MMID), PIN hashing, transaction ID hashing, block hashing |
| **SPECK64/128** | Encrypt MID → VMID for QR codes (27 rounds, 128-bit key) |
| **Blockchain** | Immutable, hash-chained transaction records with genesis block |
| **Shor's Algorithm** | Educational demo showing RSA vulnerability to quantum computing |

---

## 6. Expected Outcomes

1. A fully functional centralized UPI Payment Gateway mimicking real-world transactions
2. Lightweight Cryptography (SPECK) for VMID generation and QR code encryption
3. Quantum Cryptography simulation (Shor's Algorithm) demonstrating PIN/MMID vulnerabilities
4. Blockchain integration for secure, immutable transaction logging and validation

---

## 7. Deliverables

- Complete source code with modular architecture
- README file with project description, run instructions, and team members
- Project Architecture document with system diagrams
- Project Requirements document (this file)
- `.gitignore` configured for Python projects
