from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64
import json
import random
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import hashlib
import hmac
import os
import secrets
from typing import Dict, List, Tuple, Any, Set

# -------------------------
# Encryption utilities (AES-EAX)
# -------------------------

def _encrypt_text(cleartext: str, key: bytes) -> Dict[str, str]:
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(cleartext.encode('utf-8'))
    return {
        'ct': base64.b64encode(ciphertext).decode('utf-8'),
        'nonce': base64.b64encode(cipher.nonce).decode('utf-8'),
        'tag': base64.b64encode(tag).decode('utf-8')
    }


def _decrypt_text(payload: Dict[str, str], key: bytes) -> str | None:
    try:
        nonce = base64.b64decode(payload['nonce'])
        ciphertext = base64.b64decode(payload['ct'])
        tag = base64.b64decode(payload['tag'])
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        plaintext = cipher.decrypt(ciphertext)
        cipher.verify(tag)
        return plaintext.decode('utf-8')
    except Exception:
        return None


AES_KEY = b'fedcba9876543210'  # 16 bytes (AES-128)

# -------------------------
# In-memory HLR structure
# HLR_STORE[msisdn] = { 'imsi': {...}, 'ki': {...}, 'info': {...} }
# -------------------------
HLR_STORE: Dict[str, Dict[str, Any]] = {}

# -------------------------
# HLR Management (add / read / list)
# -------------------------

def add_subscriber(store: Dict[str, Dict[str, Any]], imsi: str, msisdn: str, ki: str, info: Dict[str, Any] | None = None) -> None:
    store[msisdn] = {
        'imsi': _encrypt_text(imsi, AES_KEY),
        'ki': _encrypt_text(ki, AES_KEY),
        'info': info or {}
    }
    print(f"[HLR] Registered {msisdn}.")


def get_subscriber(store: Dict[str, Dict[str, Any]], msisdn: str) -> Dict[str, Any] | None:
    record = store.get(msisdn)
    if not record:
        print(f"[HLR] {msisdn} not found.")
        return None
    imsi = _decrypt_text(record['imsi'], AES_KEY)
    ki = _decrypt_text(record['ki'], AES_KEY)
    return {'msisdn': msisdn, 'imsi': imsi, 'ki': ki, 'info': record.get('info', {})}


def list_subscribers(store: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [get_subscriber(store, msisdn) for msisdn in store]

# -------------------------
# CDR Simulation
# -------------------------

def simulate_cdrs_fast(store: Dict[str, Dict[str, Any]], days: int = 1, base_calls: int = 100, simbox_ratio: float = 0.1) -> Tuple[List[Dict[str, Any]], Set[str]]:
    subs = list(store.keys())
    cdrs: List[Dict[str, Any]] = []
    simbox_count = max(1, int(len(subs) * simbox_ratio)) if subs else 0
    simbox_set = set(random.sample(subs, simbox_count)) if subs else set()

    start_time = datetime.now() - timedelta(days=days)
    time_span = days * 24 * 3600

    for msisdn in subs:
        is_simbox = msisdn in simbox_set
        multiplier = 3 if is_simbox else 1
        num_calls = int(base_calls * multiplier * random.uniform(0.7, 1.3))

        for _ in range(num_calls):
            ts = start_time + timedelta(seconds=random.randint(0, time_span))
            if is_simbox:
                direction = 'outgoing' if random.random() < 0.99 else 'incoming'
                destination = random.choice([
                    f"2{random.randint(100000000, 999999999)}",
                    f"+{random.randint(20,99)}{random.randint(10000000,99999999)}"
                ])
                duration = int(random.expovariate(1 / 25))
            else:
                direction = 'outgoing' if random.random() < 0.6 else 'incoming'
                destination = f"2{random.randint(100000000, 999999999)}"
                duration = int(random.expovariate(1 / 120))
                if duration < 1:
                    duration = random.randint(5, 10)

            calling = msisdn if direction == 'outgoing' else destination
            called = destination if direction == 'outgoing' else msisdn

            cdrs.append({'timestamp': ts, 'calling': calling, 'called': called, 'direction': direction, 'duration': duration})

    cdrs.sort(key=lambda x: x['timestamp'])
    return cdrs, simbox_set

# -------------------------
# SIMBOX Detection (heuristics)
# -------------------------

def detect_simbox(cdrs: List[Dict[str, Any]], min_calls: int = 200, max_avg_dur: int = 30, min_out_ratio: float = 0.95, min_unique_dests: int = 80) -> Dict[str, Dict[str, Any]]:
    by_subscriber = defaultdict(list)
    for rec in cdrs:
        ab = rec['calling'] if rec['direction'] == 'outgoing' else rec['called']
        by_subscriber[ab].append(rec)

    alerts: Dict[str, Dict[str, Any]] = {}
    for msisdn, calls in by_subscriber.items():
        total = len(calls)
        outgoing = sum(1 for c in calls if c['direction'] == 'outgoing')
        out_ratio = outgoing / total if total else 0
        avg_dur = sum(c['duration'] for c in calls) / total if total else 0
        unique_dests = len({c['called'] for c in calls if c['direction'] == 'outgoing'})

        hours = [c['timestamp'].replace(minute=0, second=0, microsecond=0) for c in calls]
        peak = max(Counter(hours).values()) if hours else 0

        reasons: List[str] = []
        if total >= min_calls and avg_dur < max_avg_dur:
            reasons.append(f"{total} calls >= {min_calls} and avg duration {avg_dur:.1f}s < {max_avg_dur}s")
        if out_ratio > min_out_ratio and unique_dests >= min_unique_dests:
            reasons.append(f"Outgoing ratio {out_ratio:.2f} > {min_out_ratio} and unique destinations {unique_dests} >= {min_unique_dests}")
        if avg_dur < 10 and total > 50:
            reasons.append(f"Very short average duration ({avg_dur:.1f}s) over {total} calls")
        if peak > 100:
            reasons.append(f"High hourly peak: {peak} calls in one hour")

        if reasons:
            alerts[msisdn] = {'total_calls': total, 'outgoing': outgoing, 'out_ratio': out_ratio, 'avg_duration': avg_dur, 'unique_dests': unique_dests, 'peak_hour': peak, 'reasons': reasons}

    return alerts

# -------------------------
# Display helpers
# -------------------------

def print_alerts(alerts: Dict[str, Dict[str, Any]]) -> None:
    if not alerts:
        print('\n[SIMBOX Alert] No suspects found.')
        return
    print('\n[SIMBOX Alert] Suspected numbers:')
    for msisdn, info in alerts.items():
        print(f"- {msisdn}: {info['total_calls']} calls, avg {info['avg_duration']:.1f}s, out_ratio {info['out_ratio']:.2f}, unique {info['unique_dests']}")
        for r in info['reasons']:
            print(f"    * {r}")

# -------------------------
# Part 3: A3/A8 simulation + OTP + transaction sealing
# -------------------------

def _random_hex(nbytes: int = 16) -> str:
    return secrets.token_hex(nbytes)


def _a3a8(ki: str, rand_hex: str) -> Tuple[str, str]:
    mac = hmac.new(ki.encode('utf-8'), bytes.fromhex(rand_hex), digestmod='sha256').digest()
    sres = mac[:4].hex()
    kc = mac[4:20].hex()
    return sres, kc


def authenticate_a3a8(msisdn: str, store: Dict[str, Dict[str, Any]]) -> Tuple[bool, str | None, str | None, str | None]:
    record = store.get(msisdn)
    if not record:
        print(f"[A3/A8] {msisdn} not found in HLR.")
        return False, None, None, None
    ki = _decrypt_text(record['ki'], AES_KEY)
    if ki is None:
        print(f"[A3/A8] Unable to decrypt Ki for {msisdn}.")
        return False, None, None, None
    rand = _random_hex(16)
    sres_sim, kc_sim = _a3a8(ki, rand)
    sres_net, kc_net = _a3a8(ki, rand)
    ok = (sres_sim == sres_net)
    print(f"[A3/A8] RAND: {rand}")
    print(f"[A3/A8] SRES SIM: {sres_sim} / SRES NET: {sres_net} -> {'OK' if ok else 'FAIL'}")
    return ok, sres_sim, sres_net, kc_net


def seal_transaction(payload: str, key_material: str) -> str:
    return hashlib.sha256((payload + key_material).encode('utf-8')).hexdigest()


def send_otp_secure(msisdn: str) -> int:
    code = secrets.randbelow(900000) + 100000  # 6 digits
    print(f"[OTP] {msisdn} -> {code}")
    return code

# -------------------------
# Complete test (main)
# -------------------------
if __name__ == '__main__':
    random.seed(42)

    add_subscriber(HLR_STORE, imsi='123456789012345', msisdn='21234567890', ki='secretkey123', info={'owner': 'Alice'})
    add_subscriber(HLR_STORE, imsi='987654321098765', msisdn='21234567891', ki='otherkey456', info={'owner': 'Bob'})
    add_subscriber(HLR_STORE, imsi='555000111222333', msisdn='21234567892', ki='key3', info={'owner': 'SimA'})
    add_subscriber(HLR_STORE, imsi='555000111222334', msisdn='21234567893', ki='key4', info={'owner': 'SimB'})
    add_subscriber(HLR_STORE, imsi='555000111222335', msisdn='21234567894', ki='key5', info={'owner': 'SimC'})

    print('\nSubscribers (decrypted):')
    for s in list_subscribers(HLR_STORE):
        print(s)

    cdrs, simboxes = simulate_cdrs_fast(HLR_STORE, days=1, base_calls=80, simbox_ratio=0.4)
    print(f"\nSimulated CDRs: {len(cdrs)}. Simulated SIMBOXes: {simboxes}")

    alerts = detect_simbox(cdrs, min_calls=150, max_avg_dur=30, min_out_ratio=0.95, min_unique_dests=50)
    print_alerts(alerts)

    print('\nExamples (first 10 CDRs):')
    for rec in cdrs[:10]:
        print(f"{rec['timestamp']} | {rec['direction']} | {rec['calling']} -> {rec['called']} | dur {rec['duration']}s")

    print('\n--- Part 3: Mobile Payments (A3/A8) ---\n')
    test_msisdn = '21234567890'
    amount = '250.50 USD'
    bank = 'BankX'

    ok, sres_sim, sres_net, kc = authenticate_a3a8(test_msisdn, HLR_STORE)
    if ok:
        tx = f"Subscriber:{test_msisdn}|Amount:{amount}|Bank:{bank}"
        sealed = seal_transaction(tx, kc or '')
        print(f"[Encryption] Transaction sealed: {sealed}")
        otp = send_otp_secure(test_msisdn)
        print('[Payment] Transaction ready for confirmation via OTP.')
