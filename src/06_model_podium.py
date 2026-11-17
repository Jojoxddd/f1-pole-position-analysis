"""
Langkah 7: Model prediksi podium (3 besar).

Pertanyaan: dengan informasi yang sudah diketahui SEBELUM balapan dimulai,
seberapa baik kita bisa menebak siapa yang naik podium?

Cara pakai (dari folder utama project):
    pip install scikit-learn
    python src/06_model_podium.py

Input : data/processed/results_clean.csv
Output: reports/model_summary.txt
        reports/figures/07_model_comparison.png
        reports/figures/08_feature_importance.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed" / "results_clean.csv"
REPORT = ROOT / "reports" / "model_summary.txt"
FIG_DIR = ROOT / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_UNTIL = 2022      # latih pada musim <= 2022, uji pada musim sesudahnya
FORM_WINDOW = 5         # "performa terkini" = rata-rata 5 balapan terakhir
SEED = 42

lines = []


def log(text=""):
    print(text)
    lines.append(str(text))


# ====================================================================
# 1. SIAPKAN DATA
# ====================================================================
df = pd.read_csv(DATA)
df = df.sort_values(["season", "round"]).reset_index(drop=True)
df["podium"] = df["podium"].astype(int)
df["win"] = df["win"].astype(int)

# ====================================================================
# 2. BUAT FITUR (hanya dari informasi SEBELUM balapan)
# ====================================================================
# PENTING: .shift(1) membuat setiap baris hanya melihat balapan SEBELUMNYA.
# Tanpa shift, model "mengintip" hasil balapan yang sedang diprediksi
# (disebut data leakage) dan hasilnya jadi terlalu bagus untuk jadi nyata.

# Performa pembalap: rata-rata poin 5 balapan terakhir
df["driver_form_pts"] = df.groupby("driver_id")["points"].transform(
    lambda s: s.shift(1).rolling(FORM_WINDOW, min_periods=1).mean()
)

# Performa tim: rata-rata total poin tim di 5 balapan terakhir
team = (
    df.groupby(["constructor", "season", "round"], as_index=False)["points"].sum()
    .sort_values(["constructor", "season", "round"])
)
team["team_form_pts"] = team.groupby("constructor")["points"].transform(
    lambda s: s.shift(1).rolling(FORM_WINDOW, min_periods=1).mean()
)
df = df.merge(team[["constructor", "season", "round", "team_form_pts"]],
              on=["constructor", "season", "round"], how="left")

# Peringkat performa di dalam satu balapan (1 = paling bagus saat itu)
race_key = ["season", "round"]
df["driver_form_rank"] = df.groupby(race_key)["driver_form_pts"].rank(ascending=False, method="min")
df["team_form_rank"] = df.groupby(race_key)["team_form_pts"].rank(ascending=False, method="min")

FEATURES = ["grid_adj", "team_form_pts", "team_form_rank", "driver_form_pts", "driver_form_rank"]
TARGET = "podium"

# ====================================================================
# 3. BAGI DATA BERDASARKAN WAKTU
# ====================================================================
# Latih pada masa lalu, uji pada masa depan. Tidak diacak, karena di dunia nyata
# kita memang memprediksi balapan yang belum terjadi.
train = df[df["season"] <= TRAIN_UNTIL]
test = df[df["season"] > TRAIN_UNTIL].reset_index(drop=True)
log("=== 1. DATA ===")
log(f"Latih : musim {train['season'].min()}-{train['season'].max()} "
    f"({train.groupby(race_key).ngroups} balapan, {len(train)} baris)")
log(f"Uji   : musim {test['season'].min()}-{test['season'].max()} "
    f"({test.groupby(race_key).ngroups} balapan, {len(test)} baris)")
log(f"Proporsi podium di data uji: {test[TARGET].mean() * 100:.1f}% (3 dari sekitar 20 pembalap)")
log(f"Fitur : {FEATURES}")


# ====================================================================
# 4. METRIK
# ====================================================================
def race_metrics(frame, score):
    """Untuk tiap balapan, ambil 3 pembalap dengan skor tertinggi sebagai tebakan podium."""
    t = frame[race_key + [TARGET, "win"]].copy()
    t["score"] = np.asarray(score)
    t["rank"] = t.groupby(race_key)["score"].rank(ascending=False, method="first")
    top3 = t[t["rank"] <= 3].groupby(race_key)[TARGET].sum()
    winner_ok = t[t["rank"] == 1]["win"].mean()
    return top3.mean(), (top3 == 3).mean(), winner_ok


results = []


def evaluate(name, score, prob=None):
    avg_hit, exact, winner = race_metrics(test, score)
    row = {
        "Model": name,
        "Podium benar per balapan (dari 3)": avg_hit,
        "Podium persis benar (%)": exact * 100,
        "Pemenang benar (%)": winner * 100,
        "ROC AUC": roc_auc_score(test[TARGET], score),
        "Average precision": average_precision_score(test[TARGET], score),
        "Log loss": log_loss(test[TARGET], prob) if prob is not None else np.nan,
    }
    results.append(row)


# ====================================================================
# 5. MODEL
# ====================================================================
# (a) Pembanding paling sederhana: tebak podium = 3 pembalap yang start paling depan.
evaluate("A. Aturan: 3 start terdepan", -test["grid_adj"])

# (b) Regresi logistik, hanya posisi start
lr_grid = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=1000))
lr_grid.fit(train[["grid_adj"]], train[TARGET])
p = lr_grid.predict_proba(test[["grid_adj"]])[:, 1]
evaluate("B. Regresi logistik (posisi start saja)", p, p)

# (c) Regresi logistik, semua fitur
lr_all = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=1000))
lr_all.fit(train[FEATURES], train[TARGET])
p = lr_all.predict_proba(test[FEATURES])[:, 1]
evaluate("C. Regresi logistik (semua fitur)", p, p)

# (d) Gradient boosting, semua fitur (model yang bisa menangkap pola tidak linear)
gb = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, random_state=SEED)
gb.fit(train[FEATURES], train[TARGET])
p = gb.predict_proba(test[FEATURES])[:, 1]
evaluate("D. Gradient boosting (semua fitur)", p, p)

res = pd.DataFrame(results)
log("\n=== 2. PERBANDINGAN MODEL (pada data uji) ===")
log(res.round(2).to_string(index=False))
log(
    "\nCara membaca: 'Podium benar per balapan' adalah rata-rata berapa dari 3 tebakan yang tepat "
    "(0 sampai 3). Tebakan acak kira-kira 0,45; sempurna adalah 3."
)

best = res.iloc[res["Podium benar per balapan (dari 3)"].idxmax()]
base = res.iloc[0]
diff = best["Podium benar per balapan (dari 3)"] - base["Podium benar per balapan (dari 3)"]
log(f"\nModel terbaik menurut 'podium benar per balapan': {best['Model']}")
log(f"Selisih dibanding aturan 'start terdepan': {diff:+.2f} dari 3 per balapan")

# ====================================================================
# 6. FITUR MANA YANG PALING BERPENGARUH?
# ====================================================================
imp = permutation_importance(gb, test[FEATURES], test[TARGET], scoring="roc_auc",
                             n_repeats=10, random_state=SEED)
imp_df = pd.DataFrame({"fitur": FEATURES, "penurunan_auc": imp.importances_mean,
                       "std": imp.importances_std}).sort_values("penurunan_auc")
log("\n=== 3. PENTINGNYA FITUR (gradient boosting) ===")
log("Angka = seberapa turun ROC AUC jika fitur itu diacak. Makin besar = makin penting.")
log(imp_df.sort_values("penurunan_auc", ascending=False).round(3).to_string(index=False))

# ====================================================================
# 7. GRAFIK
# ====================================================================
fig, ax = plt.subplots(figsize=(8, 4))
labels = [m.split(". ", 1)[1] for m in res["Model"]]
colors = ["#9aa0a6"] + ["#1f4e79"] * (len(res) - 1)
ax.barh(labels[::-1], res["Podium benar per balapan (dari 3)"][::-1], color=colors[::-1])
for y, v in enumerate(res["Podium benar per balapan (dari 3)"][::-1]):
    ax.text(v + 0.02, y, f"{v:.2f}", va="center", fontsize=9)
ax.set_xlim(0, 3)
ax.set_xlabel("Rata-rata tebakan podium yang benar per balapan (maks. 3)")
ax.set_title("Perbandingan model pada data uji")
fig.tight_layout()
fig.savefig(FIG_DIR / "07_model_comparison.png", dpi=150, bbox_inches="tight")
plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 3.5))
ax.barh(imp_df["fitur"], imp_df["penurunan_auc"], xerr=imp_df["std"], color="#1f4e79", ecolor="#9aa0a6")
ax.set_xlabel("Penurunan ROC AUC jika fitur diacak")
ax.set_title("Fitur yang paling berpengaruh")
fig.tight_layout()
fig.savefig(FIG_DIR / "08_feature_importance.png", dpi=150, bbox_inches="tight")
plt.close(fig)

REPORT.write_text("\n".join(lines), encoding="utf-8")
log(f"\nTersimpan: {REPORT}")
