"""
Dashboard: Seberapa besar peluang menang dari pole position di Formula 1?

Jalankan dari folder utama project:
    python -m streamlit run app.py
"""
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Peluang Menang dari Pole Position - Formula 1", layout="wide")

DATA_FILE = Path(__file__).parent / "data" / "processed" / "results_clean.csv"
BLUE = "#1f4e79"
LIGHT = "#b9c7d8"
GREY = "#9aa0a6"
BOOL_COLS = ["classified", "finished", "dnf", "pit_lane_start", "pole", "win", "podium"]


# ---------------------------------------------------------------- data
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_FILE)
    for col in BOOL_COLS:
        df[col] = df[col].astype(int)
    latest = df.sort_values(["season", "round"]).groupby("circuit_id")["circuit_name"].last()
    df["circuit"] = df["circuit_id"].map(latest)
    return df


def wilson(k, n, z=1.96):
    """Interval kepercayaan 95% (Wilson) untuk proporsi, dalam persen."""
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = k / n
        d = 1 + z * z / n
        c = p + z * z / (2 * n)
        a = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        lo, hi = (c - a) / d * 100, (c + a) / d * 100
    return np.clip(lo, 0, 100), np.clip(hi, 0, 100)


@st.cache_data
def spread_pvalue(ns, ks, n_sim=20000, seed=42):
    """Uji simulasi: apakah variasi antar kelompok lebih besar dari yang wajar karena kebetulan?"""
    ns = np.array(ns, dtype=float)
    ks = np.array(ks, dtype=float)
    pooled = ks.sum() / ns.sum()
    observed = np.std(ks / ns)
    rng = np.random.default_rng(seed)
    sims = np.array([np.std(rng.binomial(ns.astype(int), pooled) / ns) for _ in range(n_sim)])
    return float(np.mean(sims >= observed))


def style(chart):
    return (
        chart.configure_view(strokeWidth=0)
        .configure_axis(gridColor="#e5e7eb", labelFontSize=12, titleFontSize=12, domainColor="#9aa0a6")
        .configure_legend(labelFontSize=12, titleFontSize=12)
    )


def per_10(x):
    """Ubah proporsi jadi kalimat 'sekitar N dari 10'."""
    return int(round(x * 10))


st.markdown(
    """
    <style>
    .block-container { padding-top: 2.2rem; max-width: 1100px; }
    h1 { font-size: 2.2rem !important; line-height: 1.25 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

df = load_data()
smin, smax = int(df["season"].min()), int(df["season"].max())
races_per_season = df.groupby("season")["round"].nunique()
partial_season = smax if races_per_season[smax] < races_per_season.max() else None

# ================================================================ 1. PEMBUKA
st.title("Seberapa Besar Peluang Menang dari Pole Position?")
st.markdown(
    "Di Formula 1, pembalap yang start paling depan sering dianggap hampir pasti menang. "
    "**Benarkah begitu?** Saya memeriksa hasil balapan Formula 1 dari "
    f"{smin} sampai {smax} untuk mencari jawabannya, dan hasilnya bisa kamu utak-atik sendiri di halaman ini."
)

with st.expander("Belum familiar dengan istilahnya? Klik di sini"):
    st.markdown(
        "- **Posisi start (grid):** urutan mobil di garis start, ditentukan dari kualifikasi. "
        "Posisi 1 disebut *pole position*.\n"
        "- **Podium:** finis di posisi 1, 2, atau 3.\n"
        "- **Gagal finis (DNF):** tidak menyelesaikan balapan, misalnya karena mogok atau kecelakaan. "
        "Pembalap yang finis tapi tertinggal satu lap atau lebih tetap dihitung finis."
    )

with st.expander("Ingin melihat periode, sirkuit, atau tim tertentu? (opsional)"):
    fc1, fc2, fc3 = st.columns(3)
    season_range = fc1.slider("Musim", smin, smax, (smin, smax))
    circuit_sel = fc2.multiselect("Sirkuit (kosong = semua)", sorted(df["circuit"].unique()))
    team_sel = fc3.multiselect("Tim (kosong = semua)", sorted(df["constructor"].unique()))
    show_ci = st.checkbox("Tampilkan rentang ketidakpastian di grafik (untuk yang suka statistik)")

f = df[df["season"].between(*season_range)]
if circuit_sel:
    f = f[f["circuit"].isin(circuit_sel)]
if team_sel:
    f = f[f["constructor"].isin(team_sel)]

if f.empty or f[f["grid"] == 1].empty:
    st.warning("Tidak ada data untuk kombinasi filter ini. Coba lebarkan pilihannya.")
    st.stop()

n_races = f.groupby(["season", "round"]).ngroups
pole = f[f["grid"] == 1]
n_pole = len(pole)
win_rate = pole["win"].mean()
podium_rate = pole["podium"].mean()
total_wins = int(f["win"].sum())
front_wins = int(((f["win"] == 1) & f["grid"].between(1, 3)).sum())
back_wins = total_wins - front_wins

st.caption(
    f"Berdasarkan {n_races} balapan, musim {season_range[0]} sampai {season_range[1]}."
    + (f" Musim {partial_season} belum selesai." if partial_season and season_range[1] >= partial_season else "")
)

# ================================================================ 2. JAWABAN SINGKAT
st.header("Jawaban singkatnya")
st.markdown(
    f"### Dari 10 balapan, sekitar **{per_10(win_rate)}** dimenangkan pembalap yang start dari posisi pertama."
)

a, b, c = st.columns(3)
with a, st.container(border=True, height=190):
    st.metric("Menang dari pole", f"{win_rate * 100:.0f}%")
    st.caption(f"{int(pole['win'].sum())} dari {n_pole} balapan.")
with b, st.container(border=True, height=190):
    st.metric("Naik podium dari pole", f"{podium_rate * 100:.0f}%")
    st.caption(f"Sekitar {per_10(podium_rate)} dari 10 pembalap pole finis di tiga besar.")
with c, st.container(border=True, height=190):
    share = front_wins / total_wins * 100 if total_wins else 0
    st.metric("Kemenangan dari 3 posisi terdepan", f"{share:.0f}%")
    st.caption(f"Hanya {back_wins} dari {total_wins} balapan dimenangkan pembalap yang start di posisi 4 ke belakang.")

st.caption(
    "Catatan: angka ini menunjukkan hubungan, bukan sebab-akibat. Mobil tercepat biasanya start di depan dan juga "
    "menang, jadi pole bukan satu-satunya penyebab kemenangan."
)

# ================================================================ 3. COBA SENDIRI
st.header("Coba sendiri: bagaimana kalau start dari posisi lain?")
sel = st.slider("Pilih posisi start", 1, 20, 1)
sub = f[f["grid"] == sel]
if sub.empty:
    st.info("Belum ada data untuk posisi start ini dengan filter yang dipilih.")
else:
    n_s = len(sub)
    k_s = int(sub["win"].sum())
    st.markdown(
        f"Dari **{n_s}** kali pembalap start di posisi **{sel}**, mereka menang **{k_s}** kali "
        f"(**{k_s / n_s * 100:.0f}%**)."
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Menang", f"{k_s / n_s * 100:.0f}%")
    m2.metric("Naik podium", f"{sub['podium'].mean() * 100:.0f}%")
    m3.metric("Gagal finis (DNF)", f"{sub['dnf'].mean() * 100:.0f}%")
    avg_fin = sub[sub["classified"] == 1]["position"].mean()
    m4.metric("Rata-rata finis", f"P{avg_fin:.1f}" if pd.notna(avg_fin) else "-")

metric_name = st.radio("Tampilkan peluang untuk", ["Menang", "Podium", "Gagal finis"], horizontal=True)
metric_col = {"Menang": "win", "Podium": "podium", "Gagal finis": "dnf"}[metric_name]
upto = max(10, sel)
g = (
    f[f["grid"].between(1, upto)]
    .groupby("grid")
    .agg(starts=("win", "size"), k=(metric_col, "sum"))
    .reset_index()
)
g["pct"] = 100 * g["k"] / g["starts"]
g["lo"], g["hi"] = wilson(g["k"], g["starts"])
base = alt.Chart(g).encode(x=alt.X("grid:O", title="Posisi start", sort="ascending", axis=alt.Axis(labelAngle=0)))
bars = base.mark_bar().encode(
    y=alt.Y("pct:Q", title=f"Peluang {metric_name.lower()} (%)"),
    color=alt.condition(alt.datum.grid == sel, alt.value(BLUE), alt.value(LIGHT)),
    tooltip=[
        alt.Tooltip("grid:O", title="Posisi start"),
        alt.Tooltip("starts:Q", title="Jumlah start"),
        alt.Tooltip("k:Q", title=metric_name),
        alt.Tooltip("pct:Q", title="Peluang (%)", format=".1f"),
    ],
)
layers = bars + base.mark_rule(color="#444444").encode(y="lo:Q", y2="hi:Q") if show_ci else bars
st.altair_chart(style(layers.properties(width="container", height=320)))
st.caption("Batang berwarna tua adalah posisi yang kamu pilih." + (" Garis hitam menunjukkan rentang ketidakpastian." if show_ci else ""))

# ================================================================ 4. PER SIRKUIT
st.header("Apakah ada sirkuit di mana pole lebih sering menang?")
min_races = st.slider("Hanya tampilkan sirkuit dengan minimal ... balapan", 1, 20, 8,
                      help="Sirkuit dengan sedikit balapan kurang bisa dipercaya, jadi sebaiknya jangan terlalu kecil.")
circ = pole.groupby("circuit").agg(n=("win", "size"), k=("win", "sum")).reset_index()
circ = circ[circ["n"] >= min_races].copy()
if circ.empty:
    st.info("Belum ada sirkuit yang memenuhi syarat. Turunkan batas minimal balapan atau lebarkan filter.")
else:
    circ["pct"] = 100 * circ["k"] / circ["n"]
    circ["lo"], circ["hi"] = wilson(circ["k"], circ["n"])
    circ = circ.sort_values("pct", ascending=False)
    order = circ["circuit"].tolist()
    top, bot = circ.iloc[0], circ.iloc[-1]
    st.markdown(
        f"Di **{top['circuit']}**, pembalap pole menang **{top['pct']:.0f}%** ({int(top['k'])} dari {int(top['n'])} balapan). "
        f"Di **{bot['circuit']}**, hanya **{bot['pct']:.0f}%** ({int(bot['k'])} dari {int(bot['n'])})."
    )
    pooled = 100 * circ["k"].sum() / circ["n"].sum()
    y = alt.Y("circuit:N", sort=order, title=None)
    cbars = alt.Chart(circ).mark_bar(color=BLUE).encode(
        y=y, x=alt.X("pct:Q", title="Pole menang (%)", scale=alt.Scale(domain=[0, 100])),
        tooltip=[
            alt.Tooltip("circuit:N", title="Sirkuit"),
            alt.Tooltip("n:Q", title="Jumlah balapan"),
            alt.Tooltip("k:Q", title="Pole menang"),
            alt.Tooltip("pct:Q", title="Persen", format=".1f"),
        ],
    )
    avg = alt.Chart(pd.DataFrame({"x": [pooled]})).mark_rule(strokeDash=[5, 4], color="#333333").encode(x="x:Q")
    clayers = cbars + avg
    if show_ci:
        clayers = clayers + alt.Chart(circ).mark_rule(color="#444444").encode(y=y, x="lo:Q", x2="hi:Q")
    st.altair_chart(style(clayers.properties(width="container", height=max(260, 26 * len(circ) + 50))))
    st.warning(
        f"Hati-hati menyimpulkan. Garis putus-putus adalah rata-rata keseluruhan ({pooled:.0f}%). "
        "Tiap sirkuit hanya punya belasan balapan, jadi urutan ini belum bisa dianggap pasti. "
        "Uji statistik menunjukkan perbedaannya masih wajar terjadi karena kebetulan (lihat tab Tentang dan Detail Teknis)."
    )

# ================================================================ 5. PER MUSIM
st.header("Apakah dari tahun ke tahun berubah?")
season = pole.groupby("season").agg(n=("win", "size"), k=("win", "sum")).reset_index()
season["pct"] = 100 * season["k"] / season["n"]
season["lo"], season["hi"] = wilson(season["k"], season["n"])
season["partial"] = season["season"] == partial_season
sbase = alt.Chart(season).encode(x=alt.X("season:O", title="Musim", axis=alt.Axis(labelAngle=-45)))
line = sbase.mark_line(color=BLUE).encode(y=alt.Y("pct:Q", title="Pole menang (%)", scale=alt.Scale(domain=[0, 100])))
points = sbase.mark_point(filled=True, size=80, strokeWidth=2, stroke=BLUE).encode(
    y="pct:Q",
    fill=alt.condition("datum.partial", alt.value("white"), alt.value(BLUE)),
    tooltip=[
        alt.Tooltip("season:O", title="Musim"),
        alt.Tooltip("n:Q", title="Jumlah balapan"),
        alt.Tooltip("k:Q", title="Pole menang"),
        alt.Tooltip("pct:Q", title="Persen", format=".1f"),
    ],
)
slayers = line + points
if show_ci:
    slayers = alt.Chart(season).mark_rule(color="#c8ccd0").encode(
        x=alt.X("season:O"), y="lo:Q", y2="hi:Q") + slayers
st.altair_chart(style(slayers.properties(width="container", height=320)))
cap = "Persen balapan yang dimenangkan pembalap pole di setiap musim. Naik turunnya wajar karena tiap musim hanya punya belasan sampai dua puluhan balapan."
if partial_season and partial_season in season["season"].values:
    cap += f" Titik kosong ({partial_season}) adalah musim yang belum selesai."
st.caption(cap)

# ================================================================ 6. JELAJAH LEBIH DALAM
st.header("Jelajahi lebih dalam")
tab_driver, tab_data, tab_about = st.tabs(["Pembalap", "Tabel data", "Tentang dan detail teknis"])

with tab_driver:
    st.markdown("Statistik pembalap pada periode dan filter yang dipilih.")
    min_drv = st.slider("Minimal jumlah balapan", 1, 100, 20)
    d = f.groupby("driver").agg(
        Balapan=("win", "size"),
        Menang=("win", "sum"),
        Podium=("podium", "sum"),
        Start_pole=("grid", lambda s: int((s == 1).sum())),
        Rata2_grid=("grid_adj", "mean"),
        DNF=("dnf", "mean"),
    )
    d["Rata2_finis"] = f[f["classified"] == 1].groupby("driver")["position"].mean()
    d["DNF"] = d["DNF"] * 100
    d = d[d["Balapan"] >= min_drv].sort_values(["Menang", "Podium"], ascending=False)
    d = d.rename(columns={"Start_pole": "Start dari pole", "Rata2_grid": "Rata-rata posisi start",
                          "Rata2_finis": "Rata-rata finis", "DNF": "Gagal finis (%)"})
    if d.empty:
        st.info("Tidak ada pembalap yang memenuhi syarat. Turunkan batas minimal balapan.")
    else:
        st.dataframe(d.round(1).reset_index().rename(columns={"driver": "Pembalap"}), hide_index=True)
        pick = st.selectbox("Lihat rincian per musim", d.index.tolist())
        one = f[f["driver"] == pick].groupby("season").agg(
            Tim=("constructor", lambda s: ", ".join(sorted(set(s)))),
            Balapan=("win", "size"),
            Menang=("win", "sum"),
            Podium=("podium", "sum"),
            Poin=("points", "sum"),
            Rata2_grid=("grid_adj", "mean"),
        ).rename(columns={"Rata2_grid": "Rata-rata posisi start"})
        st.dataframe(one.round(1).reset_index().rename(columns={"season": "Musim"}), hide_index=True)

with tab_data:
    st.markdown("Data hasil balapan sesuai filter. Bisa diunduh sebagai CSV.")
    cols = ["season", "round", "race_name", "circuit", "driver", "constructor", "grid", "position",
            "status", "points", "finished", "quali_position"]
    table = f[cols].sort_values(["season", "round", "position"])
    st.dataframe(table, hide_index=True)
    st.download_button("Unduh CSV", table.to_csv(index=False).encode("utf-8"),
                       file_name="f1_hasil_balapan_filter.csv", mime="text/csv")

with tab_about:
    all_pole = df[df["grid"] == 1]
    circ_all = all_pole.groupby("circuit_id").agg(n=("win", "size"), k=("win", "sum"))
    circ_all = circ_all[circ_all["n"] >= 8]
    season_all = all_pole[all_pole["season"] != partial_season].groupby("season").agg(n=("win", "size"), k=("win", "sum"))
    p_circuit = spread_pvalue(tuple(circ_all["n"]), tuple(circ_all["k"]))
    p_season = spread_pvalue(tuple(season_all["n"]), tuple(season_all["k"]))

    def verdict(p):
        return "belum terbukti berbeda" if p >= 0.05 else "ada bukti perbedaan"

    st.subheader("Apa tujuan halaman ini?")
    st.markdown(
        "Halaman ini adalah **project portofolio analisis data** yang saya buat memakai topik yang saya sukai. "
        "Tujuannya menunjukkan cara menjawab satu pertanyaan sederhana dengan data: mengambil data, membersihkannya, "
        "menganalisisnya, menguji apakah kesimpulannya cukup kuat, lalu menyajikannya supaya mudah dipahami siapa saja."
    )

    st.subheader("Dari mana datanya?")
    st.markdown(
        f"Hasil balapan dan kualifikasi Formula 1 musim {smin} sampai {smax} ({df.groupby(['season', 'round']).ngroups} balapan, "
        f"{len(df):,} baris hasil) dari Jolpica-F1 API. Ini data proyek komunitas, bukan data resmi Formula 1."
    )

    st.subheader("Catatan penting")
    st.markdown(
        "- Angka di halaman ini menunjukkan **hubungan**, bukan sebab-akibat. Mobil tercepat cenderung start di depan dan menang.\n"
        "- Tiap sirkuit hanya punya belasan balapan, jadi perbandingan antar sirkuit kurang kuat.\n"
        + (f"- Musim {partial_season} belum selesai sehingga datanya belum lengkap.\n" if partial_season else "")
        + "- Posisi start dihitung dari grid saat balapan, yang bisa berbeda dari hasil kualifikasi jika ada penalti."
    )

    st.subheader("Hasil uji statistik")
    st.markdown(
        "Untuk memastikan perbedaan di grafik bukan sekadar kebetulan, saya menjalankan uji simulasi pada seluruh data. "
        f"Hasilnya: perbedaan antar sirkuit **{verdict(p_circuit)}** (p = {p_circuit:.2f}) dan perbedaan antar musim "
        f"**{verdict(p_season)}** (p = {p_season:.2f}). Nilai p di atas 0,05 berarti perbedaannya masih wajar terjadi "
        "karena kebetulan. Ini tidak membuktikan bahwa perbedaan itu tidak ada, hanya bahwa data yang ada belum cukup untuk memastikannya."
    )

    st.subheader("Cara kerja dan alat")
    st.markdown(
        "1. Mengambil data lewat API dan menyimpannya sebagai CSV.\n"
        "2. Membersihkan data (nilai kosong, duplikat, status finis, start dari pit lane).\n"
        "3. Memuat ke database SQLite dan menulis query SQL (agregasi, CTE, window function).\n"
        "4. Eksplorasi dan visualisasi.\n"
        "5. Uji statistik dan interval kepercayaan.\n"
        "6. Dashboard interaktif ini.\n\n"
        "**Alat:** Python, Pandas, NumPy, SciPy, SQL (SQLite), Altair, Matplotlib, Streamlit."
    )

    st.subheader("Tentang saya")
    st.markdown(
        "**Jonathan Daniel Hope**, mahasiswa S1 Teknik Informatika Universitas Tarumanagara yang tertarik pada "
        "Data Science dan Machine Learning.\n\n"
        "[GitHub](https://github.com/Jojoxddd) | "
        "[LinkedIn](https://linkedin.com/in/jonathandanielh) | "
        "[Portofolio](https://jonathandaniel.my.id)"
    )