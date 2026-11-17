"""
Langkah 3: Masukkan data bersih ke database SQLite, lalu jalankan query SQL.

Cara pakai (dari folder utama project):
    python src/03_load_to_sqlite.py

Input : data/processed/results_clean.csv, data/processed/qualifying.csv
        sql/queries.sql
Output: data/f1.db
        reports/sql_results.txt  (hasil semua query)
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "f1.db"
SQL_FILE = ROOT / "sql" / "queries.sql"
OUT_FILE = ROOT / "reports" / "sql_results.txt"
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# ---------- 1. Muat CSV ke database ----------
results = pd.read_csv(DATA / "results_clean.csv")
quali = pd.read_csv(DATA / "qualifying.csv")

with sqlite3.connect(DB_PATH) as conn:
    results.to_sql("results", conn, if_exists="replace", index=False)
    quali.to_sql("qualifying", conn, if_exists="replace", index=False)

    # Index supaya query lebih cepat
    conn.execute("CREATE INDEX IF NOT EXISTS idx_results_race ON results(season, round)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_results_grid ON results(grid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_results_circuit ON results(circuit_id)")
    conn.commit()

    print(f"Database dibuat: {DB_PATH}")
    for table in ("results", "qualifying"):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  tabel {table}: {n} baris")

    # ---------- 2. Jalankan query dari sql/queries.sql ----------
    text = SQL_FILE.read_text(encoding="utf-8")
    # Pecah berdasarkan penanda "-- Q<angka>: judul"
    parts = re.split(r"^-- (Q\d+: .*)$", text, flags=re.MULTILINE)
    # parts = [sebelum, judul1, isi1, judul2, isi2, ...]
    output = []
    for title, query in zip(parts[1::2], parts[2::2]):
        df = pd.read_sql_query(query.strip().rstrip(";"), conn)
        block = f"\n=== {title} ===\n{df.to_string(index=False)}\n"
        print(block)
        output.append(block)

OUT_FILE.write_text("".join(output), encoding="utf-8")
print(f"Hasil query disimpan di: {OUT_FILE}")
