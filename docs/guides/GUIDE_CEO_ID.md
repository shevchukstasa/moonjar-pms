# Panduan CEO -- Moonjar PMS

> Versi: 1.0 | Tanggal: 2026-04-06
> Moonjar Production Management System

---

## Daftar Isi

1. [Memulai](#1-memulai)
2. [Ringkasan Dashboard](#2-ringkasan-dashboard)
3. [Kartu KPI](#3-kartu-kpi)
4. [Tab Alur Produksi](#4-tab-alur-produksi)
5. [Tab Perbandingan Pabrik](#5-tab-perbandingan-pabrik)
6. [Tab Tugas & Masalah](#6-tab-tugas--masalah)
7. [Tab Kiln & Jadwal](#7-tab-kiln--jadwal)
8. [Analitik OPEX Rak Kiln](#8-analitik-opex-rak-kiln)
9. [Izin Pembersihan Data PM](#9-izin-pembersihan-data-pm)
10. [Manajemen Karyawan](#10-manajemen-karyawan)
11. [Laporan Keuangan](#11-laporan-keuangan)
12. [Pengawasan Gamifikasi](#12-pengawasan-gamifikasi)
13. [Ekspor & Pelaporan](#13-ekspor--pelaporan)
14. [Perintah Bot Telegram](#14-perintah-bot-telegram)
15. [Pengambilan Keputusan Berbasis Data](#15-pengambilan-keputusan-berbasis-data)
16. [Referensi Navigasi](#16-referensi-navigasi)
17. [Tips dan Praktik Terbaik](#17-tips-dan-praktik-terbaik)

---

## 1. Memulai

### 1.1. Masuk ke Sistem

1. Buka dashboard Moonjar PMS di browser Anda.
2. Masuk menggunakan salah satu metode yang tersedia:
   - **Google OAuth** -- klik "Sign in with Google"
   - **Email dan kata sandi** -- masukkan kredensial Anda dan klik "Login"
3. Setelah autentikasi, sistem mendeteksi peran CEO Anda dan mengarahkan ke `/ceo` -- dashboard CEO.

### 1.2. Pemilihan Pabrik

Sebagai CEO, Anda memiliki akses ke **semua pabrik** secara bersamaan:

- **Mode Semua Pabrik** (default): Dashboard menampilkan data gabungan dari seluruh pabrik.
- **Mode Pabrik Tunggal**: Gunakan dropdown pemilih pabrik (kanan atas) untuk fokus pada satu pabrik.

> **Tips**: Mulai setiap hari dalam mode "Semua Pabrik" untuk melihat gambaran lengkap, lalu telusuri pabrik tertentu saat menyelidiki masalah.

### 1.3. Kemampuan Peran

Sebagai CEO, Anda dapat:

- Melihat alur produksi, kesehatan buffer, dan posisi kritis di semua pabrik
- Membandingkan kinerja pabrik secara berdampingan
- Meninjau dan mengelola tugas pemblokir serta permintaan perubahan
- Memantau jadwal dan pemanfaatan kiln
- Mengontrol izin pembersihan data PM per pabrik
- Melihat analitik siklus hidup dan OPEX rak kiln
- Mengekspor laporan harian CEO ke Excel
- Mengakses manajemen karyawan lintas pabrik
- Menerima notifikasi Telegram untuk kejadian kritis

---

## 2. Ringkasan Dashboard

Dashboard CEO (`/ceo`) adalah pusat komando strategis Anda. Menyediakan tampilan operasional tingkat tinggi dengan kemampuan untuk menelusuri detail.

### 2.1. Tata Letak

Dashboard terdiri dari:

1. **Header** -- judul halaman, pemilih pabrik, dan tombol Ekspor Excel
2. **Kartu KPI** -- enam indikator kinerja utama
3. **Tab** -- empat bagian utama (Alur Produksi, Perbandingan Pabrik, Tugas & Masalah, Kiln & Jadwal)
4. **Widget OPEX Rak Kiln** -- analitik siklus hidup rak kiln
5. **Izin Pembersihan PM** -- toggle izin sementara

### 2.2. Penanganan Error

Jika API analitik atau API pabrik gagal, banner error merah muncul di bagian atas:

> "Error loading dashboard data. Analytics API failed."

Coba refresh halaman. Jika error berlanjut, periksa log backend atau hubungi administrator sistem.

---

## 3. Kartu KPI

Enam kartu KPI ditampilkan di bagian atas dashboard:

| KPI | Deskripsi | Yang Perlu Diperhatikan |
|---|---|---|
| **Pesanan Aktif** | Pesanan yang sedang dalam produksi (dari total) | Penumpukan mungkin menandakan masalah kapasitas |
| **Output m²** | Meter persegi diproduksi dalam 30 hari terakhir | Bandingkan dengan target kapasitas |
| **Tepat Waktu** | Persentase posisi dikirim sesuai jadwal | Di bawah 85% perlu investigasi |
| **Tingkat Cacat** | Persentase barang cacat | Di atas 5% adalah tanda bahaya kualitas |
| **Util. Kiln** | Persentase pemanfaatan kiln | Di bawah 70% berarti kiln kurang terpakai |
| **OEE** | Efektivitas Peralatan Keseluruhan | Target kelas dunia 85%+ |

> **Wawasan kunci**: Jika Tepat Waktu turun sementara Pemanfaatan Kiln tinggi, kemacetan kemungkinan ada di tahap pra-pembakaran atau pasca-pembakaran, bukan di kiln itu sendiri.

---

## 4. Tab Alur Produksi

Tab default yang menampilkan alur produksi dan kondisi saat ini.

### 4.1. Grafik Alur Produksi

Visualisasi corong yang menunjukkan berapa banyak posisi di setiap tahap:

- Direncanakan -> Dalam Proses -> Glazing -> Pembakaran -> Sortir -> QC -> Siap -> Dikirim

Ini membantu Anda melihat di mana pekerjaan menumpuk dan mengidentifikasi kemacetan secara visual.

### 4.2. Grafik Output Harian

Grafik batang 30 hari yang menunjukkan output produksi harian dalam meter persegi. Perhatikan:

- Output harian yang konsisten (baik)
- Penurunan mendadak (selidiki -- pemeliharaan kiln? kekurangan material?)
- Penurunan akhir pekan (wajar jika pabrik tidak beroperasi di akhir pekan)

### 4.3. Kesehatan Buffer (TOC)

Tabel kesehatan buffer Theory of Constraints menampilkan posisi berdasarkan status buffer:

| Zona | Kondisi | Tindakan |
|---|---|---|
| **Hijau** | delta >= -5% | Sesuai jadwal, tidak perlu tindakan |
| **Kuning** | -20% <= delta < -5% | Pantau dengan cermat, pertimbangkan penyesuaian prioritas |
| **Merah** | delta < -20% atau melewati tenggat | Mendesak: eskalasi ke Production Manager |

### 4.4. Posisi Kritis

Tabel yang mencantumkan posisi yang memerlukan perhatian -- terlambat, mandek, atau berisiko melewati tenggat. Diurutkan berdasarkan urgensi.

### 4.5. Defisit Material

Menampilkan material dengan stok di bawah saldo minimum, yang dapat menghambat produksi. Jika Anda melihat defisit yang terus-menerus:

1. Periksa apakah permintaan pembelian sudah dibuat
2. Verifikasi jadwal pengiriman supplier dengan Purchaser
3. Pertimbangkan apakah prioritas produksi perlu diseimbangkan kembali

### 4.6. Feed Aktivitas

Feed kejadian sistem secara real-time (auto-refresh setiap 30 detik):

- Pesanan baru diterima dari Sales
- Posisi maju melalui tahapan
- Masalah kualitas terdeteksi
- Transaksi material
- Penyelesaian tugas

---

## 5. Tab Perbandingan Pabrik

### 5.1. Kartu Kinerja Pabrik

Kartu perbandingan visual untuk setiap pabrik yang menampilkan metrik kunci:

- Output dalam m²
- Pesanan aktif
- Pemanfaatan kiln
- Tingkat cacat
- Tingkat pengiriman tepat waktu
- Skor OEE

### 5.2. Tabel Perbandingan Detail

Tabel komprehensif yang membandingkan semua pabrik secara berdampingan:

| Kolom | Deskripsi |
|---|---|
| Pabrik | Nama dan lokasi |
| Pesanan Aktif | Pesanan sedang dalam produksi |
| Output m² | Output produksi |
| Util. Kiln | Persentase pemanfaatan kiln |
| Cacat % | Tingkat cacat (merah jika terburuk, hijau jika terbaik) |
| Tepat Waktu % | Tingkat pengiriman tepat waktu (hijau jika terbaik) |
| OEE % | Efektivitas Peralatan Keseluruhan |

> **Tips**: Gunakan tab ini saat rapat manajemen mingguan untuk membandingkan kinerja pabrik dan menetapkan target perbaikan.

---

## 6. Tab Tugas & Masalah

### 6.1. Kartu Ringkasan

Empat kartu tampilan cepat di bagian atas:

- **Tugas Pemblokir** -- tugas yang mencegah posisi maju
- **Posisi Terlambat** -- posisi yang melewati tenggat
- **Permintaan Perubahan Tertunda** -- permintaan modifikasi dari Sales yang menunggu review
- **Total Tugas Terbuka** -- semua tugas aktif lintas pabrik

### 6.2. Daftar Tugas Pemblokir

Menampilkan semua tugas dengan `blocking = true` yang saat ini menghambat kemajuan produksi. Untuk setiap tugas:

- Jenis dan deskripsi tugas
- Posisi/pesanan mana yang diblokir
- Peran yang ditugaskan
- Tanggal pembuatan dan usia tugas

### 6.3. Permintaan Perubahan

Permintaan perubahan dari Sales yang memodifikasi pesanan yang ada. Ini memerlukan persetujuan Production Manager tetapi CEO dapat memantau antrian dan intervensi jika diperlukan.

### 6.4. Posisi Terlambat

Posisi yang telah melewati tanggal penyelesaian yang direncanakan. Diberi kode warna berdasarkan tingkat keparahan:

- **< 24 jam terlambat**: Kuning
- **24-48 jam terlambat**: Oranye
- **> 48 jam terlambat**: Merah

---

## 7. Tab Kiln & Jadwal

### 7.1. Ikhtisar Status Kiln

Menampilkan semua kiln di seluruh pabrik dengan status saat ini:

| Status | Warna | Arti |
|---|---|---|
| `idle` | Abu-abu | Tersedia untuk pemuatan |
| `loading` | Biru | Sedang dimuat |
| `firing` | Oranye | Pembakaran sedang berlangsung |
| `cooling` | Cyan | Pendinginan setelah pembakaran |
| `unloading` | Kuning | Sedang dibongkar |
| `maintenance` | Merah | Dalam pemeliharaan, tidak tersedia |

### 7.2. Jadwal Pembakaran

Tampilan kalender pembakaran mendatang dan yang baru selesai. Menampilkan:

- Nama kiln dan kapasitas
- Tanggal dan waktu pembakaran terjadwal
- Isi batch (posisi, total m²)
- Profil pembakaran yang digunakan

> **Tips**: Jika kiln menganggur lebih dari 2 hari, tanyakan PM apakah ada batch yang siap dibakar atau ada masalah yang menghambat.

---

## 8. Analitik OPEX Rak Kiln

Widget analitik khusus di bagian bawah dashboard yang menyediakan data siklus hidup dan biaya untuk rak kiln.

### 8.1. KPI Ikhtisar

| KPI | Deskripsi |
|---|---|
| **Rak Aktif** | Jumlah rak yang saat ini digunakan (dengan total area dalam m²) |
| **Rata-rata Umur Pakai** | Rata-rata jumlah siklus pembakaran sebelum penghapusan |
| **Biaya / Siklus** | Rata-rata biaya per siklus pembakaran dalam IDR |
| **Total Investasi** | Total uang yang diinvestasikan untuk rak (dengan jumlah yang sudah dihapus) |

### 8.2. Proyeksi Penggantian

Peringatan berwarna kuning yang menampilkan:

- Jumlah penggantian rak yang diharapkan dalam **30 hari** ke depan dengan estimasi biaya
- Jumlah penggantian rak yang diharapkan dalam **90 hari** ke depan dengan estimasi biaya

Gunakan ini untuk perencanaan anggaran dan pengadaan.

### 8.3. Mendekati Akhir Masa Pakai

Daftar rak yang telah menggunakan 80%+ dari siklus pembakaran maksimum, diurutkan berdasarkan urgensi:

- Nama rak dan lokasi kiln
- Progress bar yang menunjukkan persentase penggunaan siklus
- Siklus saat ini / siklus maksimum

### 8.4. Rincian per Material

Menampilkan statistik rak yang dikelompokkan berdasarkan jenis material:

- **SiC** (Silicon Carbide) -- 200 siklus maksimum default
- **Cordierite** -- 150 siklus maksimum default
- **Mullite** -- 300 siklus maksimum default
- **Alumina** -- 250 siklus maksimum default

Untuk setiap material: jumlah aktif, jumlah dihapus, rata-rata umur pakai.

### 8.5. Tren Biaya Penghapusan Bulanan

Grafik batang 6 bulan yang menunjukkan biaya penghapusan rak bulanan dalam IDR. Berguna untuk:

- Melacak tren OPEX
- Mengidentifikasi lonjakan biaya tak terduga
- Merencanakan anggaran pengadaan rak

---

## 9. Izin Pembersihan Data PM

Fitur sementara yang memungkinkan CEO memberikan atau mencabut kemampuan Production Manager untuk menghapus data:

| Izin | Deskripsi |
|---|---|
| **PM dapat menghapus tugas** | Izinkan PM menghapus tugas |
| **PM dapat menghapus posisi** | Izinkan PM menghapus posisi pesanan |
| **PM dapat menghapus pesanan** | Izinkan PM menghapus seluruh pesanan |

> **Peringatan**: Ini adalah izin yang bersifat destruktif. Aktifkan hanya ketika PM perlu membersihkan data uji coba atau mengoreksi kesalahan. Nonaktifkan untuk operasi normal.

Kartu ini muncul per pabrik. Centang untuk mengaktifkan/menonaktifkan.

---

## 10. Manajemen Karyawan

Navigasi ke `/ceo/employees` untuk mengelola karyawan di semua pabrik.

### 10.1. Fitur

- Lihat semua karyawan di semua pabrik dalam satu tempat
- Filter berdasarkan pabrik, peran, dan status aktif
- Lihat catatan kehadiran
- Lihat data penggajian (hukum Indonesia: PPh 21, BPJS, lembur sesuai PP 35/2021)

### 10.2. Ikhtisar Penggajian

Tampilan karyawan CEO mencakup agregasi penggajian:

- Total biaya penggajian per pabrik
- Rincian berdasarkan peran
- Biaya lembur
- Kontribusi pajak dan BPJS

> **Penting**: Data gaji dikontrol aksesnya. Hanya peran CEO dan Owner yang dapat melihat informasi penggajian di semua pabrik.

---

## 11. Laporan Keuangan

### 11.1. Halaman Laporan

Navigasi ke `/reports` untuk analitik komprehensif:

- **Ringkasan Pesanan** -- jumlah pesanan, tingkat penyelesaian, lead time
- **Pemanfaatan Kiln** -- frekuensi pembakaran, penggunaan kapasitas, waktu idle
- **Analitik Produksi** -- tren output, metrik efisiensi

### 11.2. Ekspor Harian CEO

Klik tombol **Ekspor Excel** di dashboard CEO untuk mengunduh laporan harian komprehensif yang mencakup:

- Semua KPI untuk hari ini
- Data perbandingan pabrik
- Ringkasan pesanan aktif
- Daftar defisit material
- Ringkasan tugas

File ekspor diberi nama `ceo-daily-YYYY-MM-DD.xlsx`.

---

## 12. Pengawasan Gamifikasi

### 12.1. Sistem Poin

Pekerja mendapatkan poin melalui kerja yang akurat:

| Akurasi | Poin |
|---|---|
| +/- 1% | 10 poin |
| +/- 3% | 7 poin |
| +/- 5% | 5 poin |
| +/- 10% | 3 poin |
| Lainnya | 1 poin |

Poin tambahan:
- **Bonus verifikasi foto**: +2 poin per foto yang diverifikasi

Poin terakumulasi tahunan dan direset pada 1 Januari.

### 12.2. Papan Peringkat

Papan peringkat bulanan terlihat di `/gamification`. Sebagai CEO, Anda dapat:

- Melihat papan peringkat untuk semua pabrik
- Melihat kinerja pekerja individual
- Memantau lencana pencapaian

### 12.3. Tantangan Harian

Sistem menghasilkan tantangan harian untuk pekerja. Sebagai CEO, Anda dapat melihat tingkat penyelesaian tantangan dan metrik keterlibatan secara keseluruhan.

### 12.4. Pemantauan Force Unblock

Ketika PM menggunakan Smart Force Unblock, Anda menerima notifikasi Telegram. Pantau ini dengan cermat -- force unblock yang sering mungkin menunjukkan masalah sistemik.

---

## 13. Ekspor & Pelaporan

### 13.1. Ekspor yang Tersedia

| Ekspor | Format | Akses |
|---|---|---|
| Laporan Harian CEO | Excel (.xlsx) | Dashboard CEO > Ekspor Excel |
| Detail Pesanan | PDF | Halaman Detail Pesanan > Ekspor |
| Jadwal Produksi | PDF | Halaman Jadwal > Ekspor |

### 13.2. Laporan Otomatis

Bot Telegram mengirim laporan otomatis:

- **Briefing Pagi** (harian): Hasil kemarin, rencana hari ini, masalah pemblokir
- **Ringkasan Sore** (18:00): Hasil produksi harian
- **Peringatan Kehadiran**: Notifikasi saat 3+ kekosongan kehadiran terdeteksi

---

## 14. Perintah Bot Telegram

Bot Telegram (`@LeanOpsAI_bot`) menyediakan perintah khusus CEO:

| Perintah | Deskripsi |
|---|---|
| `/start` | Inisialisasi koneksi bot |
| `/ceoreport` | Dapatkan laporan harian CEO komprehensif |
| `/mystats` | Lihat statistik interaksi pribadi |
| `/leaderboard` | Lihat papan peringkat pekerja |
| `/stock` | Periksa level stok material |
| `/help` | Daftar semua perintah yang tersedia |

### 14.1. Notifikasi Otomatis

Sebagai CEO, Anda secara otomatis menerima:

- **Peringatan force unblock** -- saat PM menggunakan Smart Force Unblock pada posisi apa pun
- **Kekosongan kehadiran** -- saat 3+ pekerja absen
- **Anomali kualitas** -- saat tingkat cacat melonjak di atas ambang batas
- **Pesanan masuk** -- pesanan baru diterima dari webhook Sales

### 14.2. Eskalasi Malam

Masalah kritis yang terdeteksi di luar jam kerja mengikuti jalur eskalasi:

1. **MORNING** -- notifikasi diantrekan untuk pengiriman pagi
2. **REPEAT** -- kirim pengingat jika belum dikonfirmasi
3. **CALL** -- eskalasi ke panggilan telepon jika masih belum dikonfirmasi

---

## 15. Pengambilan Keputusan Berbasis Data

### 15.1. Checklist Review Harian

Setiap pagi, tinjau hal-hal berikut:

1. **Kartu KPI** -- ada metrik di bawah target?
2. **Jumlah Tugas Pemblokir** -- ada yang mandek?
3. **Defisit Material** -- ada produksi yang berisiko?
4. **Kesehatan Buffer** -- ada posisi di zona merah?
5. **Jadwal Kiln** -- ada kiln yang menganggur?

### 15.2. Analisis Mingguan

| Pertanyaan | Di Mana Menemukan Jawaban |
|---|---|
| Pabrik mana yang berkinerja terbaik? | Tab Perbandingan Pabrik > Tabel perbandingan |
| Apakah tenggat waktu terpenuhi? | KPI: Tingkat Tepat Waktu |
| Apakah kualitas membaik? | KPI: Tingkat Cacat + Tren kualitas |
| Apakah kiln digunakan secara efisien? | Tab Kiln + KPI: Pemanfaatan Kiln |
| Berapa anggaran penggantian rak? | Widget OPEX Rak Kiln > Proyeksi |

### 15.3. Rasio Kunci yang Dipantau

| Rasio | Baik | Perhatian | Kritis |
|---|---|---|---|
| Pengiriman Tepat Waktu | > 90% | 80-90% | < 80% |
| Tingkat Cacat | < 3% | 3-5% | > 5% |
| Pemanfaatan Kiln | > 75% | 60-75% | < 60% |
| OEE | > 85% | 70-85% | < 70% |

### 15.4. Kapan Harus Intervensi

Intervensi secara langsung ketika:

- **Posisi zona buffer merah** melebihi 20% dari pekerjaan aktif
- **Pemanfaatan kiln** turun di bawah 60% selama lebih dari 3 hari
- **Defisit material** memblokir 5+ posisi secara bersamaan
- **Force unblock** terjadi lebih dari 3 kali per minggu di satu pabrik

---

## 16. Referensi Navigasi

| Halaman | URL | Tujuan |
|---|---|---|
| Dashboard CEO | `/ceo` | Pusat komando utama |
| Karyawan CEO | `/ceo/employees` | Semua karyawan dan penggajian lintas pabrik |
| Laporan | `/reports` | Laporan produksi dan analitik |
| Gamifikasi | `/gamification` | Poin, papan peringkat, pencapaian |
| Detail Pesanan | `/orders/:id` | Tampilan detail pesanan tertentu |
| Tablo | `/tablo` | Papan tampilan produksi layar penuh |
| Pengaturan | `/settings` | Pengaturan akun pribadi |

---

## 17. Tips dan Praktik Terbaik

> **Rutinitas pagi**: Buka dashboard CEO dalam mode "Semua Pabrik". Periksa kartu KPI terlebih dahulu, lalu pindai Feed Aktivitas untuk kejadian semalam. Beralih ke pabrik individual hanya saat menyelidiki masalah tertentu.

> **Irama mingguan**: Ekspor laporan harian CEO setiap Jumat. Bandingkan data minggu ini dengan minggu sebelumnya. Cari tren, bukan hanya potret.

> **Perbandingan pabrik**: Ketika satu pabrik terus berkinerja buruk, telusuri metrik spesifiknya. Penyebab umum: masalah pasokan material, penumpukan pemeliharaan kiln, kekurangan tenaga kerja.

> **OPEX rak**: Tinjau proyeksi 30 hari secara mingguan. Pesan rak setidaknya 2 minggu sebelum tanggal penggantian yang diproyeksikan untuk menghindari waktu henti produksi.

> **Integrasi Telegram**: Jaga agar bot Telegram tetap aktif. Notifikasi force unblock dan peringatan kehadiran memberikan peringatan dini penting yang mungkin tidak terlihat di dashboard.

> **Keputusan berbasis data**: Jangan pernah mendasarkan keputusan pada data satu hari saja. Gunakan fitur Ekspor Excel untuk melacak tren selama berminggu-minggu dan berbulan-bulan. Lonjakan jangka pendek (baik positif maupun negatif) biasanya hanya gangguan, bukan sinyal.

---

*Panduan ini mencakup fitur Moonjar PMS v1.0 untuk peran CEO. Untuk dukungan teknis, hubungi administrator sistem.*
