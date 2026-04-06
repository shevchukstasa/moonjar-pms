# Panduan Owner -- Moonjar PMS

> Versi: 1.0 | Tanggal: 2026-04-06
> Moonjar Production Management System

---

## Daftar Isi

1. [Memulai](#1-memulai)
2. [Ringkasan Dashboard](#2-ringkasan-dashboard)
3. [Ringkasan Keuangan](#3-ringkasan-keuangan)
4. [KPI Operasional](#4-kpi-operasional)
5. [Tren Kinerja](#5-tren-kinerja)
6. [Rincian OPEX](#6-rincian-opex)
7. [Papan Peringkat Pabrik](#7-papan-peringkat-pabrik)
8. [Matriks Kinerja Pabrik](#8-matriks-kinerja-pabrik)
9. [Posisi Kritis & Defisit](#9-posisi-kritis--defisit)
10. [Akses ke Semua Peran](#10-akses-ke-semua-peran)
11. [Ekspor & Pelaporan](#11-ekspor--pelaporan)
12. [Manajemen Pengguna & Pabrik](#12-manajemen-pengguna--pabrik)
13. [Kesehatan Sistem & Diagnostik](#13-kesehatan-sistem--diagnostik)
14. [Bot Telegram](#14-bot-telegram)
15. [Kerangka Keputusan Strategis](#15-kerangka-keputusan-strategis)
16. [Referensi Navigasi](#16-referensi-navigasi)
17. [Tips dan Praktik Terbaik](#17-tips-dan-praktik-terbaik)

---

## 1. Memulai

### 1.1. Masuk ke Sistem

1. Buka dashboard Moonjar PMS di browser Anda.
2. Masuk menggunakan salah satu metode:
   - **Google OAuth** -- klik "Sign in with Google"
   - **Email dan kata sandi** -- masukkan kredensial Anda dan klik "Login"
3. Setelah autentikasi, sistem mendeteksi peran Owner Anda dan mengarahkan ke `/owner` -- dashboard Owner.

### 1.2. Hak Akses Owner

Sebagai Owner, Anda memiliki **tingkat akses tertinggi** di sistem:

- Akses penuh ke semua dashboard (Owner, CEO, PM, QM, Gudang, Sortir, Purchaser, Admin)
- Visibilitas data keuangan (pendapatan, pengeluaran, margin, OPEX, CAPEX)
- Manajemen pengguna dan pabrik
- Semua kemampuan ekspor
- Analitik strategis dan data tren
- Pemantauan kesehatan sistem

### 1.3. Pemilihan Periode

Dashboard Owner dilengkapi **Pemilih Periode** (kanan atas) dengan opsi:

- **Minggu** -- 7 hari terakhir
- **Bulan** -- 30 hari terakhir (default)
- **Kuartal** -- 90 hari terakhir
- **Tahun** -- 365 hari terakhir

Semua data keuangan dan operasional di dashboard menyesuaikan dengan periode yang dipilih.

---

## 2. Ringkasan Dashboard

Dashboard Owner (`/owner`) memberikan tampilan strategis dengan fokus keuangan.

### 2.1. Tata Letak

1. **Header** -- judul, pemilih periode, tombol Ekspor Excel
2. **Kartu Ringkasan Keuangan** -- pendapatan, pengeluaran, margin, output, pesanan
3. **Kartu KPI Operasional** -- tepat waktu, tingkat cacat, pemanfaatan kiln, OEE
4. **Blok Keuangan** -- rincian keuangan detail
5. **Tren Kinerja** -- grafik tren 6 bulan
6. **Rincian OPEX** -- analisis kategori pengeluaran
7. **Papan Peringkat Pabrik** -- peringkat kompetitif pabrik
8. **Matriks Kinerja Pabrik** -- tabel perbandingan detail
9. **Posisi Kritis** -- posisi yang berisiko
10. **Defisit Material** -- material yang memblokir produksi

---

## 3. Ringkasan Keuangan

### 3.1. Kartu KPI Keuangan

Lima kartu keuangan di atas:

| KPI | Deskripsi |
|---|---|
| **Pendapatan** | Total pendapatan untuk periode yang dipilih (USD) |
| **Pengeluaran** | OPEX + CAPEX gabungan |
| **Margin Laba** | Persentase margin dan jumlah absolut |
| **Output m²** | Total output produksi dengan biaya per m² |
| **Pesanan Selesai** | Pesanan yang diselesaikan dengan jumlah yang sedang berjalan |

### 3.2. Blok Keuangan

Komponen rincian keuangan detail yang menampilkan:

- Pendapatan berdasarkan sumber
- Kategori OPEX (material, tenaga kerja, utilitas, pemeliharaan)
- Item CAPEX (peralatan, perbaikan fasilitas)
- Analisis margin
- Perbandingan periode ke periode

### 3.3. Rasio Keuangan Kunci

| Rasio | Baik | Perhatian | Perlu Tindakan |
|---|---|---|---|
| Margin Laba | > 30% | 15-30% | < 15% |
| Biaya per m² | Menurun | Stabil | Meningkat |
| OPEX terhadap Pendapatan | < 60% | 60-75% | > 75% |

---

## 4. KPI Operasional

### 4.1. Kartu KPI

Empat kartu KPI operasional:

| KPI | Target | Deskripsi |
|---|---|---|
| **Tepat Waktu** | > 90% | Persentase posisi dikirim sesuai jadwal |
| **Tingkat Cacat** | < 3% | Persentase produk cacat |
| **Util. Kiln** | > 75% | Pemanfaatan kapasitas kiln |
| **OEE** | > 85% | Efektivitas Peralatan Keseluruhan |

### 4.2. Rincian OEE

OEE (Overall Equipment Effectiveness) menggabungkan tiga faktor:

- **Ketersediaan** -- waktu aktif vs. waktu produksi yang direncanakan
- **Kinerja** -- kecepatan aktual vs. kecepatan maksimum
- **Kualitas** -- produk baik vs. total produk

OEE = Ketersediaan x Kinerja x Kualitas

---

## 5. Tren Kinerja

### 5.1. Grafik Tren

Empat grafik tren 6 bulan memberikan konteks historis:

| Grafik | Yang Ditampilkan |
|---|---|
| **Tren Output** | Output produksi bulanan dalam m² |
| **Tingkat Tepat Waktu** | Persentase pengiriman tepat waktu bulanan |
| **Tren Tingkat Cacat** | Perkembangan tingkat cacat bulanan |
| **Tren OEE** | Skor OEE bulanan |

### 5.2. Membaca Tren

- **Tren naik pada Output + Tepat Waktu**: Bisnis tumbuh efisien
- **Tingkat Cacat naik**: Masalah kualitas -- selidiki akar penyebab
- **OEE turun dengan Output stabil**: Masalah peralatan, pemeliharaan diperlukan
- **Tepat Waktu turun dengan Util. Kiln tinggi**: Kendala kapasitas, pertimbangkan ekspansi

> **Tips**: Tren lebih bermakna daripada potret. Satu minggu yang buruk hanyalah gangguan; tren menurun 3 bulan memerlukan tindakan.

---

## 6. Rincian OPEX

### 6.1. Kategori OPEX

Grafik Rincian OPEX menampilkan pengeluaran berdasarkan kategori:

- **Material** -- bahan baku, glasir, engobe, bahan kimia
- **Tenaga Kerja** -- gaji, lembur, kontribusi BPJS
- **Utilitas** -- listrik, gas, air
- **Pemeliharaan** -- perbaikan peralatan, penggantian rak kiln
- **Logistik** -- pengiriman, biaya pengantaran
- **Lainnya** -- pengeluaran operasional lain-lain

### 6.2. Menganalisis OPEX

Perhatikan:

- Kategori yang tumbuh lebih cepat dari pendapatan (biaya merayap)
- Lonjakan mendadak dalam biaya pemeliharaan (kegagalan peralatan)
- Biaya material meningkat tanpa peningkatan output yang sesuai
- Biaya tenaga kerja naik tanpa perubahan jumlah karyawan (lembur berlebihan)

---

## 7. Papan Peringkat Pabrik

### 7.1. Peringkat Kompetitif

Komponen Papan Peringkat Pabrik memberi peringkat pabrik berdasarkan skor kinerja keseluruhan. Ini menciptakan kompetisi sehat antar tim pabrik.

### 7.2. Faktor Penilaian

Pabrik dinilai berdasarkan:

- Output produksi (m²)
- Tingkat pengiriman tepat waktu
- Tingkat cacat (lebih rendah lebih baik)
- OEE
- Pemanfaatan kiln

---

## 8. Matriks Kinerja Pabrik

### 8.1. Tabel Perbandingan

Tabel detail yang membandingkan semua pabrik:

| Kolom | Deskripsi |
|---|---|
| Pabrik | Nama dan lokasi |
| Output m² | Volume produksi (hijau = tertinggi) |
| Kualitas (Cacat %) | Tingkat cacat (hijau = terendah) |
| Efisiensi (OEE) | Efektivitas peralatan (hijau = tertinggi) |
| Util. Kiln | Persentase pemanfaatan kiln |
| Tepat Waktu % | Keandalan pengiriman |
| Pesanan Aktif | Beban kerja saat ini |

### 8.2. Kode Warna

- **Hijau**: Performa terbaik atau di atas target
- **Kuning**: Memerlukan perhatian
- **Merah**: Di bawah tingkat yang dapat diterima

---

## 9. Posisi Kritis & Defisit

### 9.1. Posisi Kritis

Posisi yang:

- Terlambat (melewati tenggat)
- Sangat terlambat (> 48 jam tertinggal)
- Berisiko melewati tenggat (kesehatan buffer di zona merah)

### 9.2. Defisit Material

Material yang stok saat ini di bawah ambang batas minimum, berpotensi memblokir produksi.

---

## 10. Akses ke Semua Peran

### 10.1. Akses Dashboard

Sebagai Owner, Anda dapat menavigasi ke dashboard peran apa pun:

| Dashboard | URL | Yang Anda Lihat |
|---|---|---|
| Owner | `/owner` | Ikhtisar strategis (Anda di sini) |
| CEO | `/ceo` | Ikhtisar operasional, lintas pabrik |
| PM | `/manager` | Produksi harian |
| Kualitas | `/quality` | Antrian QC, blokir, kartu masalah |
| Gudang | `/warehouse` | Inventaris, pengiriman |
| Sortir/Packer | `/sorter-packer` | Operasi sortir, packing |
| Purchaser | `/purchaser` | Pengadaan, supplier |
| Admin | `/admin` | Konfigurasi sistem |

### 10.2. Kapan Menggunakan Setiap Dashboard

| Situasi | Dashboard |
|---|---|
| Review strategis mingguan | Owner |
| Pengecekan operasional harian | CEO |
| Investigasi keterlambatan produksi | PM |
| Memahami masalah kualitas | Kualitas |
| Memeriksa ketersediaan material | Gudang |
| Meninjau status pengadaan | Purchaser |
| Perubahan konfigurasi sistem | Admin |

---

## 11. Ekspor & Pelaporan

### 11.1. Ekspor Bulanan Owner

Klik **Ekspor Excel** di dashboard Owner untuk mengunduh laporan bulanan komprehensif:

- Ringkasan keuangan (pendapatan, pengeluaran, margin)
- Data perbandingan pabrik
- Metrik produksi
- Metrik kualitas
- Data tren

Format file: `owner-report-YYYY-MM.xlsx`

### 11.2. Laporan Lainnya

Navigasi ke `/reports` untuk jenis laporan tambahan:

- Ringkasan pesanan
- Pemanfaatan kiln
- Analitik produksi
- Pemilihan rentang tanggal kustom

---

## 12. Manajemen Pengguna & Pabrik

### 12.1. Manajemen Pengguna

Navigasi ke `/users` untuk mengelola semua pengguna sistem:

- Buat dan edit akun pengguna
- Tugaskan peran dan akses pabrik
- Aktifkan/nonaktifkan akun
- Reset kata sandi

### 12.2. Manajemen Pabrik

Navigasi ke `/admin` untuk mengelola pabrik:

- Tambah pabrik baru
- Konfigurasi integrasi Telegram per pabrik
- Aktifkan/nonaktifkan pabrik
- Atur izin pembersihan PM

---

## 13. Kesehatan Sistem & Diagnostik

### 13.1. Pengecekan Kesehatan

Sistem menyediakan endpoint kesehatan:

```
GET /api/health -> {"status": "ok"}
```

Jika kesehatan mengembalikan selain "ok", sistem memiliki masalah yang perlu perhatian.

### 13.2. Titik Pemantauan

| Pemeriksaan | Cara | Yang Dicari |
|---|---|---|
| Kesehatan API | `/api/health` | Harus mengembalikan `{"status":"ok"}` |
| Status Bot | Panel Admin > Bot Telegram | Titik hijau = terhubung |
| Sesi Aktif | Panel Admin > Keamanan > Sesi | Tidak ada sesi mencurigakan |
| Log Audit | Panel Admin > Keamanan > Audit | Tidak ada perubahan yang tidak diotorisasi |
| Tingkat Error | Log backend (Railway) | Tidak ada error 500 berulang |

### 13.3. Backup dan Keamanan Data

- Database dikelola oleh Railway dengan backup otomatis
- Log audit menangkap semua perubahan data
- Entri keuangan tidak pernah dihapus (hanya soft-delete)
- Ekspor ke Excel menyediakan backup tambahan untuk laporan

---

## 14. Bot Telegram

### 14.1. Perintah

| Perintah | Deskripsi |
|---|---|
| `/start` | Inisialisasi koneksi bot |
| `/ceoreport` | Dapatkan laporan harian level CEO |
| `/mystats` | Lihat statistik pribadi |
| `/leaderboard` | Lihat papan peringkat pabrik/pekerja |
| `/stock` | Periksa level stok material |
| `/help` | Daftar semua perintah |

### 14.2. Notifikasi yang Anda Terima

Sebagai Owner, Anda menerima semua notifikasi kritis:

- Kejadian force unblock
- Kekosongan kehadiran (3+ pekerja absen)
- Anomali kualitas
- Pesanan baru dari webhook Sales
- Masalah yang dieskalasi

---

## 15. Kerangka Keputusan Strategis

### 15.1. Checklist Review Bulanan

| Pertanyaan | Sumber Data | Ambang Batas Tindakan |
|---|---|---|
| Apakah bisnis profitable? | Kartu Keuangan | Margin < 15% |
| Apakah kita berproduksi cukup? | Tren Output | Menurun 3+ bulan |
| Apakah kualitas dapat diterima? | Tren Tingkat Cacat | Naik di atas 5% |
| Apakah kita mengirim tepat waktu? | Tren Tepat Waktu | Di bawah 85% |
| Apakah biaya terkendali? | Rincian OPEX | Tumbuh lebih cepat dari pendapatan |
| Pabrik mana yang perlu bantuan? | Matriks Pabrik | OEE di bawah 70% |

### 15.2. Kriteria Keputusan Ekspansi

Pertimbangkan menambah kapasitas (kiln baru, pabrik baru) ketika:

- Pemanfaatan kiln konsisten > 85% di semua pabrik
- Backlog pesanan tumbuh bulan ke bulan
- Tingkat tepat waktu turun meskipun pemanfaatan penuh
- Pesanan yang menguntungkan ditolak

### 15.3. Peluang Pengurangan Biaya

| Area | Sinyal | Pendekatan |
|---|---|---|
| Material | Biaya per m² naik | Negosiasi dengan supplier, pertimbangkan alternatif |
| Energi | Biaya utilitas meningkat | Optimalkan jadwal kiln (batch pembakaran serupa) |
| Kualitas | Tingkat cacat tinggi | Investasi pelatihan QC, perbarui resep |
| Pemeliharaan | OPEX rak meningkat | Evaluasi material rak berkualitas lebih tinggi |
| Tenaga Kerja | Lembur berlebihan | Rekrut pekerja tambahan atau perbaiki penjadwalan |

---

## 16. Referensi Navigasi

| Halaman | URL | Tujuan |
|---|---|---|
| Dashboard Owner | `/owner` | Ikhtisar keuangan strategis |
| Dashboard CEO | `/ceo` | Ikhtisar operasional |
| Dashboard PM | `/manager` | Manajemen produksi |
| Dashboard QM | `/quality` | Manajemen kualitas |
| Dashboard Gudang | `/warehouse` | Manajemen inventaris |
| Sortir Packer | `/sorter-packer` | Sortir dan packing |
| Purchaser | `/purchaser` | Pengadaan |
| Panel Admin | `/admin` | Konfigurasi sistem |
| Pengguna | `/users` | Manajemen pengguna |
| Laporan | `/reports` | Analitik dan laporan |
| Gamifikasi | `/gamification` | Poin dan papan peringkat |
| Tablo | `/tablo` | Tampilan produksi |
| Pengaturan | `/settings` | Pengaturan pribadi |

---

## 17. Tips dan Praktik Terbaik

> **Keuangan dulu**: Sebagai Owner, mulai dengan ringkasan keuangan. Pendapatan, margin, dan biaya per m² adalah metrik utama Anda. Semua yang lain mendukung ini.

> **Mingguan, bukan harian**: Dashboard Owner dirancang untuk review mingguan atau dua mingguan. Untuk pemantauan harian, gunakan dashboard CEO. Terlalu sering memeriksa mengarah ke keputusan reaktif.

> **Tren daripada potret**: Data satu minggu bisa menyesatkan. Gunakan pemilih periode untuk melihat tren bulanan dan kuartalan sebelum membuat keputusan strategis.

> **Papan peringkat pabrik**: Gunakan papan peringkat untuk menciptakan kompetisi sehat tetapi juga untuk mengidentifikasi pabrik mana yang memerlukan lebih banyak dukungan.

> **Ekspor untuk rapat**: Ekspor Excel berisi semua data yang diperlukan untuk update investor atau mitra. Ekspor bulanan dan simpan arsip.

> **Delegasikan masalah operasional**: Jika Anda melihat lonjakan kualitas atau masalah pengiriman di dashboard Owner, jangan selesaikan sendiri. Tandai ke CEO atau PM dan biarkan mereka menyelidiki. Tugas Anda memastikan sistem bekerja, bukan mengoperasikannya.

> **Pantau para pemantau**: Periksa Panel Admin secara berkala untuk memastikan log audit dihasilkan, sesi aktif terlihat normal, dan bot Telegram terhubung.

> **Kesadaran keamanan**: Sebagai akun dengan hak akses tertinggi, kredensial Anda adalah target paling berharga. Gunakan kata sandi yang kuat, aktifkan Google OAuth, dan jangan pernah bagikan login Anda.

---

*Panduan ini mencakup fitur Moonjar PMS v1.0 untuk peran Owner. Untuk dukungan teknis, hubungi pengembang sistem.*
