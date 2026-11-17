# F1 Pole Position Analysis

Project kecil untuk latihan analisis data, pakai topik yang saya suka: Formula 1. Pertanyaannya sederhana, kalau seorang pembalap start dari posisi paling depan, seberapa besar kemungkinan dia menang?

Dashboard: 

## Kenapa saya bikin ini

Tiap nonton balapan hampir selalu ada yang bilang "yang pole pasti menang". Saya ingin cek sendiri pakai data, dan sekalian latihan mengerjakan satu project dari awal sampai akhir: ambil data dari API, bersihkan, query pakai SQL, uji statistik, coba model sederhana, lalu bikin dashboard supaya hasilnya bisa dilihat tanpa harus baca kode.

## Hasilnya

Dari 348 balapan (2010 sampai 2026), pembalap yang start dari posisi 1 menang di 185 balapan, sekitar 53%, dan finis di podium sekitar 80%. Start dari posisi 2 menang 25%, dan posisi 3 tinggal 10%.

Per sirkuit sempat kelihatan menarik: Yas Marina 75%, Sochi 25%. Tapi tiap sirkuit hanya punya 8 sampai 18 balapan, dan setelah diuji (chi-square, p sekitar 0,42) selisih sebesar itu masih wajar terjadi karena kebetulan. Perbandingan antar musim juga begitu (p sekitar 0,87). Jadi saya tidak menyimpulkan bahwa ada sirkuit yang memang lebih menguntungkan pole.

Untuk model prediksi podium, saya latih di musim 2010 sampai 2022 dan uji di 2023 sampai 2026. Hasilnya agak antiklimaks. Aturan sederhana "tebak tiga pembalap yang start terdepan" benar rata-rata 2,01 dari 3 per balapan, sedangkan model terbaik 2,03. Menambahkan performa tim dan pembalap di lima balapan terakhir sedikit memperbaiki kualitas probabilitas (ROC AUC dari 0,92 ke 0,94), tapi tidak membuat tebakan tiga besar lebih akurat. Posisi start tetap faktor yang paling berpengaruh.

## Isi project

Skrip di `src/` dijalankan berurutan:

- `01_fetch_data.py` mengambil hasil balapan dan kualifikasi dari API lalu menyimpannya jadi CSV
- `02_clean_data.py` membersihkan data dan membuat kolom turunan (finis atau DNF, posisi start, dan lain-lain)
- `03_load_to_sqlite.py` memasukkan data ke SQLite dan menjalankan query dari `sql/queries.sql`
- `04_eda_charts.py` membuat grafik eksplorasi
- `05_stats_tests.py` menghitung interval kepercayaan dan uji statistik
- `06_model_podium.py` melatih dan membandingkan model prediksi podium

Dashboard-nya ada di `app.py` (Streamlit).

## Menjalankan sendiri

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; di Mac/Linux: source .venv/bin/activate
python -m pip install -r requirements-analysis.txt

python src/01_fetch_data.py     # butuh internet, beberapa menit
python src/02_clean_data.py
python src/03_load_to_sqlite.py
python src/04_eda_charts.py
python src/05_stats_tests.py
python src/06_model_podium.py

python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Catatan

Data dari Jolpica-F1 API, proyek komunitas yang meneruskan Ergast, jadi bukan data resmi Formula 1. Total poin dihitung dari hasil balapan saja (poin sprint tidak ikut), jadi bisa sedikit beda dari klasemen resmi. Musim 2026 masih berjalan waktu data diambil.

Analisis ini hanya menunjukkan hubungan, bukan sebab-akibat. Mobil yang cepat biasanya start di depan dan juga menang, dan posisi start sendiri sudah mencerminkan kecepatan mobil. Data uji model juga hanya 89 balapan, jadi selisih kecil antar model jangan terlalu dipercaya.

Satu hal yang sempat salah di awal: status "Lapped" terhitung sebagai DNF. Ketahuan dari laporan kualitas data dan sudah diperbaiki.

Kalau ada waktu, saya ingin menguji apakah selisih antar model benar-benar nyata (bootstrap per balapan) dan menampilkan hasil model di dashboard.

## Kontak

Jonathan Daniel Hope, mahasiswa Teknik Informatika Universitas Tarumanagara.
[GitHub](https://github.com/Jojoxddd) | [LinkedIn](https://linkedin.com/in/jonathandanielh) | [Portofolio](https://jonathandaniel.my.id)
