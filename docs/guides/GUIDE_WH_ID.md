# Panduan Gudang -- Moonjar PMS

> Versi: 1.0 | Tanggal: 2026-04-06
> Moonjar Production Management System

---

## Daftar Isi

1. [Memulai](#1-memulai)
2. [Ringkasan Dashboard](#2-ringkasan-dashboard)
3. [Manajemen Inventaris](#3-manajemen-inventaris)
4. [Peringatan Stok Rendah](#4-peringatan-stok-rendah)
5. [Transaksi Material](#5-transaksi-material)
6. [Pemrosesan Foto Pengiriman](#6-pemrosesan-foto-pengiriman)
7. [Manajemen Barang Jadi](#7-manajemen-barang-jadi)
8. [Rekonsiliasi](#8-rekonsiliasi)
9. [Pengiriman Mana](#9-pengiriman-mana)
10. [Permintaan Pembelian](#10-permintaan-pembelian)
11. [Perintah Bot Telegram](#11-perintah-bot-telegram)
12. [Referensi Navigasi](#12-referensi-navigasi)
13. [Tips dan Praktik Terbaik](#13-tips-dan-praktik-terbaik)

---

## 1. Memulai

### 1.1. Masuk ke Sistem

1. Buka dashboard Moonjar PMS di browser Anda.
2. Masuk menggunakan salah satu metode:
   - **Google OAuth** -- klik "Sign in with Google"
   - **Email dan kata sandi** -- masukkan kredensial Anda dan klik "Login"
3. Setelah autentikasi, sistem mendeteksi peran Anda dan mengarahkan ke `/warehouse` -- dashboard Gudang.

### 1.2. Pemilihan Pabrik

Saat login, sistem memeriksa penugasan pabrik Anda:

- **Satu pabrik**: Terpilih otomatis, dropdown tidak terlihat.
- **Beberapa pabrik**: Dropdown pemilih pabrik muncul di pojok kanan atas.

> **Penting**: Transaksi material bersifat spesifik per pabrik. Selalu pastikan pabrik yang benar terpilih sebelum menerima material atau melakukan audit.

### 1.3. Kemampuan Peran

Sebagai staf Gudang, Anda dapat:

- Melihat dan mengelola inventaris material
- Menerima pengiriman material yang masuk
- Melakukan audit inventaris (penghitungan stok)
- Melihat riwayat transaksi material
- Memproses foto pengiriman
- Mengelola inventaris barang jadi
- Melakukan rekonsiliasi
- Melacak pengiriman Mana
- Melihat dan merespons permintaan pembelian

---

## 2. Ringkasan Dashboard

Dashboard Gudang (`/warehouse`) menampilkan ringkasan tanggung jawab utama Anda.

### 2.1. Kartu KPI

Tiga metrik utama di atas:

| KPI | Warna | Deskripsi |
|---|---|---|
| **Total Material** | Abu-abu | Jumlah total material dalam sistem |
| **Stok Rendah** | Oranye | Material dengan saldo di bawah batas minimum |
| **Permintaan Tertunda** | Biru | Permintaan pembelian yang menunggu tindakan |

### 2.2. Tab

| Tab | Tujuan |
|---|---|
| **Inventaris** | Daftar inventaris material lengkap dengan saldo terkini |
| **Stok Rendah** | Tampilan filter material di bawah batas minimum |
| **Transaksi** | Transaksi material terbaru dari semua jenis |
| **Permintaan** | Permintaan pembelian yang memerlukan perhatian |

---

## 3. Manajemen Inventaris

### 3.1. Melihat Inventaris

Tab Inventaris menampilkan semua material untuk pabrik yang dipilih:

| Kolom | Deskripsi |
|---|---|
| **Nama** | Nama material |
| **Kode** | Kode yang dibuat sistem (misal, M-0042) |
| **Jenis** | Subkelompok material (pigmen, oksida, frit, dll.) |
| **Saldo** | Jumlah stok saat ini |
| **Saldo Min** | Ambang batas minimum untuk peringatan |
| **Satuan** | Satuan pengukuran (kg, g, L, ml, pcs, m, m²) |
| **Status** | "OK" (hijau) atau jumlah defisit (merah) |

### 3.2. Menerima Material

Saat pengiriman tiba di gudang:

1. Temukan material di tab Inventaris.
2. Klik tombol **Terima** (ikon panah atas).
3. Dialog Transaksi terbuka dalam mode "Terima".
4. Masukkan:
   - **Jumlah** -- jumlah yang diterima
   - **Catatan** -- referensi pengiriman, nomor batch, info supplier
5. Klik **"Terima"**.

Saldo diperbarui segera.

> **Penting**: Selalu hitung fisik pengiriman sebelum memasukkan jumlah. Jangan hanya mengandalkan invoice supplier.

### 3.3. Audit Inventaris

Saat Anda perlu mengoreksi saldo (hitungan fisik berbeda dari sistem):

1. Temukan material di tab Inventaris.
2. Klik tombol **Audit** (ikon tiga garis).
3. Dialog Transaksi terbuka dalam mode "Audit Inventaris".
4. Anda melihat **saldo sistem saat ini** di atas.
5. Masukkan **jumlah hitungan fisik aktual** di kolom "Saldo aktual baru".
6. Sistem secara otomatis menghitung **selisih** (hijau = surplus, merah = defisit).
7. Masukkan **Alasan** untuk perbedaan (wajib).
8. Klik **"Konfirmasi Audit"**.

> **Peringatan**: Selalu berikan alasan yang jujur dan jelas untuk audit. Catatan ini ditinjau oleh manajemen. Contoh: "Tumpah saat transfer", "Kesalahan pengukuran pada hitungan sebelumnya", "Menemukan stok tambahan di penyimpanan sekunder".

---

## 4. Peringatan Stok Rendah

### 4.1. Cara Kerja Peringatan

Material dengan saldo di bawah ambang batas minimum ditandai:

- Latar belakang baris menjadi merah di tabel inventaris
- Kolom Status menampilkan "Defisit: X.X unit" dalam merah
- Badge jumlah muncul di tab Stok Rendah

### 4.2. Merespons Stok Rendah

Saat Anda melihat peringatan stok rendah:

1. Periksa tab **Permintaan** untuk melihat apakah permintaan pembelian sudah ada
2. Jika belum ada permintaan, beritahu Production Manager
3. Periksa apakah material tersedia di bagian gudang lain
4. Untuk material kritis yang memblokir produksi, tandai sebagai mendesak

### 4.3. Override Saldo Minimum

Production Manager dapat mengubah ambang batas saldo minimum untuk material tertentu. Jika Anda melihat material yang ambang batasnya terlihat salah, laporkan ke PM.

---

## 5. Transaksi Material

### 5.1. Jenis Transaksi

| Jenis | Arah | Deskripsi | Warna |
|---|---|---|---|
| `receive` | Masuk | Material dikirim ke gudang | Hijau |
| `consume` | Keluar | Material digunakan dalam produksi (glazing, engobe) | Merah |
| `manual_write_off` | Keluar | Pengurangan stok manual | Merah |
| `reserve` | Tahan | Dicadangkan untuk posisi tertentu | Biru |
| `unreserve` | Lepas | Cadangan dibatalkan | Biru |
| `audit` (inventaris) | Koreksi | Penyesuaian hitungan stok | Kuning |

### 5.2. Melihat Riwayat Transaksi

1. Temukan material di tabel inventaris.
2. Klik tombol **Riwayat** (ikon Hst).
3. Dialog terbuka menampilkan semua transaksi, terbaru di atas.
4. Setiap entri menampilkan: tanggal, jenis, jumlah (+/-), siapa yang melakukan, dan catatan.

### 5.3. Memahami Konsumsi

Konsumsi material terjadi otomatis saat posisi maju melalui produksi:

- **Tahap glazing**: Glasir dan engobe dikonsumsi berdasarkan aturan konsumsi
- **Sistem menghitung**: jumlah yang dibutuhkan berdasarkan area posisi dan tingkat konsumsi per m²
- **Jika tidak cukup**: Posisi diblokir dengan status `INSUFFICIENT_MATERIALS`

Anda tidak perlu memasukkan konsumsi secara manual -- sistem yang menangani. Tetapi jika Anda melihat ketidaksesuaian, lakukan audit inventaris.

---

## 6. Pemrosesan Foto Pengiriman

### 6.1. Ikhtisar

Saat pengiriman tiba, Anda dapat memotret pengiriman dan menggunakan pemrosesan berbasis AI untuk mengidentifikasi material.

### 6.2. Cara Menggunakan

1. Ambil foto pengiriman (label, kemasan, invoice).
2. Kirim foto ke bot Telegram atau unggah melalui sistem.
3. AI memproses foto menggunakan OCR untuk mengekstrak nama dan jumlah material.
4. Sistem mencoba mencocokkan item yang diekstrak dengan material yang ada di database.
5. Tinjau kecocokan dan konfirmasi.

### 6.3. Pencocokan Material Cerdas

Sistem menggunakan dua strategi pencocokan:

1. **Pencocokan berbasis token** -- memecah nama material menjadi token dan menemukan kecocokan terbaik
2. **Fallback AI** -- jika pencocokan token tidak pasti, AI digunakan untuk pencocokan lebih akurat

### 6.4. Alur Konfirmasi

Setelah pemrosesan AI, Anda melihat daftar material yang dicocokkan:

- **Kecocokan yakin** (hijau) -- otomatis terhubung, verifikasi dan konfirmasi
- **Kecocokan tidak pasti** (kuning) -- tebakan terbaik AI, tinjau dengan cermat
- **Tidak cocok** (merah) -- tidak ada material yang ada, Anda bisa buat baru atau lewati

Untuk setiap item:
- Konfirmasi kecocokan
- Edit material yang dicocokkan (jika salah)
- Sesuaikan jumlah
- Lewati item yang tidak ingin Anda terima

---

## 7. Manajemen Barang Jadi

### 7.1. Ikhtisar

Navigasi ke `/warehouse/finished-goods` untuk mengelola inventaris produk jadi.

### 7.2. Fitur

Barang jadi adalah produk yang telah menyelesaikan semua tahap produksi:

- **Tampilan inventaris** -- semua produk jadi dengan jumlah dan lokasi
- **Pengecekan ketersediaan** -- verifikasi apakah produk tertentu tersedia di stok untuk pesanan
- **Pelacakan lokasi** -- bagian gudang mana yang menyimpan produk mana

### 7.3. Ketersediaan Stok

Saat memeriksa stok untuk pengiriman:

1. Buka halaman Barang Jadi.
2. Cari atau filter berdasarkan produk (warna, ukuran, koleksi).
3. Periksa jumlah yang tersedia.
4. Tandai item untuk pengiriman jika tersedia.

---

## 8. Rekonsiliasi

### 8.1. Ikhtisar

Navigasi ke `/warehouse/reconciliations` untuk sesi pemeriksaan inventaris multi-material formal.

### 8.2. Apa Itu Rekonsiliasi?

Rekonsiliasi adalah audit stok komprehensif dan terjadwal yang mencakup beberapa material sekaligus. Berbeda dengan audit material individual, rekonsiliasi adalah sesi formal dengan cakupan dan proses persetujuan yang jelas.

### 8.3. Alur Kerja Rekonsiliasi

1. **Buat Sesi** -- tentukan cakupan (material mana, bagian gudang mana)
2. **Hitung** -- hitung fisik setiap material dalam cakupan
3. **Masukkan Hasil** -- input hitungan aktual untuk setiap material
4. **Tinjau Ketidaksesuaian** -- sistem menyoroti perbedaan antara yang diharapkan dan aktual
5. **Kirim** -- kirim untuk review dan persetujuan
6. **Setuju/Tolak** -- PM atau admin meninjau dan menyetujui

### 8.4. Mencatat Ketidaksesuaian

Untuk setiap ketidaksesuaian yang ditemukan selama rekonsiliasi:

| Kolom | Deskripsi |
|---|---|
| Yang Diharapkan | Saldo sistem |
| Aktual | Hitungan fisik |
| Selisih | Dihitung otomatis |
| Alasan | Penjelasan untuk ketidaksesuaian |

Alasan umum:
- Konsumsi yang tidak tercatat
- Tumpah atau limbah
- Kesalahan pengukuran pada hitungan sebelumnya
- Transfer antar bagian yang tidak tercatat
- Pengiriman kurang dari supplier yang tidak terdeteksi saat penerimaan

---

## 9. Pengiriman Mana

### 9.1. Ikhtisar

Navigasi ke `/warehouse/mana-shipments` untuk melacak pengiriman antar pabrik atau pusat distribusi.

### 9.2. Melacak Pengiriman

Halaman Pengiriman Mana menampilkan:

- ID Pengiriman dan tanggal
- Asal dan tujuan
- Item yang termasuk (material atau barang jadi)
- Informasi kurir
- Status pelacakan (disiapkan, dalam perjalanan, terkirim)

### 9.3. Membuat Catatan Pengiriman

1. Klik **+ Pengiriman Baru**.
2. Pilih asal dan tujuan.
3. Tambahkan item ke pengiriman.
4. Masukkan detail kurir.
5. Kirim.

### 9.4. Memperbarui Status Pengiriman

Seiring pengiriman berlangsung, perbarui statusnya:

- **Disiapkan** -- item dikemas dan siap
- **Dalam Perjalanan** -- pengiriman telah meninggalkan asal
- **Terkirim** -- pengiriman telah tiba di tujuan

---

## 10. Permintaan Pembelian

### 10.1. Melihat Permintaan

Tab **Permintaan** menampilkan permintaan pembelian yang relevan dengan gudang:

| Kolom | Deskripsi |
|---|---|
| Material | Apa yang perlu dibeli |
| Jumlah | Jumlah yang diminta |
| Status | Tertunda, Disetujui, Dikirim, Diterima |
| Diminta Oleh | Siapa yang membuat permintaan |
| Tanggal | Kapan permintaan dibuat |

### 10.2. Peran Anda dalam Permintaan Pembelian

Sebagai staf gudang, Anda:

1. **Verifikasi kebutuhan** -- konfirmasi material memang rendah
2. **Terima pengiriman** -- saat pembelian tiba, terima ke inventaris
3. **Perbarui status** -- tandai permintaan sebagai diterima setelah penerimaan

---

## 11. Perintah Bot Telegram

| Perintah | Deskripsi |
|---|---|
| `/start` | Inisialisasi koneksi bot |
| `/stock` | Periksa level stok material |
| `/mystats` | Lihat statistik Anda |
| `/help` | Daftar semua perintah yang tersedia |

### 11.1. Foto Pengiriman via Telegram

Anda dapat mengirim foto pengiriman langsung ke bot Telegram:

1. Ambil foto label/invoice pengiriman.
2. Kirim foto ke bot.
3. Bot memproses gambar dan menampilkan material yang cocok.
4. Konfirmasi atau edit kecocokan menggunakan tombol inline.
5. Material diterima ke inventaris secara otomatis.

### 11.2. Notifikasi Otomatis

Anda menerima notifikasi untuk:

- Peringatan stok rendah untuk pabrik Anda
- Permintaan pembelian baru
- Notifikasi pengiriman masuk
- Briefing pagi dengan ringkasan stok

---

## 12. Referensi Navigasi

| Halaman | URL | Tujuan |
|---|---|---|
| Dashboard Gudang | `/warehouse` | Dashboard utama dengan inventaris, peringatan, permintaan |
| Barang Jadi | `/warehouse/finished-goods` | Inventaris produk jadi |
| Rekonsiliasi | `/warehouse/reconciliations` | Sesi audit stok formal |
| Pengiriman Mana | `/warehouse/mana-shipments` | Pelacakan pengiriman antar pabrik |
| Pengaturan | `/settings` | Pengaturan akun pribadi |

---

## 13. Tips dan Praktik Terbaik

> **Hitung sebelum memasukkan**: Selalu hitung fisik pengiriman sebelum memasukkannya ke sistem. Invoice supplier bisa mengandung kesalahan.

> **Audit secara rutin**: Jangan menunggu sesi rekonsiliasi formal. Jika ada yang terlihat tidak beres untuk material tertentu, segera lakukan audit individual.

> **Beri label pada semuanya**: Pastikan semua material di gudang diberi label jelas dengan kode sistem. Ini mencegah kebingungan dan mempercepat rekonsiliasi.

> **First In, First Out (FIFO)**: Selalu gunakan stok lama sebelum stok baru. Ini sangat penting untuk material yang bisa rusak seiring waktu (beberapa glasir, bahan kimia tertentu).

> **Laporkan ketidaksesuaian segera**: Jika Anda menemukan ketidaksesuaian signifikan selama pemeriksaan stok apa pun, laporkan ke PM segera. Jangan menunggu akhir hari.

> **Gunakan foto pengiriman**: Pencocokan AI menghemat waktu secara signifikan dibandingkan memasukkan setiap item secara manual. Biasakan memotret setiap pengiriman.

> **Jaga bagian gudang tetap teratur**: Sistem melacak bagian mana yang menyimpan material mana. Jika Anda memindahkan material antar bagian, perbarui sistem.

> **Stok rendah bukan kesalahan Anda**: Tugas Anda adalah melaporkannya dengan akurat dan menerima material saat tiba. Keputusan dan waktu pembelian adalah tanggung jawab Purchaser dan PM.

---

*Panduan ini mencakup fitur Moonjar PMS v1.0 untuk peran Gudang. Untuk dukungan teknis, hubungi administrator sistem.*
