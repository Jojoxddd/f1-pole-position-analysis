"""
Langkah 2: Bersihkan data & buat kolom turunan.

Cara pakai (dari folder utama project):
    python src/02_clean_data.py

Input : data/processed/results.csv, data/processed/qualifying.csv
Output: data/processed/results_clean.csv
        reports/data_quality_report.txt
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "data_quality_report.txt"
REPORT.parent.mkdir(parents=True, exist_ok=True)

lines = []


def log(text=""):
    print(text)
    lines.append(str(text))


# ---------- 1. Muat data ----------
results = pd.read_csv(IN_DIR / "results.csv")
quali = pd.read_csv(IN_DIR / "qualifying.csv")

log("=== 1. UKURAN DATA ===")
log(f"results   : {results.shape[0]} baris, {results.shape[1]} kolom")
log(f"qualifying: {quali.shape[0]} baris, {quali.shape[1]} kolom")
log(f"Musim     : {results['season'].min()} - {results['season'].max()}")
log(f"Jumlah balapan: {results.groupby(['season', 'round']).ngroups}")

# ---------- 2. Cek kualitas ----------
log("\n=== 2. NILAI KOSONG (results) ===")
log(results.isna().sum()[lambda s: s > 0].to_string() or "Tidak ada nilai kosong")

dup = results.duplicated(subset=["season", "round", "driver_id"]).sum()
log(f"\nBaris duplikat (musim+ronde+pembalap): {dup}")
results = results.drop_duplicates(subset=["season", "round", "driver_id"])

log("\nBalapan per musim (cek apakah ada musim yang janggal):")
log(results.groupby("season")["round"].nunique().to_string())

# ---------- 3. Kolom turunan ----------
# position_text berisi angka untuk pembalap yang diklasifikasikan, dan huruf
# (R, D, E, W, F, N) untuk yang tidak finis / didiskualifikasi dll.
results["classified"] = results["position_text"].astype(str).str.isdigit()

# Finish vs DNF dari kolom status.
# "Finished", "+1 Lap", "+2 Laps", ... dan "Lapped" = menyelesaikan balapan.
status = results["status"].astype(str)
results["finished"] = (
    (status == "Finished") | status.str.startswith("+") | (status == "Lapped")
)
results["dnf"] = ~results["finished"]

# grid = 0 artinya start dari pit lane. Anggap start di belakang grid.
results["pit_lane_start"] = results["grid"] == 0
max_grid = results.groupby(["season", "round"])["grid"].transform("max")
results["grid_adj"] = results["grid"].where(results["grid"] > 0, max_grid + 1)

results["pole"] = results["grid"] == 1
results["win"] = results["position"] == 1
results["podium"] = results["position"] <= 3
# Selisih posisi: positif = naik posisi dari start. Hanya untuk yang finish.
results["positions_gained"] = (results["grid_adj"] - results["position"]).where(results["finished"])

# ---------- 4. Gabung data kualifikasi ----------
q = quali[["season", "round", "driver_id", "quali_position"]].drop_duplicates(
    subset=["season", "round", "driver_id"]
)
results = results.merge(q, on=["season", "round", "driver_id"], how="left")
no_quali = results["quali_position"].isna().sum()
log(f"\n=== 3. GABUNG KUALIFIKASI ===\nBaris tanpa data kualifikasi: {no_quali}")
if no_quali:
    log("Rincian per musim:")
    log(results[results["quali_position"].isna()].groupby("season").size().to_string())
    log("Contoh baris tanpa kualifikasi:")
    log(results[results["quali_position"].isna()][
        ["season", "round", "driver", "constructor", "grid", "position", "status"]
    ].head(15).to_string())

# ---------- 5. Ringkasan hasil bersih ----------
log("\n=== 4. RINGKASAN HASIL BERSIH ===")
log(f"Total baris        : {len(results)}")
log(f"Finish / DNF       : {results['finished'].sum()} / {results['dnf'].sum()}")
log(f"Start dari pit lane: {results['pit_lane_start'].sum()}")
winners_per_race = results[results["win"]].groupby(["season", "round"]).size()
log(f"Balapan dengan tepat 1 pemenang: {(winners_per_race == 1).sum()} dari {results.groupby(['season', 'round']).ngroups}")
log("\nSemua status beserta klasifikasinya (finish/DNF):")
status_table = (
    results.groupby("status")["finished"].agg(jumlah="size", finish="first")
    .sort_values("jumlah", ascending=False)
)
log(status_table.to_string())
log("\nContoh 5 baris:")
log(results[["season", "round", "driver", "grid", "grid_adj", "position", "finished", "positions_gained"]].head().to_string())

# ---------- 6. Simpan ----------
results.to_csv(IN_DIR / "results_clean.csv", index=False)
REPORT.write_text("\n".join(lines), encoding="utf-8")
log(f"\nTersimpan: {IN_DIR / 'results_clean.csv'}")
log(f"Laporan  : {REPORT}")
