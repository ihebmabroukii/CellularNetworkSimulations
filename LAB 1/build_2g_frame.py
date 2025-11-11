import struct
import zlib
import socket
import threading
import hashlib
import os

# -------------------------
# Part 1: Building / Sending a 2G Frame
# -------------------------
def build_2g_frame(lac, ci, tmsi, message):
    """
    Builds a 2G frame containing:
    - LAC (2 bytes)
    - CI  (2 bytes)
    - TMSI (4 bytes)
    - TLV : Type (1 byte) | Length (1 byte) | Value (message)
    - CRC32 (4 bytes)
    """
    frame = struct.pack('>H', lac)
    frame += struct.pack('>H', ci)
    frame += struct.pack('>I', tmsi)

    message_bytes = message.encode('utf-8')
    tlv = struct.pack('>B', 1)  # Type = 1 (SMS)
    tlv += struct.pack('>B', len(message_bytes))  # Message length
    tlv += message_bytes  # Value (content)
    frame += tlv

    crc_value = zlib.crc32(frame) & 0xffffffff  # CRC32 (4 bytes)
    frame += struct.pack('>I', crc_value)  # Append CRC to the end of the frame

    return frame


def verify_crc(frame):
    """
    Verifies if the CRC32 at the end of the frame is correct.
    """
    if len(frame) < 4:
        return False
    data_without_crc = frame[:-4]  # All bytes except the last 4 (CRC)
    received_crc = struct.unpack('>I', frame[-4:])[0]  # Extract received CRC
    calculated_crc = zlib.crc32(data_without_crc) & 0xffffffff  # Recalculate CRC

    return received_crc == calculated_crc


def send_frame_udp(frame, host="127.0.0.1", port=21000):
    """
    Sends the frame using a UDP socket to localhost, port 21000 by default.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(frame, (host, port))
    finally:
        sock.close()


# -------------------------
# Part 2: Attachment / Detachment Simulation
# -------------------------
IP_POOL_START = 2
IP_POOL_END = 254
IP_BASE = "10.0.0."  # ip = IP_BASE + X

sessions = {}      # Mapping: imsi -> ip
ip_to_imsi = {}    # Reverse mapping: ip -> imsi

_sessions_lock = threading.Lock()  # Thread safety lock


def _format_ip(n: int) -> str:
    return f"{IP_BASE}{n}"


def _find_next_free_ip() -> int:
    """
    Finds the smallest available IP number in the range.
    Returns the number (e.g., 2 -> 10.0.0.2) or None if all are used.
    """
    for n in range(IP_POOL_START, IP_POOL_END + 1):
        ip = _format_ip(n)
        if ip not in ip_to_imsi:
            return n
    return None


def attach_request(imsi: str) -> dict:
    """
    Simulates an attachment procedure.
    If the IMSI is already attached, returns the same IP.
    Otherwise, allocates a new free IP and stores the session.
    """
    with _sessions_lock:
        if imsi in sessions:
            return {'imsi': imsi, 'ip': sessions[imsi], 'status': 'attached'}

        next_n = _find_next_free_ip()
        if next_n is None:
            return {'imsi': imsi, 'ip': None, 'status': 'failed'}

        ip = _format_ip(next_n)
        sessions[imsi] = ip
        ip_to_imsi[ip] = imsi
        return {'imsi': imsi, 'ip': ip, 'status': 'attached'}


def detach_request(imsi: str) -> dict:
    """
    Simulates the release of a session (detachment).
    If IMSI is not found, returns status not_found.
    Otherwise, removes it and frees its IP.
    """
    with _sessions_lock:
        if imsi not in sessions:
            return {'imsi': imsi, 'status': 'not_found'}

        ip = sessions.pop(imsi)
        ip_to_imsi.pop(ip, None)
        return {'imsi': imsi, 'ip': ip, 'status': 'detached'}


def get_session(imsi: str) -> dict:
    """
    Returns the session if it exists, otherwise returns not_found.
    """
    with _sessions_lock:
        if imsi in sessions:
            return {'imsi': imsi, 'ip': sessions[imsi], 'status': 'attached'}
        else:
            return {'imsi': imsi, 'status': 'not_found'}


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    # Part 1: Frame creation and sending
    lac = 1234
    ci = 5678
    tmsi = 987654321
    message = "Bonjour depuis le 2G !"  # You can change this message

    frame = build_2g_frame(lac, ci, tmsi, message)

    print("Is CRC valid? ", verify_crc(frame))
    print("Frame (Hex):", frame.hex())
    send_frame_udp(frame)
    print("✅ Frame sent to 127.0.0.1:21000\n")

    # Part 2: Attach/detach simulator
    imsi_a = "001010123456789"
    imsi_b = "001010987654321"

    print("-> Attach IMSI A:", attach_request(imsi_a))
    print("-> Attach IMSI B:", attach_request(imsi_b))

    print("-> Re-attach IMSI A:", attach_request(imsi_a))
    print("-> Get session IMSI A:", get_session(imsi_a))
    print("-> Get session IMSI B:", get_session(imsi_b))

    print("-> Detach IMSI A:", detach_request(imsi_a))
    print("-> After detach IMSI A:", get_session(imsi_a))
    print("-> Re-attach IMSI A:", attach_request(imsi_a))


# -------------------------
# Part 3: Authentication Simulation
# -------------------------
# Simple fake subscriber database
hlr_db = {
    "001010123456789": "secret_key_abc123",
    "001010987654321": "secret_key_xyz987"
}

def generate_rand():
    return os.urandom(8)

def compute_sres(ki, rand):
    # Simplified auth algorithm (in real GSM it's A3)
    return hashlib.sha256((ki + rand.hex()).encode()).hexdigest()[:8]

def authenticate_mobile(imsi):
    if imsi not in hlr_db:
        return {"imsi": imsi, "status": "unknown_subscriber"}
    
    ki = hlr_db[imsi]
    rand = generate_rand()
    expected_sres = compute_sres(ki, rand)

    # Simulate mobile generating its own response
    mobile_sres = compute_sres(ki, rand)

    if mobile_sres == expected_sres:
        return {"imsi": imsi, "auth": "success", "rand": rand.hex(), "sres": mobile_sres}
    else:
        return {"imsi": imsi, "auth": "failure"}