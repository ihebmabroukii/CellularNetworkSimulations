# first exercice

# 📘 Code Explanation and Justification

## 🔹 Part 1 – Construction and Sending of a 2G Frame

This part simulates the transmission of a typical **2G frame**, used in mobile networks to carry information such as SMS messages or signaling data.

---

### 🔸 Function `build_2g_frame(lac, ci, tmsi, message)`

**Objective:**  
To build a binary frame that follows a simplified version of the 2G protocol structure.

**Steps:**

- **LAC (Location Area Code)** and **CI (Cell ID)** → 2 bytes each
- **TMSI (Temporary Mobile Subscriber Identity)** → 4 bytes
- **TLV (Type-Length-Value)** → a common structure in telecom protocols
  - **Type = 1** → represents an SMS
  - **Length** → the message length
  - **Value** → the actual message content (encoded in UTF-8)

Finally, a **CRC32 checksum (4 bytes)** is added to ensure data integrity during transmission.

> 🧩 **Why CRC32?**  
> The CRC (Cyclic Redundancy Check) is a widely used error detection mechanism in networking and telecommunications.  
> It ensures that the frame has not been altered or corrupted during transmission.

---

### 🔸 Function `verify_crc(frame)`

Checks whether the CRC at the end of the frame is valid.

It recalculates the CRC32 from the data and compares it with the received CRC value.

> 🧩 **Why?**  
> To ensure the frame’s integrity.  
> This verification step is essential in any communication protocol to detect transmission errors.

---

### 🔸 Function `send_frame_udp(frame, host, port)`

Sends the binary frame through a **UDP socket** to a specific IP address and port (default: `127.0.0.1:21000`).

> 🧩 **Why UDP?**  
> UDP is fast and simple (no connection required).  
> It is ideal for simulating frame transmission where reliability is not critical.

---

## 🔹 Part 2 – Attachment / Detachment Simulation

This part simulates **session management** in a mobile network, as if each user (IMSI) were assigned an IP address when attaching to the network.

---

### 🔸 Global Variables

- `sessions`: maps **IMSI → IP**
- `ip_to_imsi`: reverse mapping to quickly find which IMSI owns a given IP
- `_sessions_lock`: ensures thread safety (useful if multiple attachments occur simultaneously)

> 🧩 **Why use a lock (`threading.Lock`)?**  
> To prevent race conditions or inconsistent data access when several threads modify sessions at the same time.

---

### 🔸 Function `attach_request(imsi)`

Simulates a user attachment procedure.

- If the user is already attached → returns the same IP.
- Otherwise → allocates the next available IP (from `10.0.0.2` to `10.0.0.254`).
- Returns a session dictionary with the IMSI, assigned IP, and status.

> 🧩 **Why this simulation?**  
> In a real mobile network, during the attach procedure, the core network (e.g., **SGSN/GGSN** in 3G or **MME/PGW** in 4G) assigns an IP to the subscriber.  
> This function reproduces that logic in a simplified way.

---

### 🔸 Function `detach_request(imsi)`

Simulates the user detachment process (freeing the assigned IP address).

> 🧩 **Why?**  
> It’s the reverse mechanism of attachment: when a user disconnects, the IP address is released and made available again.

---

### 🔸 Function `get_session(imsi)`

Returns the current session of a user if it exists; otherwise, reports `not_found`.

---

## 🔹 Example of Use

In the block `if __name__ == "__main__":`:

- A frame is constructed and sent.
- The CRC validity and frame (in hexadecimal form) are displayed.
- Several attachments and detachments are simulated using fake IMSIs.
- The script shows how sessions are created, retrieved, and released.

---

## 🧩 Purpose of This Work

This code was developed to:

- Simulate the behavior of a **simplified 2G network**, from frame construction to session management.
- Demonstrate understanding of **key mobile network concepts**:
  - Frame structure (LAC, CI, TMSI, TLV)
  - Data integrity (CRC)
  - IP address and session management
- Allow **local testing** and **educational experimentation** without relying on a real GSM network.

## 🔹 Part 3 – Mobile Authentication Simulation (2G/3G)

This part simulates the authentication process between a mobile device, the **VLR**, and the **HLR/AuC** in GSM/UMTS networks.  
The goal is to verify a subscriber’s identity **without exposing the secret key** (Ki) stored in the HLR/AuC.

---

### 🔸 Authentication Process

1. The **VLR** generates a random challenge (RAND).
2. The **mobile device** computes a response (SRES) using its secret key (Ki) and the challenge.
3. The **VLR** compares the SRES with the expected value calculated from the HLR/AuC.
4. If they match, authentication succeeds; otherwise, it fails.
