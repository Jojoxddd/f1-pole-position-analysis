"""
Langkah 4: Analisis eksploratif (EDA) dan visualisasi.

Cara pakai (dari folder utama project):
    python src/04_eda_charts.py

Input : data/f1.db  (dibuat oleh 03_load_to_sqlite.py)
Output: reports/figures/*.png
        reports/eda_summary.txt  (ringkasan angka utama)
"""
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # simpan gambar tanpa membuka jendela
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "f1.db"
FIG_DIR = ROOT / "reports" / "figures"
SUMMARY = ROOT / "reports" / "eda_summary.txt"
FIG_DIR.mkdir(parents=True, exist_ok=True)

MIN_CIRCUIT_RACES = 8
sns.set_theme(style="whitegrid", context="notebook")

with sqlite3.connect(DB_PATH) as conn:
    df = pd.read_sql_query("SELECT * FROM results", conn)

# Musim terakhir kemungkinan belum lengkap -> ditandai di grafik tren
last_season = int(df["season"].max())
summary = []


def note(text=""):
    print(text)
    summary.append(str(text))


def save(fig, name):
    path = FIG_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  tersimpan: {path.name}")


# ---------- Grafik 1 & 2: peluang menang dan podium per posisi start ----------
grid_stats = (
    df[df["grid"].between(1, 10)]
    .groupby("grid")
    .agg(starts=("win", "size"), wins=("win", "sum"), podiums=("podium", "sum"), dnf=("dnf", "sum"))
)
grid_stats["win_pct"] = 100 * grid_stats["wins"] / grid_stats["starts"]
grid_stats["podium_pct"] = 100 * grid_stats["podiums"] / grid_stats["starts"]
grid_stats["dnf_pct"] = 100 * grid_stats["dnf"] / grid_stats["starts"]

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
for ax, col, title in (
    (axes[0], "win_pct", "Peluang menang berdasarkan posisi start"),
    (axes[1], "podium_pct", "Peluang podium berdasarkan posisi start"),
):
    sns.barplot(x=grid_stats.index, y=grid_stats[col], color="#c0392b", ax=ax)
    ax.set_title(title)
    ax.set_xlabel("Posisi start (grid)")
    ax.set_ylabel("Persen (%)")
    for i, v in enumerate(grid_stats[col]):
        ax.text(i, v + 0.6, f"{v:.0f}%", ha="center", fontsize=8)
fig.suptitle(f"Formula 1 {df['season'].min()}-{last_season}: pengaruh posisi start", y=1.02)
save(fig, "01_win_podium_by_grid.png")

# ---------- Grafik 3: rata-rata posisi naik per posisi start ----------
gain = (
    df[(df["finished"] == 1) & df["grid"].between(1, 20)]
    .groupby("grid")["positions_gained"].mean()
)
fig, ax = plt.subplots(figsize=(9, 4.5))
colors = ["#2e86c1" if v >= 0 else "#c0392b" for v in gain.values]
ax.bar(gain.index, gain.values, color=colors)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_title("Rata-rata posisi yang didapat/hilang dibanding posisi start (hanya yang finish)")
ax.set_xlabel("Posisi start (grid)")
ax.set_ylabel("Posisi naik (+) / turun (-)")
ax.set_xticks(range(1, 21))
save(fig, "02_positions_gained_by_grid.png")

# ---------- Grafik 4: tren pole -> menang per musim ----------
pole = df[df["grid"] == 1]
season_stats = pole.groupby("season").agg(races=("win", "size"), wins=("win", "sum"))
season_stats["pct"] = 100 * season_stats["wins"] / season_stats["races"]

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(season_stats.index, season_stats["pct"], marker="o", color="#c0392b")
if last_season in season_stats.index:
    ax.plot(last_season, season_stats.loc[last_season, "pct"], marker="o",
            markerfacecolor="white", markeredgecolor="#c0392b", markersize=10)
    ax.annotate("musim berjalan\n(belum lengkap)", (last_season, season_stats.loc[last_season, "pct"]),
                textcoords="offset points", xytext=(-10, -35), ha="center", fontsize=8)
ax.set_ylim(0, 100)
ax.set_xticks(season_stats.index)
ax.tick_params(axis="x", rotation=45)
ax.set_title("Persentase balapan yang dimenangkan pembalap start P1, per musim")
ax.set_xlabel("Musim")
ax.set_ylabel("Persen (%)")
save(fig, "03_pole_win_pct_by_season.png")

# ---------- Grafik 5: pole -> menang per sirkuit ----------
circ = (
    pole.groupby("circuit_id")
    .agg(circuit=("circuit_name", "max"), races=("win", "size"), wins=("win", "sum"))
)
circ = circ[circ["races"] >= MIN_CIRCUIT_RACES].copy()
circ["pct"] = 100 * circ["wins"] / circ["races"]
circ = circ.sort_values("pct")
if len(circ):
    fig, ax = plt.subplots(figsize=(9, max(4, 0.32 * len(circ))))
    ax.barh(circ["circuit"], circ["pct"], color="#c0392b")
    for y, (pct, n) in enumerate(zip(circ["pct"], circ["races"])):
        ax.text(pct + 1, y, f"{pct:.0f}% (n={n})", va="center", fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_title(f"Persen menang dari P1 per sirkuit (minimal {MIN_CIRCUIT_RACES} balapan)")
    ax.set_xlabel("Persen (%)")
    save(fig, "04_pole_win_pct_by_circuit.png")
else:
    print(f"  (grafik sirkuit dilewati: belum ada sirkuit dengan >= {MIN_CIRCUIT_RACES} balapan)")

# ---------- Grafik 6: heatmap posisi start vs posisi finis ----------
hm = df[df["classified"] == 1]
hm = hm[hm["grid"].between(1, 20) & hm["position"].between(1, 20)]
table = pd.crosstab(hm["grid"], hm["position"], normalize="index") * 100
fig, ax = plt.subplots(figsize=(10, 7))
sns.heatmap(table, cmap="Reds", ax=ax, cbar_kws={"label": "% dari pembalap di posisi start tsb"})
ax.set_title("Dari posisi start tertentu, di mana mereka finis? (hanya yang diklasifikasikan)")
ax.set_xlabel("Posisi finis")
ax.set_ylabel("Posisi start (grid)")
save(fig, "05_heatmap_grid_vs_finish.png")

# ---------- Ringkasan angka utama ----------
note("\n=== RINGKASAN ANGKA UTAMA ===")
note(f"Periode: {df['season'].min()} - {last_season} ({df.groupby(['season', 'round']).ngroups} balapan)")
note(f"Menang dari P1 : {pole['win'].mean() * 100:.1f}% ({int(pole['win'].sum())} dari {len(pole)})")
note(f"Podium dari P1 : {pole['podium'].mean() * 100:.1f}%")
for g in (1, 2, 3):
    if g in grid_stats.index:
        note(f"Start P{g}: menang {grid_stats.loc[g, 'win_pct']:.1f}%, podium {grid_stats.loc[g, 'podium_pct']:.1f}%, DNF {grid_stats.loc[g, 'dnf_pct']:.1f}%")
if len(circ):
    top, bot = circ.iloc[-1], circ.iloc[0]
    note(f"Sirkuit dengan P1 paling sering menang : {top['circuit']} ({top['pct']:.0f}%, n={top['races']})")
    note(f"Sirkuit dengan P1 paling jarang menang : {bot['circuit']} ({bot['pct']:.0f}%, n={bot['races']})")
full = season_stats.drop(index=last_season, errors="ignore")
if len(full):
    note(f"Musim lengkap tertinggi: {int(full['pct'].idxmax())} ({full['pct'].max():.0f}%), terendah: {int(full['pct'].idxmin())} ({full['pct'].min():.0f}%)")

SUMMARY.write_text("\n".join(summary), encoding="utf-8")
print(f"\nRingkasan disimpan di: {SUMMARY}")
