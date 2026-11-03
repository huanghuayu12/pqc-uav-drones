"""Verify the four-byte client-side growth of the ticket artefact (paper 3.3, item 5).

Runs the ML-KEM-768 + ML-DSA-65 mutual handshake twice, once with -no_ticket
and once with tickets enabled, and prints the ClientHello extension list of
each.  Expected: the tickets-enabled run carries one extra empty extension,
type 35 (session_ticket, length 0), so the ClientHello grows by exactly four
bytes -- 1,357 -> 1,361 on the wire -- while every other record is unchanged.
This is the measurement behind the "+11,392 and +4 bytes" sentence.
"""
import sys, tempfile, os
sys.path.insert(0, os.path.abspath("harness"))
import record_breakdown as rb, link_measure as lm

orig = rb.Stream.feed
def feed2(self, data):
    self.raw = getattr(self, "raw", b"") + data
    return orig(self, data)
rb.Stream.feed = feed2

def ext_list(raw):
    ln = int.from_bytes(raw[3:5], "big")
    p = raw[5:5+ln]
    mt = p[0]; bl = int.from_bytes(p[1:4], "big"); b = p[4:4+bl]
    i = 2+32
    sid = b[i]; i += 1+sid
    cs = int.from_bytes(b[i:i+2], "big"); i += 2+cs
    cm = b[i]; i += 1+cm
    exts = []
    if i+2 <= len(b):
        tot = int.from_bytes(b[i:i+2], "big"); i += 2
        end = i+tot
        while i+4 <= end:
            t = int.from_bytes(b[i:i+2], "big"); l = int.from_bytes(b[i+2:i+4], "big")
            exts.append((t, l)); i += 4+l
    return bl, exts

with tempfile.TemporaryDirectory() as td:
    certs = {a:(c,k) for a,c,k in lm.make_certs(td)}
    c,k = certs["ml-dsa-65"]
    for allow,tag in ((False,"no_ticket"),(True,"tickets")):
        st,rc = rb.run("MLKEM768", cert=c, key=k, port=18900+20*allow, allow_ticket=allow)
        raw = st["c2s"].raw
        bl, exts = ext_list(raw)
        print(tag, "ClientHello body", bl, "n_ext", len(exts))
        print("  ext types:", exts)
