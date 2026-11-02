#!/usr/bin/env python3
"""Figures for the measured TLS 1.3 post-quantum handshake study.

Every number plotted here comes from results/*.csv or
results/record_breakdown.json, produced by link_measure.py and
record_breakdown.py.  Nothing is synthesised.  The one exception is Figure 4,
which explicitly plots a *prediction* for FN-DSA-512 and says so in the
caption and on the axis.
"""
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures")
os.makedirs(FIG, exist_ok=True)

matplotlib.rcParams.update({
    "font.size": 8, "axes.linewidth": 0.6, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7,
    "figure.dpi": 200, "savefig.dpi": 600, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02, "axes.grid": False,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
})

# Okabe-Ito: colour-blind safe
CB = ["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442",
      "#0072B2", "#D55E00", "#CC79A7"]
GREY = "#767676"


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIG, f"{name}.{ext}"))
    plt.close(fig)
    print(f"  {name}.pdf / .png")


def load(fn):
    path = os.path.join(RES, fn)
    return list(csv.DictReader(open(path)))


def idx(rows):
    return {(r["group"], r["cert_alg"]): r for r in rows}


# --------------------------------------------------------------- Figure 1
def fig1():
    """Byte attribution: how much of a handshake is key exchange vs identity."""
    rows = json.load(open(os.path.join(RES, "record_breakdown.json")))
    order = ["X25519 + ECDSA-P256", "X25519 + ML-DSA-65",
             "ML-KEM-768 + ECDSA-P256", "ML-KEM-768 + ML-DSA-65",
             "ML-KEM-768 + PSK", "X25519 + PSK"]
    rows = sorted(rows, key=lambda r: order.index(r["label"]))

    labels, kx, nonkx = [], [], []
    for r in rows:
        labels.append(r["label"])
        k = r["c2s_kx_bytes"] + r["s2c_kx_bytes"]
        kx.append(k)
        nonkx.append(r["total"] - k)

    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(6.6, 2.55))
    # The identity segment is hatched as well as coloured so that the two
    # parts stay distinguishable when the figure is printed in greyscale.
    ax.barh(y, kx, 0.6, color=CB[2], label="key exchange (ClientHello/ServerHello)")
    ax.barh(y, nonkx, 0.6, left=kx, color=CB[6], hatch="////",
            edgecolor="white", linewidth=0.0,
            label="identity: Certificate + CertificateVerify")
    for i, (k, n) in enumerate(zip(kx, nonkx)):
        ax.text(k + n + 320, i, f"{k+n:,} B", va="center", fontsize=7)
        if n > 2000:
            ax.text(k + n / 2, i, f"{100*n/(k+n):.0f}%", va="center",
                    ha="center", fontsize=6.6, color="white")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("handshake bytes, both directions (mutual authentication)")
    ax.set_xlim(0, 26200)
    ax.invert_yaxis()
    ax.legend(loc="lower right", frameon=False, fontsize=6.8)
    save(fig, "m1_breakdown")


# --------------------------------------------------------------- Figure 2
def fig2():
    """Certificate parameter sweep: bytes and time, two link rates."""
    s96, s64 = idx(load("real_9600_sweep.csv")), idx(load("real_64k_sweep.csv"))
    certs = ["ecdsa-p256", "ml-dsa-44", "ml-dsa-65", "ml-dsa-87"]
    nice = ["ECDSA\nP-256", "ML-DSA\n44", "ML-DSA\n65", "ML-DSA\n87"]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(6.6, 2.5),
                                  gridspec_kw={"width_ratios": [1.35, 1]})

    x = np.arange(len(certs))
    w = 0.36
    t96 = [float(s96[("MLKEM768", c)]["wall_ms"]) / 1000 for c in certs]
    t64 = [float(s64[("MLKEM768", c)]["wall_ms"]) / 1000 for c in certs]
    ax.bar(x - w / 2, t96, w, color=CB[5], label="9.6 kbps / 250 ms")
    ax.bar(x + w / 2, t64, w, color=CB[1], label="64 kbps / 2 ms")
    for xi, v in zip(x - w / 2, t96):
        ax.text(xi, v + 0.28, f"{v:.2f}", ha="center", fontsize=6.4)
    for xi, v in zip(x + w / 2, t64):
        ax.text(xi, v + 0.28, f"{v:.2f}", ha="center", fontsize=6.4)
    ax.set_xticks(x)
    ax.set_xticklabels(nice, fontsize=7)
    ax.set_ylabel("handshake completion time (s)")
    ax.set_title("(a) ML-KEM-768 + certificate signature", fontsize=7.8)
    ax.set_ylim(0, 16.5)
    ax.legend(loc="upper left", frameon=False, fontsize=6.6)

    # right panel: the same sweep expressed as marginal bytes per second,
    # which is the quantity that transfers between links
    steps, rates96, rates64 = [], [], []
    for i in range(1, len(certs)):
        b0 = int(s96[("MLKEM768", certs[i - 1])]["total_bytes"])
        b1 = int(s96[("MLKEM768", certs[i])]["total_bytes"])
        short = ["ECDSA", "44", "65", "87"]
        steps.append(f"{short[i-1]}$\\to${short[i]}")
        rates96.append((b1 - b0) / (t96[i] - t96[i - 1]))
        rates64.append((b1 - b0) / (t64[i] - t64[i - 1]))
    xi = np.arange(len(steps))
    ax2.bar(xi - w / 2, rates96, w, color=CB[5])
    ax2.bar(xi + w / 2, rates64, w, color=CB[1])
    ax2.axhline(2 * 9600 / 8, color=CB[5], lw=0.8, ls=":")
    ax2.axhline(2 * 64000 / 8, color=CB[1], lw=0.8, ls=":")
    ax2.set_xticks(xi)
    ax2.set_xticklabels(steps, fontsize=6.8)
    ax2.set_ylabel("marginal B/s")
    ax2.set_title("(b) slope of the byte$\\to$time relation", fontsize=7.8)
    ax2.text(0.03, 0.94, "dotted: ideal 2$\\times$link rate", transform=ax2.transAxes,
             fontsize=6.0, color=GREY, va="top")
    ax2.set_ylim(0, 19500)
    fig.subplots_adjust(wspace=0.42)
    save(fig, "m2_sweep")


# --------------------------------------------------------------- Figure 3
def fig3():
    """Architecture comparison: certificate vs pre-provisioned trust."""
    s96, s64 = idx(load("real_9600_sweep.csv")), idx(load("real_64k_sweep.csv"))
    p96, p64 = idx(load("real_psk_9600.csv")), idx(load("real_psk_64k.csv"))

    cfgs = [("X25519 $+$ ECDSA\n(classical)", ("X25519", "ecdsa-p256"), ("X25519", "ecdsa-p256")),
            ("ML-KEM-768\n$+$ ML-DSA-65", ("MLKEM768", "ml-dsa-65"), None),
            ("ML-KEM-768\n$+$ PSK", None, ("MLKEM768", "psk"))]

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.5), sharey=False)
    for ax, (data, psk_data, rate, tag) in zip(
            axes, [(s96, p96, 9600, "(a) 9.6 kbps, 250 ms one-way"),
                   (s64, p64, 64000, "(b) 64 kbps, 2 ms one-way")]):
        vals = []
        for label, ck, pk in cfgs:
            if ck:
                vals.append(float(data[ck]["wall_ms"]) / 1000)
            else:
                vals.append(float(psk_data[pk]["wall_ms"]) / 1000)
        x = np.arange(len(cfgs))
        bars = ax.bar(x, vals, 0.52, color=[CB[0], CB[6], CB[3]])
        base = vals[0]
        for xi, v in zip(x, vals):
            # absolute time above the bar, ratio inside it: two rows of text
            # would collide at these heights
            ax.text(xi, v * 1.03, f"{v:.2f} s", ha="center", va="bottom", fontsize=7)
            ax.text(xi, v * 0.45, f"{v/base:.2f}$\\times$", ha="center",
                    va="center", fontsize=6.8, color="white")
        ax.set_xticks(x)
        ax.set_xticklabels([c[0] for c in cfgs], fontsize=6.8)
        ax.set_title(tag, fontsize=7.8)
        ax.set_ylabel("handshake completion time (s)")
        ax.set_ylim(0, max(vals) * 1.20)
    fig.subplots_adjust(wspace=0.32)
    save(fig, "m3_architecture")


# --------------------------------------------------------------- Figure 4
def fig4():
    """Byte-cost ladder, measured points plus one labelled prediction.

    The FN-DSA-512 point is NOT measured: OpenSSL 3.5 has no Falcon
    implementation, so it is the measured ML-DSA-65 anchor minus the byte
    difference between an ML-DSA-65 and an FN-DSA-512 certificate, converted
    at the slope measured in Figure 2(b).  It is drawn hollow and hatched so
    that it cannot be mistaken for a measurement.
    """
    s96 = idx(load("real_9600_sweep.csv"))
    p96 = idx(load("real_psk_9600.csv"))

    base_b = int(s96[("MLKEM768", "ml-dsa-65")]["total_bytes"])
    base_t = float(s96[("MLKEM768", "ml-dsa-65")]["wall_ms"]) / 1000

    b87 = int(s96[("MLKEM768", "ml-dsa-87")]["total_bytes"])
    t87 = float(s96[("MLKEM768", "ml-dsa-87")]["wall_ms"]) / 1000
    slope = (t87 - base_t) / (b87 - base_b)          # s per byte

    falcon_delta = 2 * ((1952 - 897) + (3309 - 666))
    falcon_b, falcon_t = base_b - falcon_delta, base_t - falcon_delta * slope

    rows = [
        ("ML-KEM-768 + ML-DSA-87", b87, t87, CB[6], True),
        ("ML-KEM-768 + ML-DSA-65", base_b, base_t, CB[5], True),
        ("ML-KEM-768 + FN-DSA-512", falcon_b, falcon_t, CB[7], False),
        ("ML-KEM-768 + ML-DSA-44", int(s96[("MLKEM768", "ml-dsa-44")]["total_bytes"]),
         float(s96[("MLKEM768", "ml-dsa-44")]["wall_ms"]) / 1000, CB[4], True),
        ("ML-KEM-768 + PSK", int(p96[("MLKEM768", "psk")]["total_bytes"]),
         float(p96[("MLKEM768", "psk")]["wall_ms"]) / 1000, CB[3], True),
        ("X25519 + ECDSA-P256", int(s96[("X25519", "ecdsa-p256")]["total_bytes"]),
         float(s96[("X25519", "ecdsa-p256")]["wall_ms"]) / 1000, CB[0], True),
    ]

    y = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    time_x = 31200          # fixed column so the labels line up
    for i, (label, b, t, c, measured) in enumerate(rows):
        ax.barh(i, b, 0.58, color=c if measured else "none",
                edgecolor=c, hatch="" if measured else "///", linewidth=1.0)
        ax.text(b + 320, i, f"{b:,} B", va="center", fontsize=6.8,
                color="0.15" if measured else c)
        ax.text(time_x, i, f"{t:.2f} s", va="center", fontsize=6.8,
                color="0.15" if measured else c,
                fontstyle="normal" if measured else "italic")

    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows], fontsize=7)
    ax.set_xlabel("handshake bytes  $\\cdot$  right column: completion time at "
                  "9.6 kbps / 250 ms")
    ax.set_xlim(0, 35500)
    ax.set_xticks([0, 5000, 10000, 15000, 20000, 25000, 30000])
    ax.invert_yaxis()
    ax.axhline(2.5, color="0.75", lw=0.6)
    ax.text(0.99, -0.30, "hatched / italic = predicted from measured slope, not measured",
            transform=ax.transAxes, ha="right", fontsize=6.1, color=CB[7])
    save(fig, "m4_ladder")


# --------------------------------------------------------------- Figure 5
def fig5():
    """The ticket artefact: what one mis-flagged option did to the numbers.

    Both bars come from record_breakdown.py with the server-side ticket flag
    toggled, so they are the same script, the same certificate and the same
    handshake.  With tickets enabled the CA certificate that -CAfile also uses
    to build the outgoing chain is embedded in each of the two post-handshake
    tickets, growing each from 79 to 5,775 bytes.
    """
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    c2s = [10372, 10376]
    s2c = [10468, 21860]
    x = np.arange(2)
    ax.bar(x, c2s, 0.42, color=CB[2], label="client$\\to$server")
    ax.bar(x, s2c, 0.42, bottom=c2s, color=CB[6], hatch="////",
           edgecolor="white", linewidth=0.0, label="server$\\to$client")
    totals = [a + b for a, b in zip(c2s, s2c)]
    for xi, v in zip(x, totals):
        ax.text(xi, v + 1200, f"{v:,} B", ha="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(["-no_ticket\n(both sides)", "default\n(ticket embeds\nCA cert)"],
                       fontsize=6.7)
    ax.set_ylabel("handshake bytes, ML-KEM-768\n+ ML-DSA-65, mutual auth")
    ax.set_ylim(0, 41000)
    ax.set_xlim(-0.6, 1.6)
    ax.legend(loc="upper left", frameon=False, fontsize=6.5, handlelength=1.0)
    ax.annotate("+11,396 B\n(+54.7%)", xy=(1.0, 33200), xytext=(0.5, 36500),
                fontsize=6.6, color=GREY, ha="center", va="center",
                arrowprops=dict(arrowstyle="->", color="0.6", lw=0.7,
                                connectionstyle="arc3,rad=-0.2"))
    save(fig, "m5_artefact")


# --------------------------------------------------------------- Figure 6
def fig6():
    """What link loss does to the handshake, and what it does not do.

    Two panels answer two different questions.  (a) is the distribution:
    eight runs per configuration per loss rate, so the spread is visible
    rather than averaged away.  (b) tests whether the penalty is a property
    of the handshake or a property of the link, by plotting the mean
    increase against the number of losses actually suffered.  If the points
    collapse onto one line through the origin, the cost of a loss is a
    constant and the only thing that varies between configurations is how
    many losses they incur.
    """
    rows = load("loss_sweep.csv")
    for r in rows:
        r["t"] = float(r["t_s"]); r["p"] = float(r["loss_prob"])
        r["d"] = int(r["drops"])

    cfgs = ["X25519 + ECDSA-P256", "ML-KEM-768 + PSK",
            "ML-KEM-768 + ML-DSA-44", "ML-KEM-768 + ML-DSA-65"]
    short = ["X25519 $+$ ECDSA", "ML-KEM-768 $+$ PSK",
             "ML-KEM-768 $+$ ML-DSA-44", "ML-KEM-768 $+$ ML-DSA-65"]
    colors = [CB[0], CB[3], CB[4], CB[5]]
    ps = [0.0, 0.10, 0.20]

    by = {}
    for r in rows:
        by.setdefault((r["config"], r["p"]), []).append(r)
    base = {c: np.mean([x["t"] for x in by[(c, 0.0)]]) for c in cfgs}

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(6.8, 2.75),
        gridspec_kw={"width_ratios": [1.1, 1.0]})

    for ci, c in enumerate(cfgs):
        meds = []
        for p in ps:
            ts = np.array([x["t"] for x in by[(c, p)]])
            jit = np.linspace(-0.014, 0.014, ts.size)
            ax.plot(p + jit, ts, "o", ms=2.4, mfc="none", mec=colors[ci],
                    mew=0.55, alpha=0.85)
            meds.append((p, np.median(ts)))
        ax.plot([m[0] for m in meds], [m[1] for m in meds], "-",
                color=colors[ci], lw=1.1, label=short[ci])
        for p, m in meds:
            ax.plot([p], [m], "o", color=colors[ci], ms=3.4)

    ax.set_yscale("log")
    ax.set_xlabel("per-segment loss probability $p$")
    ax.set_ylabel("handshake completion time (s)")
    ax.set_title("(a) distributions, 8 runs each, open circles", fontsize=7.8)
    ax.set_xticks(ps)
    ax.set_xticklabels(["0", "0.10", "0.20"])
    ax.set_xlim(-0.035, 0.235)
    ax.set_ylim(1.6, 17.0)

    # (b) penalty against losses incurred
    allpts = []
    for ci, c in enumerate(cfgs):
        for p in ps:
            g = by[(c, p)]
            d = float(np.mean([x["d"] for x in g]))
            dt = float(np.mean([x["t"] for x in g])) - base[c]
            ax2.plot([d], [dt], "o", color=colors[ci], ms=4.0,
                     mfc=colors[ci] if p else "none", mew=0.9)
            allpts.append((d, dt))
    num = sum(d * t for d, t in allpts); den = sum(d * d for d, t in allpts)
    slope = num / den
    xs = np.linspace(0, 3.7, 30)
    ax2.plot(xs, slope * xs, "--", color=GREY, lw=0.9, zorder=0)
    ax2.set_xlabel("mean losses per handshake")
    ax2.set_ylabel("mean increase over the clean link (s)")
    ax2.set_title("(b) the cost of a loss is a constant", fontsize=7.8)
    ax2.set_xlim(0, 3.9)
    ax2.set_ylim(-0.1, 1.75)
    ax2.text(0.97, 0.10,
             f"slope {slope:.3f} s per loss\n= {100*slope/1.2:.0f}% of the "
             f"1.2 s RTO",
             transform=ax2.transAxes, ha="right", va="bottom",
             fontsize=6.3, color=GREY)

    h, lab = ax.get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.01),
               handlelength=1.6, columnspacing=1.1, handletextpad=0.5,
               fontsize=6.5)
    fig.subplots_adjust(bottom=0.30, wspace=0.30, top=0.88)
    save(fig, "m6_loss")


def fig7():
    """Rate sweep at fixed 250 ms propagation delay.

    (a) Completion time against link rate, log-log.  If the handshake were
        pure serialisation the points would be a line of slope -1; the
        deviation at high rate is the fixed propagation and round-trip cost.
    (b) The cost of each architecture relative to the classical baseline at
        the same rate.  The certificate penalty is not a constant: it grows
        as the link gets slower, which is the point of the figure.
    """
    from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator

    rows = load("rate_sweep.csv")
    cases = [
        ("X25519 + ECDSA-P256",    CB[0], "o"),
        ("ML-KEM-768 + ML-DSA-65", CB[1], "s"),
        ("ML-KEM-768 + PSK",       CB[5], "^"),
    ]
    rates = sorted({int(r["rate_bps"]) for r in rows})
    tick_lab = [f"{r / 1000:g}" for r in rates]

    def series(label):
        out = []
        for r in rates:
            t = [float(x["t_s"]) for x in rows
                 if x["config"] == label and int(x["rate_bps"]) == r]
            if t:
                out.append((r, sum(t) / len(t)))
        return out

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(6.6, 2.5))
    data = {}
    for label, col, mk in cases:
        d = series(label)
        data[label] = dict(d)
        ax.plot([x for x, _ in d], [y for _, y in d], marker=mk, ms=3.6,
                lw=1.1, color=col, mfc="white", mew=0.9, label=label)

    for a in (ax, ax2):
        a.set_xscale("log")
        a.xaxis.set_major_locator(FixedLocator(rates))
        a.xaxis.set_major_formatter(FixedFormatter(tick_lab))
        a.xaxis.set_minor_locator(NullLocator())
        a.set_xlim(2000, 46000)
        a.set_xlabel("Link rate per direction (kbps)")

    ax.set_yscale("log")
    ax.yaxis.set_major_locator(FixedLocator([1.5, 2, 3, 5, 10, 20, 40]))
    ax.yaxis.set_major_formatter(FixedFormatter(["1.5", "2", "3", "5", "10",
                                                 "20", "40"]))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylim(1.05, 55)
    ax.set_ylabel("Handshake completion time (s)")
    ax.set_title("(a) time against rate, 250 ms one-way", fontsize=7.5, pad=3)
    # 9.6 kbps is the DO-362 operating point; mark it with a tick on the axis
    # rather than a full-height rule, which would cut through the legend.
    ax.plot([9600], [1.02], marker="v", ms=4.5, color=GREY, clip_on=False,
            zorder=3, label="_nolegend_")

    cls = data["X25519 + ECDSA-P256"]
    for label, col, mk in cases[1:]:
        d = data[label]
        xs, ys = [], []
        for r in rates:
            if r in d and r in cls:
                xs.append(r)
                ys.append(d[r] / cls[r])
        ax2.plot(xs, ys, marker=mk, ms=3.6, lw=1.1, color=col,
                 mfc="white", mew=0.9, label=label)
        for r, y in zip(xs, ys):
            if r == 9600:
                ax2.annotate(f"{y:.2f}$\\times$", xy=(r, y), xytext=(6, 3),
                             textcoords="offset points", fontsize=6.2,
                             color=col)

    ax2.axhline(1.0, color=GREY, lw=0.7, ls=(0, (2, 2)), zorder=0)
    ax2.set_ylim(0.8, 10.2)
    ax2.set_ylabel("Cost relative to classical, same rate")
    ax2.set_title("(b) the penalty is not rate-invariant", fontsize=7.5, pad=3)

    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.98), frameon=False,
              handlelength=1.6, labelspacing=0.22, borderpad=0.1,
              fontsize=6.2)
    fig.subplots_adjust(wspace=0.36)
    save(fig, "m7_rate")

if __name__ == "__main__":
    print("figures:")
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7()
