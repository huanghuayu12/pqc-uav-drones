"""Measure a two-level certificate chain instead of extrapolating it.

Section 5.3 of the paper currently states that a second certificate in
each direction adds 11,088 bytes and about 5.0 s at 9.6 kbps, i.e. that a
two-level chain costs 31.9 kB and 16.3 s.  That number is arithmetic on
the depth-one measurement, not a measurement.  This script turns it into
one.

What is built: a root CA per signature algorithm, which signs an
intermediate CA, which signs the leaf.  The TLS server sends
leaf + intermediate (`-cert_chain`), the client sends leaf + intermediate
(`-cert` plus `-cert_chain`).  The root is trusted out of band on both
sides via `-CAfile`, which in this configuration is correct: the root is
not sent, so it cannot appear in a session ticket the way the CA
certificate did in pitfall (5) of Section 3.3, and `-no_ticket` is used
anyway.

The point of measuring rather than extrapolating is that the second link
in a chain is not a copy of the first.  An intermediate certificate
carries basicConstraints, keyUsage, and a pathLenConstraint that a leaf
does not, so its DER is a few bytes longer than the leaf's, and the
handshake gains the extra Certificate-list length prefixes.  The script
reports the measured delta so the paper can quote a measurement.

Output: results/chain_depth.csv, one row per repetition.
"""

import csv
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import link_measure as lm  # noqa: E402

# Which signature algorithm to build the hierarchy from.  ML-DSA-65 is the
# one the paper's headline number uses.
ALG = "ml-dsa-65"
REPS = 3
RATE = 9600
DELAY = 250
OUT = os.path.join(HERE, "..", "results", "chain_depth.csv")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:4])} failed: {r.stderr.strip()[:300]}")
    return r


def build_hierarchy(tmp, alg):
    """root CA -> intermediate CA -> leaf, all with the same algorithm.

    Returns (root_crt, leaf_crt, leaf_key, chain_file) where chain_file
    holds the intermediate and is what the TLS stack must send alongside
    the leaf.
    """
    keyopt = list(lm._NEWKEY[alg])
    if alg == "ecdsa-p256":
        keyopt += ["-pkeyopt", "ec_paramgen_curve:P-256"]

    p = lambda n: os.path.join(tmp, n)
    root_key, root_crt = p("root.key"), p("root.crt")
    int_key, int_csr, int_crt = p("int.key"), p("int.csr"), p("int.crt")
    leaf_key, leaf_csr, leaf_crt = p("leaf.key"), p("leaf.csr"), p("leaf.crt")
    chain = p("chain.pem")

    # Root: self-signed, CA:TRUE.
    run(["openssl", "req", "-new", "-x509", "-days", "1", "-nodes",
         "-subj", "/CN=uav-root-ca", "-keyout", root_key, "-out", root_crt,
         "-addext", "basicConstraints=critical,CA:TRUE",
         "-addext", "keyUsage=critical,keyCertSign,cRLSign"] + keyopt)

    # Intermediate: signed by the root.
    run(["openssl", "req", "-new", "-nodes", "-subj", "/CN=uav-intermediate-ca",
         "-keyout", int_key, "-out", int_csr] + keyopt)
    run(["openssl", "x509", "-req", "-in", int_csr, "-CA", root_crt,
         "-CAkey", root_key, "-CAcreateserial", "-days", "1", "-out", int_crt,
         "-extfile", write_ext(tmp, "int.ext",
                               "basicConstraints=critical,CA:TRUE,pathlen:0\n"
                               "keyUsage=critical,keyCertSign,cRLSign\n"
                               "subjectKeyIdentifier=hash\n"
                               "authorityKeyIdentifier=keyid:always\n")])

    # Leaf: signed by the intermediate.  No CA:TRUE.
    run(["openssl", "req", "-new", "-nodes", "-subj", "/CN=uav-c2-test",
         "-keyout", leaf_key, "-out", leaf_csr] + keyopt)
    run(["openssl", "x509", "-req", "-in", leaf_csr, "-CA", int_crt,
         "-CAkey", int_key, "-CAcreateserial", "-days", "1", "-out", leaf_crt,
         "-extfile", write_ext(tmp, "leaf.ext",
                               "basicConstraints=critical,CA:FALSE\n"
                               "keyUsage=critical,digitalSignature\n"
                               "extendedKeyUsage=serverAuth,clientAuth\n"
                               "subjectAltName=DNS:uav-c2-test\n"
                               "subjectKeyIdentifier=hash\n"
                               "authorityKeyIdentifier=keyid:always\n")])

    with open(int_crt) as f, open(chain, "w") as g:
        g.write(f.read())
    return root_crt, leaf_crt, leaf_key, chain


def write_ext(tmp, name, body):
    path = os.path.join(tmp, name)
    with open(path, "w") as f:
        f.write(body)
    return path


def cert_size(path):
    """DER length of a PEM certificate, which is what goes on the wire."""
    from subprocess import run as sprun
    r = sprun(["openssl", "x509", "-in", path, "-outform", "DER"],
              capture_output=True)
    return len(r.stdout)


def main():
    rows = []
    with tempfile.TemporaryDirectory() as td:
        # Reuse the shared certificate factory for the depth-one baseline so
        # the comparison holds algorithm, key size and validity fixed.
        flat = {a: (c, k) for a, c, k in lm.make_certs(td)}
        leaf_flat, key_flat = flat[ALG]

        hdir = os.path.join(td, "hier")
        os.makedirs(hdir)
        root, leaf, key, chain = build_hierarchy(hdir, ALG)

        print(f"DER sizes: leaf={cert_size(leaf)} B, "
              f"intermediate={cert_size(chain)} B, root={cert_size(root)} B")

        # Depth one: self-signed, as in every other table of the paper.
        for i in range(REPS):
            r = lm.measure("MLKEM768", leaf_flat, key_flat, ALG, RATE, DELAY,
                           25000, client_cert=leaf_flat, client_key=key_flat,
                           seed=8100 + i)
            if not r.ok:
                print(f"  depth1 rep{i} failed", file=sys.stderr)
                continue
            rows.append(dict(depth=1, alg=ALG, rep=i, bytes=r.total_bytes,
                             t_s=round(r.wall_ms / 1000, 3)))
            print(f"  depth 1 rep {i}: {r.total_bytes} B  "
                  f"{r.wall_ms/1000:.2f} s")

        # Depth two: leaf + intermediate on the wire, root trusted out of band.
        for i in range(REPS):
            r = lm.measure("MLKEM768", leaf, key, ALG, RATE, DELAY, 25000,
                           client_cert=leaf, client_key=key,
                           server_chain=chain, client_chain=chain,
                           server_ca=root, seed=8200 + i)
            if not r.ok:
                print(f"  depth2 rep{i} failed", file=sys.stderr)
                continue
            rows.append(dict(depth=2, alg=ALG, rep=i, bytes=r.total_bytes,
                             t_s=round(r.wall_ms / 1000, 3)))
            print(f"  depth 2 rep {i}: {r.total_bytes} B  "
                  f"{r.wall_ms/1000:.2f} s")

    if not rows:
        print("no successful runs", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def agg(d):
        v = [r for r in rows if r["depth"] == d]
        if not v:
            return None
        return (sum(x["bytes"] for x in v) / len(v),
                sum(x["t_s"] for x in v) / len(v))

    a1, a2 = agg(1), agg(2)
    if a1 and a2:
        print(f"\ndepth 1: {a1[0]:.0f} B  {a1[1]:.2f} s")
        print(f"depth 2: {a2[0]:.0f} B  {a2[1]:.2f} s")
        print(f"delta  : {a2[0]-a1[0]:+.0f} B  {a2[1]-a1[1]:+.2f} s")
        print(f"paper's extrapolation predicted +11,088 B and +5.0 s")
    print(f"\nwritten to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
