#!/usr/bin/env python3
"""dtls_bound.py -- what the measured TLS 1.3 handshake would cost over DTLS 1.3.

Why this is computed rather than measured
-----------------------------------------
OpenSSL 3.5.7 implements DTLS 1.0 and 1.2 only; DTLS 1.3 (RFC 9147) is not in
the release.  Worse, DTLS 1.2 cannot carry this handshake at all, and not for a
fixable reason:

  * a TLS 1.2 cipher suite name encodes its authentication algorithm
    (ECDHE-ECDSA-..., ECDHE-RSA-...).  There is no suite for ML-DSA, so an
    ML-DSA certificate cannot authenticate a TLS 1.2 or DTLS 1.2 handshake.
    Measured: `s_server -dtls1_2` with an ML-DSA-65 certificate answers every
    ClientHello with "no shared cipher".
  * a TLS 1.2 key exchange is ECDHE over an elliptic curve.  ML-KEM is not a
    TLS 1.2 group.  Measured: `-groups MLKEM768 -dtls1_2` also ends in
    "no shared cipher", even with an ECDSA certificate.

So post-quantum DTLS means DTLS 1.3, and DTLS 1.3 means computing the delta
from RFC 9147 rather than measuring it.  That is what this script does, from
the TLS 1.3 record sizes that were actually measured.

The model
---------
RFC 9147 replaces the 5-byte TLS record header with a 13-byte DTLS header
(content type 1, version 2, epoch 2, sequence number 6, length 2), adds a
12-byte DTLS handshake header (type 1, length 3, message_seq 2,
fragment_offset 3, fragment_length 3) to every fragment, and keeps the 16-byte
AEAD tag.  A datagram of `mtu` bytes therefore carries

    mtu - 13 - 12 - 16 - 1  =  mtu - 42   bytes of handshake body

per fragment, where the 1 is the inner content-type byte.  A message of body
length L is split into ceil(L / (mtu - 42)) fragments and costs L + 42*frags.

ChangeCipherSpec does not exist in DTLS 1.3 and is charged zero.

Run: python harness/dtls_bound.py [--mtu 1200]
"""
from __future__ import annotations

import argparse
import math

# (direction, message, TLS 1.3 bytes on the wire)
# Copied from msg_anatomy.py, which reads them off the record layer.  The
# 23-byte application-probe record is excluded: it is not handshake data.
MEASURED = [
    ("c2s", "ClientHello",           1357),
    ("c2s", "ChangeCipherSpec",         6),
    ("c2s", "Certificate",           5549),
    ("c2s", "CertificateVerify",     3339),
    ("c2s", "Finished",                74),
    ("c2s", "close_notify",            24),
    ("s2c", "ServerHello",           1183),
    ("s2c", "ChangeCipherSpec",         6),
    ("s2c", "EncryptedExtensions",     28),
    ("s2c", "CertificateRequest",     107),
    ("s2c", "Certificate",           5549),
    ("s2c", "CertificateVerify",     3339),
    ("s2c", "Finished",                74),
    ("s2c", "NewSessionTicket",        79),
    ("s2c", "NewSessionTicket",        79),
    ("s2c", "close_notify",            24),
]

# TLS 1.3 wire layout per record: 5 header + 16 tag + 4 handshake header
# + body + 1 inner content type.  The two hellos are plaintext, so they carry
# no tag and no inner content type: 5 + 4 + body.
PLAINTEXT = {"ClientHello", "ServerHello", "ChangeCipherSpec"}


def body_len(name: str, wire: int) -> int:
    if name == "ChangeCipherSpec":
        return 1
    if name in ("ClientHello", "ServerHello"):
        return wire - 5 - 4
    if name == "close_notify":
        return 2
    return wire - 5 - 16 - 4 - 1


def dtls_len(name: str, body: int, mtu: int) -> int:
    if name == "ChangeCipherSpec":
        return 0                      # not a DTLS 1.3 message
    per_frag = mtu - 42
    frags = max(1, math.ceil(body / per_frag))
    return body + 42 * frags


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mtu", type=int, default=1200,
                    help="DTLS datagram payload, bytes (default 1200)")
    args = ap.parse_args()

    print(f"MTU {args.mtu} B -> {args.mtu - 42} B of handshake body per fragment\n")
    print(f"{'dir':4s} {'message':20s} {'TLS 1.3':>8s} {'frag':>5s} "
          f"{'DTLS 1.3':>9s} {'delta':>7s}")
    print("-" * 60)

    tot_tls = tot_dtls = 0
    for direction, name, wire in MEASURED:
        b = body_len(name, wire)
        per_frag = args.mtu - 42
        frags = max(1, math.ceil(b / per_frag)) if name != "ChangeCipherSpec" else 0
        d = dtls_len(name, b, args.mtu)
        tot_tls += wire
        tot_dtls += d
        print(f"{direction:4s} {name:20s} {wire:8d} {frags:5d} {d:9d} {d - wire:+7d}")

    print("-" * 60)
    print(f"{'total':25s} {tot_tls:8d} {'':5s} {tot_dtls:9d} {tot_dtls - tot_tls:+7d}")
    pct = 100.0 * (tot_dtls - tot_tls) / tot_tls
    print(f"\nDTLS 1.3 costs {tot_dtls - tot_tls} bytes more, {pct:+.1f} % of {tot_tls}.")
    print("The delta is framing spread over the same messages, so it scales the "
          "handshake rather than reordering it.")

    # The two identity records, before and after, to show the ratio is stable.
    # NB this is the certificate-plus-signature subset, not the paper's identity
    # column, which also absorbs framing.
    ident_tls = 2 * (5549 + 3339)
    ident_dtls = 2 * (dtls_len("Certificate", body_len("Certificate", 5549), args.mtu)
                      + dtls_len("CertificateVerify",
                                 body_len("CertificateVerify", 3339), args.mtu))
    print(f"certificate+signature records: {ident_tls} -> {ident_dtls} B "
          f"({100*ident_dtls/ident_tls - 100:+.1f} %), "
          f"share {100*ident_tls/tot_tls:.1f} % -> {100*ident_dtls/tot_dtls:.1f} %")


if __name__ == "__main__":
    main()
