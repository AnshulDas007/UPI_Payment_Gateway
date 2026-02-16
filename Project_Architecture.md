# Project Architecture — Centralized UPI Payment Gateway

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "Device 1: Bank Laptop"
        BANK["Bank Server<br/>Port 9000"]
        DB["In-Memory Database<br/>Merchants & Users"]
        BC["Blockchain Ledger"]
    end

    subgraph "Device 2: UPI Machine"
        UPI["UPI Machine Server<br/>Port 8000"]
        SPECK["SPECK64/128<br/>Encrypt / Decrypt"]
        QR["QR Code Generator"]
    end

    subgraph "Device 3: User Laptop"
        USER["User Client"]
        SCAN["QR Code Scanner<br/>(Simulated)"]
    end

    subgraph "Standalone Module"
        SHOR["Shor's Algorithm<br/>Quantum Demo"]
    end

    MERCHANT["Merchant"] -->|"Enter MID"| UPI
    UPI -->|"SPECK Encrypt"| SPECK
    SPECK -->|"Encrypted VMID"| QR
    QR -->|"QR Image"| MERCHANT

    SCAN -->|"Scanned VMID"| USER
    USER -->|"MMID + PIN + Amount + VMID"| UPI
    UPI -->|"Decrypt VMID → MID"| SPECK
    UPI -->|"JSON Transaction"| BANK

    BANK -->|"Validate Credentials"| DB
    BANK -->|"Record Transaction"| BC
    BANK -->|"Response"| UPI
    UPI -->|"Response"| USER
```

---

## 2. Module Architecture

### 2.1 `crypto_utils.py` — Shared Cryptographic Core

| Component | Purpose |
|---|---|
| `generate_id()` | SHA-256 hash → truncated 16 hex digits (MID, UID, MMID) |
| `sha256_hash()` | Full SHA-256 digest for PIN/password hashing |
| `speck_encrypt()` | SPECK64/128 block encryption (27 rounds, 128-bit key) |
| `speck_decrypt()` | SPECK64/128 block decryption (reverse rounds) |
| `Block` class | Single blockchain block with hash-chaining |
| `Blockchain` class | Manages chain: genesis block, add transactions, validation |

### 2.2 `bank.py` — Bank Server

```mermaid
flowchart TD
    A["Bank Starts"] --> B["Register Sample Data"]
    B --> C["Interactive Menu"]
    C --> D{"User Choice"}
    D -->|"1"| E["Register Merchant"]
    D -->|"2"| F["Register User"]
    D -->|"3"| G["View Merchants"]
    D -->|"4"| H["View Users"]
    D -->|"5"| I["View Blockchain"]
    D -->|"6"| J["Start Socket Server :9000"]
    J --> K["Accept Connection"]
    K --> L["Parse JSON Request"]
    L --> M{"Validate"}
    M -->|"MMID exists?"| N{"PIN correct?"}
    N -->|"Yes"| O{"Balance sufficient?"}
    O -->|"Yes"| P["Debit User / Credit Merchant"]
    P --> Q["Add Block to Blockchain"]
    Q --> R["Return Success + Tx ID"]
    M -->|"No"| S["Return Failure"]
    N -->|"No"| S
    O -->|"No"| S
```

### 2.3 `upi_machine.py` — UPI Machine (Intermediary)

```mermaid
flowchart LR
    A["Merchant enters MID"] --> B["SPECK Encrypt → VMID"]
    B --> C["Generate QR Code"]
    C --> D["Start Server :8000"]
    D --> E["User connects"]
    E --> F["Receive MMID, PIN, Amount, VMID"]
    F --> G["SPECK Decrypt VMID → MID"]
    G --> H["Forward to Bank :9000"]
    H --> I["Return Bank Response to User"]
```

### 2.4 `user.py` — User Client

```mermaid
flowchart LR
    A["Scan QR → get VMID"] --> B["Enter MMID, Amount, PIN"]
    B --> C["Connect to UPI Machine :8000"]
    C --> D["Send JSON Request"]
    D --> E["Receive & Display Response"]
```

### 2.5 `shor_simulation.py` — Quantum Demo

```mermaid
flowchart TD
    A["Generate RSA Keys p,q"] --> B["Encrypt PIN & MMID"]
    B --> C["Shor's Algorithm: Factor n"]
    C --> D["Recover φ(n) and Private Key d"]
    D --> E["Decrypt PIN & MMID"]
    E --> F["Report Vulnerability"]
```

---

## 3. Data Flow — Complete Transaction

```mermaid
sequenceDiagram
    participant M as Merchant
    participant UPI as UPI Machine
    participant U as User
    participant B as Bank

    Note over M,UPI: Setup Phase
    M->>UPI: Enter Merchant ID (MID)
    UPI->>UPI: SPECK Encrypt MID → VMID
    UPI->>M: Generate QR Code (contains VMID)

    Note over U,B: Transaction Phase
    U->>U: Scan QR Code → obtain VMID
    U->>UPI: Send {MMID, Amount, PIN, VMID}
    UPI->>UPI: SPECK Decrypt VMID → MID
    UPI->>B: Forward {MID, MMID, Amount, PIN}
    B->>B: Validate MMID, PIN, Balance
    B->>B: Debit User, Credit Merchant
    B->>B: Add Block to Blockchain
    B->>UPI: Response {status, tx_id, balance}
    UPI->>U: Forward Response
```

---

## 4. Blockchain Structure

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Genesis Block   │    │    Block #1      │    │    Block #2      │
│                  │    │                  │    │                  │
│ Tx ID: 00000000  │    │ Tx ID: a3f8b2c1  │    │ Tx ID: 7e2d91fa  │
│ Prev:  00000000  │◄───│ Prev:  <genesis> │◄───│ Prev:  <block1>  │
│ Hash:  d4e5f6... │    │ Hash:  9a8b7c... │    │ Hash:  1f2e3d... │
│ Time:  <init>    │    │ Time:  <ts1>     │    │ Time:  <ts2>     │
│ Data:  Genesis   │    │ Data:  {txn1}    │    │ Data:  {txn2}    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

Each block hash = SHA-256(index + tx_id + previous_hash + timestamp + details)

---

## 5. Security Layers

| Layer | Algorithm | Purpose |
|---|---|---|
| ID Generation | SHA-256 | Unique, collision-resistant identifiers |
| QR Encryption | SPECK64/128 | Lightweight encryption of merchant data |
| PIN Storage | SHA-256 Hash | Passwords/PINs stored as hashes, never plaintext |
| Transaction Log | Blockchain | Immutable, tamper-evident record chain |
| Vulnerability Demo | Shor's Algorithm | Shows RSA weakness to quantum attacks |

---

## 6. Network Topology

| Component | Role | Port | Protocol |
|---|---|---|---|
| Bank Server | Central authority | 9000 | TCP |
| UPI Machine | Intermediary/gateway | 8000 | TCP |
| User Client | Initiates transactions | N/A (connects to 8000) | TCP |

All communication uses JSON-encoded messages over TCP sockets.
