# 📡 TP2 - HLR, SIMBOX Detection & Secure Mobile Transaction (Refactored English Version)

## 🧭 Overview

This project simulates a simplified **telecommunication core system** combining **HLR (Home Location Register)** management, **CDR (Call Detail Record)** generation, **SIMBOX fraud detection**, and a **secure mobile payment simulation** using **A3/A8 authentication**, **OTP verification**, and **cryptographic sealing**.

It is designed for learning and demonstration purposes, showing how mobile network security and fraud analysis can be modeled programmatically in Python.

---

## ⚙️ Main Components

### 1. 🗂️ Home Location Register (HLR) Simulation

The HLR is an in-memory database that stores information about subscribers:

- **IMSI** (International Mobile Subscriber Identity)
- **MSISDN** (phone number)
- **Ki** (secret authentication key)
- Additional **metadata** like the subscriber owner

Each entry is **encrypted using AES (EAX mode)** to simulate secure storage.

#### 🔧 Key Functions

| Function             | Description                                                   |
| -------------------- | ------------------------------------------------------------- |
| `add_subscriber()`   | Registers a new subscriber in the HLR, encrypting IMSI and Ki |
| `get_subscriber()`   | Retrieves and decrypts subscriber data                        |
| `list_subscribers()` | Lists all subscribers with decrypted values                   |

The AES key used is a static 128-bit key (`fedcba9876543210`) for demonstration.  
In a real network, this key would be stored securely (e.g., in a KMS or HSM).

---

### 2. 🔒 AES Encryption Module

Implements secure text encryption and decryption for sensitive subscriber data.

- **Mode:** AES-EAX (provides both confidentiality and integrity)
- **Helper functions:**
  - `_encrypt_text()` → returns ciphertext + nonce + tag (all Base64 encoded)
  - `_decrypt_text()` → verifies integrity and returns plaintext

This ensures that even if the database is exposed, IMSI and Ki values remain unreadable.

---

### 3. 📞 CDR Simulation (Call Detail Records)

Generates synthetic telecom call logs for testing fraud detection algorithms.

Each CDR contains:

- Timestamp
- Calling and Called numbers
- Call direction (`incoming` or `outgoing`)
- Duration (in seconds)

#### 🧮 Function: `simulate_cdrs_fast()`

It generates realistic traffic:

- **Normal subscribers** make a moderate number of calls.
- **SIMBOX subscribers** (fraudulent) generate:
  - Mostly outgoing calls (≈99%)
  - Shorter durations (typical of bypassed VoIP traffic)
  - Higher call frequency

You can control:

- `days`: period of simulation
- `base_calls`: average number of calls per subscriber
- `simbox_ratio`: fraction of subscribers behaving as SIMBOXes

Returns:

1. A list of simulated CDRs
2. The set of MSISDNs designated as SIMBOXes (ground truth)

---

### 4. 🕵️‍♂️ SIMBOX Detection Engine

Detects suspected SIMBOX numbers based on heuristics derived from telecom analytics.

#### ⚡ Function: `detect_simbox()`

It analyzes all CDRs per subscriber and calculates:

- Total calls
- Average duration
- Ratio of outgoing vs total calls
- Number of unique destinations
- Peak calls per hour

Then, it flags suspicious MSISDNs based on thresholds:

| Heuristic           | Condition            | Interpretation                      |
| ------------------- | -------------------- | ----------------------------------- |
| Call volume         | ≥ `min_calls`        | High traffic user                   |
| Average duration    | ≤ `max_avg_dur`      | Calls too short                     |
| Outgoing ratio      | ≥ `min_out_ratio`    | Almost no incoming calls            |
| Unique destinations | ≥ `min_unique_dests` | Calls to too many different numbers |
| Peak hour traffic   | ≥ 100                | Very high hourly activity           |

Detected SIMBOX numbers are printed with detailed reasons.

---

### 5. 🔐 Authentication and Secure Transaction (A3/A8 Simulation)

Simulates the GSM **A3/A8** algorithm used to authenticate a SIM card.

#### 🔁 Process

1. Network sends a random challenge (**RAND**).
2. Both SIM and Network compute:
   - **SRES** (Signed Response)
   - **Kc** (Session Key)
     using the Ki (subscriber’s secret key) and HMAC-SHA256.
3. Authentication succeeds if both SRES match.

#### ⚙️ Function: `authenticate_a3a8()`

Returns:

- Success flag (True/False)
- SIM’s SRES
- Network’s SRES
- Derived session key `Kc`

---

### 6. 💳 Secure Transaction with OTP

Once the subscriber is authenticated, a simulated mobile payment is processed.

#### 🪄 Steps

1. **Transaction sealing**  
   The transaction payload is hashed with the session key using:
   ```python
   seal_transaction(payload, key_material)
   ```

OTP Delivery
A random 6-digit OTP is generated and displayed:
send_otp_secure(msisdn)
In a real system, it would be sent via SMS or app.

The transaction is ready for confirmation once the OTP is entered.

🧩 Main Program Flow

When you run the script (python tp2_part1_and_2_refactored.py):
1.Five subscribers (Alice, Bob, SimA, SimB, SimC) are created and encrypted in the HLR.
2.A set of CDRs is simulated for 1 day, with 40% being SIMBOX-like.
3.SIMBOX detection analyzes the traffic and prints suspected fraudsters.
4.The first 10 CDRs are displayed for inspection.
5.A3/A8 authentication is run for Alice’s number.
6.If authentication succeeds:
A mock transaction is sealed cryptographically.
A 6-digit OTP is generated for confirmation.

📊 Example Output

[HLR] Registered 21234567890.
...
Subscribers (decrypted):
{'msisdn': '21234567890', 'imsi': '123456789012345', 'ki': 'secretkey123', 'info': {'owner': 'Alice'}}
...

Simulated CDRs: 1124. Simulated SIMBOXes: {'21234567892', '21234567893'}

[SIMBOX Alert] Suspected numbers:

- 21234567892: 350 calls, avg 22.3s, out_ratio 0.98, unique 180
  - 350 calls >= 150 and avg duration 22.3s < 30s
  - Outgoing ratio 0.98 > 0.95 and unique destinations 180 >= 50
  - Very short average duration (22.3s) over 350 calls

🔐 Security Concepts Demonstrated
| Concept | Explanation |
| ---------------------- | -------------------------------------------------------------------------- |
| **AES Encryption** | Protects sensitive subscriber info (IMSI, Ki) |
| **EAX Mode** | Provides both encryption and authentication (integrity check) |
| **HMAC** | Used for A3/A8 authentication to simulate cryptographic challenge-response |
| **OTP** | Adds an additional verification step for mobile payments |
| **Hash-based Sealing** | Ensures transaction data cannot be tampered with |

🚀 How to Run
🧰 Requirements

Install dependencies:
pip install pycryptodome

▶️ Execute
Run the script:
python tp2_part1_and_2_refactored.py

🧠 Key Takeaways

Demonstrates end-to-end telecom security flow: from subscriber registration → call simulation → fraud detection → authentication → secure transaction.
Introduces cryptographic primitives (AES, HMAC, SHA256) in a practical context.
Provides a testable sandbox for telecom security and analytics experiments.
Easy to extend with:
Database backend (SQLite, PostgreSQL)
REST API for subscriber management
Visualization dashboards (e.g., using Plotly)
