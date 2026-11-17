"""
Langkah 5: Uji statistik sederhana + interval kepercayaan.

Pertanyaan: apakah perbedaan persen menang-dari-P1 antar sirkuit / antar musim
benar-benar bermakna, atau bisa terjadi hanya karena kebetulan (sampel kecil)?

Cara pakai (dari folder utama project):
    pip install scipy
    python src/05_stats_tests.py

Input : data/f1.db
Output: reports/stats_summary.txt
        reports/figures/06_pole_win_ci_by_circuit.png
"""
import sqlite3
from math import sqrt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "f1.db"
FIG_DIR = ROOT / "reports" / "figures"
SUMMARY = ROOT / "reports" / "stats_summary.txt"
FIG_DIR.mkdir(parents=True, exist_ok=True)

MIN_CIRCUIT_RACES = 8
N_SIM = 20000
rng = np.random.default_rng(42)
out = []


def note(text=""):
    print(text)
    out.append(str(text))


def wilson(k, n, z=1.96):
    """Interval kepercayaan 95% untuk proporsi (metode Wilson), hasil dalam persen."""
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - a) / d * 100), min(100.0, (c + a) / d * 100)


def interpret(p, what):
    if p < 0.05:
        return f"Tafsir: p < 0.05, ada bukti statistik bahwa {what} bukan sekadar kebetulan (cek juga ukuran selisihnya)."
    return (f"Tafsir: p >= 0.05, {what} belum cukup kuat untuk dibedakan dari kebetulan "
            "(bukan berarti tidak ada perbedaan, bisa jadi sampelnya terlalu kecil).")


with sqlite3.connect(DB_PATH) as conn:
    df = pd.read_sql_query("SELECT * FROM results", conn)

pole = df[df["grid"] == 1].copy()
last_season = int(df["season"].max())

# ---------- 1. Keseluruhan & per posisi start ----------
note("=== 1. PELUANG MENANG PER POSISI START (dengan interval kepercayaan 95%) ===")
for g in (1, 2, 3):
    sub = df[df["grid"] == g]
    n, k = len(sub), int(sub["win"].sum())
    if n == 0:
        continue
    lo, hi = wilson(k, n)
    note(f"Start P{g}: menang {100 * k / n:.1f}% (95% CI {lo:.1f}-{hi:.1f}%), n={n}")

# ---------- 2. Antar sirkuit ----------
circ = (
    pole.groupby("circuit_id")
    .agg(circuit=("circuit_name", "max"), n=("win", "size"), k=("win", "sum"))
)
circ = circ[circ["n"] >= MIN_CIRCUIT_RACES].copy()
circ["pct"] = 100 * circ["k"] / circ["n"]
circ[["lo", "hi"]] = [wilson(k, n) for k, n in zip(circ["k"], circ["n"])]
circ = circ.sort_values("pct")

pooled = circ["k"].sum() / circ["n"].sum()
table = np.column_stack([circ["k"], circ["n"] - circ["k"]])
chi2, p_chi, dof, _ = stats.chi2_contingency(table)

# Uji simulasi (tidak bergantung pada asumsi chi-square untuk sampel kecil)
ns = circ["n"].to_numpy()
obs_spread = np.std(circ["k"].to_numpy() / ns)
sim = np.array([np.std(rng.binomial(ns, pooled) / ns) for _ in range(N_SIM)])
p_sim = float(np.mean(sim >= obs_spread))

note(f"\n=== 2. ANTAR SIRKUIT ({len(circ)} sirkuit, minimal {MIN_CIRCUIT_RACES} balapan) ===")
note(f"Rata-rata gabungan: {100 * pooled:.1f}%")
note(f"Chi-square homogenitas: chi2={chi2:.2f}, dof={dof}, p={p_chi:.3f}")
note(f"Uji simulasi         : p={p_sim:.3f}")
note(interpret(min(p_chi, p_sim), "perbedaan antar sirkuit"))
top, bot = circ.iloc[-1], circ.iloc[0]
note(f"Tertinggi: {top['circuit']} {top['pct']:.0f}% (CI {top['lo']:.0f}-{top['hi']:.0f}%, n={top['n']})")
note(f"Terendah : {bot['circuit']} {bot['pct']:.0f}% (CI {bot['lo']:.0f}-{bot['hi']:.0f}%, n={bot['n']})")

fig, ax = plt.subplots(figsize=(9, max(4, 0.32 * len(circ))))
y = np.arange(len(circ))
ax.errorbar(circ["pct"], y, xerr=[circ["pct"] - circ["lo"], circ["hi"] - circ["pct"]],
            fmt="o", color="#c0392b", ecolor="#999999", capsize=3)
ax.axvline(100 * pooled, color="black", linestyle="--", linewidth=1, label=f"Rata-rata gabungan ({100 * pooled:.0f}%)")
ax.set_yticks(y)
ax.set_yticklabels([f"{c} (n={n})" for c, n in zip(circ["circuit"], circ["n"])])
ax.set_xlim(0, 100)
ax.set_xlabel("Persen menang dari P1 (titik) dan interval kepercayaan 95% (garis)")
ax.set_title("Perbedaan antar sirkuit: sebagian besar interval saling tumpang tindih")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(FIG_DIR / "06_pole_win_ci_by_circuit.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------- 3. Antar musim (tanpa musim berjalan) ----------
season = (
    pole[pole["season"] < last_season]
    .groupby("season").agg(n=("win", "size"), k=("win", "sum"))
)
table_s = np.column_stack([season["k"], season["n"] - season["k"]])
chi2_s, p_s, dof_s, _ = stats.chi2_contingency(table_s)
slope = stats.linregress(season.index, 100 * season["k"] / season["n"])

note(f"\n=== 3. ANTAR MUSIM ({season.index.min()}-{season.index.max()}, musim {last_season} tidak dihitung karena belum lengkap) ===")
note(f"Chi-square homogenitas: chi2={chi2_s:.2f}, dof={dof_s}, p={p_s:.3f}")
note(f"Tren linear: {slope.slope:+.2f} poin persen per tahun (p={slope.pvalue:.3f})")
note(interpret(p_s, "perbedaan antar musim"))

SUMMARY.write_text("\n".join(out), encoding="utf-8")
print(f"\nTersimpan: {SUMMARY}")
