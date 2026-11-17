"""
Langkah 1: Ambil data hasil balapan & kualifikasi F1 dari Jolpica API
(pengganti Ergast) lalu simpan sebagai CSV.

Cara pakai (dari folder utama project):
    python src/01_fetch_data.py

Output:
    data/raw/        -> cache JSON mentah (supaya tidak request ulang)
    data/processed/results.csv
    data/processed/qualifying.csv
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.jolpi.ca/ergast/f1"
START_SEASON = 2010
END_SEASON = 2026          # musim berjalan akan terambil sebagian
PAGE_LIMIT = 100           # maksimal per request
SLEEP_SECONDS = 0.5        # jaga batas request (4/detik, 500/jam)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_json(url, params, retries=5):
    """GET dengan retry sederhana kalau kena rate limit (429) atau error server."""
    for attempt in range(retries):
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 500, 502, 503, 504):
            wait = 5 * (attempt + 1)
            print(f"  status {resp.status_code}, tunggu {wait} detik lalu coba lagi...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
    raise RuntimeError(f"Gagal mengambil {url} setelah {retries} percobaan")


def fetch_season(season, endpoint):
    """Ambil semua halaman data satu musim, dengan cache di data/raw/."""
    cache_file = RAW_DIR / f"{endpoint}_{season}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    url = f"{BASE_URL}/{season}/{endpoint}.json"
    races = {}  # key: round -> data balapan (hasil digabung antar halaman)
    offset = 0
    while True:
        data = get_json(url, {"limit": PAGE_LIMIT, "offset": offset})
        mr = data["MRData"]
        total = int(mr["total"])
        for race in mr["RaceTable"]["Races"]:
            rnd = race["round"]
            if rnd not in races:
                races[rnd] = race
            else:
                for key in ("Results", "QualifyingResults"):
                    if key in race:
                        races[rnd].setdefault(key, []).extend(race[key])
        offset += PAGE_LIMIT
        time.sleep(SLEEP_SECONDS)
        if offset >= total:
            break

    result = list(races.values())
    cache_file.write_text(json.dumps(result), encoding="utf-8")
    return result


def flatten_results(races):
    rows = []
    for race in races:
        for r in race.get("Results", []):
            rows.append({
                "season": int(race["season"]),
                "round": int(race["round"]),
                "race_name": race["raceName"],
                "circuit_id": race["Circuit"]["circuitId"],
                "circuit_name": race["Circuit"]["circuitName"],
                "country": race["Circuit"]["Location"]["country"],
                "date": race["date"],
                "driver_id": r["Driver"]["driverId"],
                "driver": f'{r["Driver"]["givenName"]} {r["Driver"]["familyName"]}',
                "constructor": r["Constructor"]["name"],
                "grid": int(r["grid"]),
                "position": int(r["position"]) if r["position"].isdigit() else None,
                "position_text": r["positionText"],
                "points": float(r["points"]),
                "laps": int(r["laps"]),
                "status": r["status"],
            })
    return rows


def flatten_qualifying(races):
    rows = []
    for race in races:
        for q in race.get("QualifyingResults", []):
            rows.append({
                "season": int(race["season"]),
                "round": int(race["round"]),
                "race_name": race["raceName"],
                "driver_id": q["Driver"]["driverId"],
                "driver": f'{q["Driver"]["givenName"]} {q["Driver"]["familyName"]}',
                "constructor": q["Constructor"]["name"],
                "quali_position": int(q["position"]),
                "q1": q.get("Q1"),
                "q2": q.get("Q2"),
                "q3": q.get("Q3"),
            })
    return rows


def main():
    results_rows, quali_rows = [], []
    for season in range(START_SEASON, END_SEASON + 1):
        print(f"Musim {season}...")
        results_rows += flatten_results(fetch_season(season, "results"))
        quali_rows += flatten_qualifying(fetch_season(season, "qualifying"))

    results = pd.DataFrame(results_rows)
    quali = pd.DataFrame(quali_rows)
    results.to_csv(OUT_DIR / "results.csv", index=False)
    quali.to_csv(OUT_DIR / "qualifying.csv", index=False)

    print("\nSelesai!")
    print(f"results.csv    : {results.shape[0]} baris, {results.shape[1]} kolom")
    print(f"qualifying.csv : {quali.shape[0]} baris, {quali.shape[1]} kolom")
    print(results.head())


if __name__ == "__main__":
    main()
