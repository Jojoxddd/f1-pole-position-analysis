-- Q1: Jumlah balapan dan jumlah entri per musim (cek kelengkapan data)
SELECT season,
       COUNT(DISTINCT round) AS balapan,
       COUNT(*)              AS entri_pembalap
FROM results
GROUP BY season
ORDER BY season;

-- Q2: Berapa persen balapan dimenangkan pembalap yang start dari P1 (2010 - sekarang)?
SELECT COUNT(*)                                   AS balapan,
       SUM(win)                                   AS menang_dari_p1,
       ROUND(100.0 * SUM(win) / COUNT(*), 1)      AS persen_menang_dari_p1,
       SUM(podium)                                AS podium_dari_p1,
       ROUND(100.0 * SUM(podium) / COUNT(*), 1)   AS persen_podium_dari_p1
FROM results
WHERE grid = 1;

-- Q3: Peluang menang, podium, dan DNF berdasarkan posisi start (P1 - P10)
SELECT grid                                         AS posisi_start,
       COUNT(*)                                     AS jumlah_start,
       SUM(win)                                     AS menang,
       ROUND(100.0 * SUM(win)    / COUNT(*), 1)     AS persen_menang,
       ROUND(100.0 * SUM(podium) / COUNT(*), 1)     AS persen_podium,
       ROUND(100.0 * SUM(dnf)    / COUNT(*), 1)     AS persen_dnf
FROM results
WHERE grid BETWEEN 1 AND 10
GROUP BY grid
ORDER BY grid;

-- Q4: Rata-rata posisi yang didapat/hilang berdasarkan posisi start (hanya yang finish)
-- Positif = rata-rata naik posisi dari start.
SELECT grid                                   AS posisi_start,
       COUNT(*)                               AS jumlah_finish,
       ROUND(AVG(positions_gained), 2)        AS rata2_posisi_naik
FROM results
WHERE finished = 1 AND grid BETWEEN 1 AND 20
GROUP BY grid
ORDER BY grid;

-- Q5: Persentase menang dari P1 per sirkuit (minimal 8 balapan)
SELECT MAX(circuit_name)                         AS sirkuit,
       COUNT(*)                                  AS balapan,
       SUM(win)                                  AS menang_dari_p1,
       ROUND(100.0 * SUM(win) / COUNT(*), 1)     AS persen_menang_dari_p1
FROM results
WHERE grid = 1
GROUP BY circuit_id
HAVING COUNT(*) >= 8
ORDER BY persen_menang_dari_p1 DESC, balapan DESC;

-- Q6: Tren per musim: persen menang dari P1 (musim terakhir mungkin belum lengkap)
SELECT season,
       COUNT(*)                                  AS balapan,
       SUM(win)                                  AS menang_dari_p1,
       ROUND(100.0 * SUM(win) / COUNT(*), 1)     AS persen_menang_dari_p1
FROM results
WHERE grid = 1
GROUP BY season
ORDER BY season;

-- Q7: Tiga tim dengan poin terbanyak per musim (window function)
-- Catatan: dihitung dari poin hasil balapan saja, jadi bisa berbeda dari klasemen resmi.
WITH poin_tim AS (
    SELECT season, constructor, SUM(points) AS total_poin
    FROM results
    GROUP BY season, constructor
),
peringkat AS (
    SELECT season, constructor, total_poin,
           ROW_NUMBER() OVER (PARTITION BY season ORDER BY total_poin DESC) AS peringkat
    FROM poin_tim
)
SELECT season, peringkat, constructor, total_poin
FROM peringkat
WHERE peringkat <= 3
ORDER BY season, peringkat;
