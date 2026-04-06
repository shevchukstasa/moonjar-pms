# Panduan Sortir & Packing -- Moonjar PMS

> Versi: 1.0 | Tanggal: 2026-04-06
> Moonjar Production Management System

---

## Daftar Isi

1. [Memulai](#1-memulai)
2. [Ringkasan Dashboard](#2-ringkasan-dashboard)
3. [Alur Kerja Sortir](#3-alur-kerja-sortir)
4. [Penilaian Kualitas Saat Sortir](#4-penilaian-kualitas-saat-sortir)
5. [Alur Kerja Packing](#5-alur-kerja-packing)
6. [Tab Grinding](#6-tab-grinding)
7. [Foto Packing](#7-foto-packing)
8. [Tugas](#8-tugas)
9. [Penanganan Koleksi Stok](#9-penanganan-koleksi-stok)
10. [Perintah Bot Telegram](#10-perintah-bot-telegram)
11. [Referensi Navigasi](#11-referensi-navigasi)
12. [Tips dan Praktik Terbaik](#12-tips-dan-praktik-terbaik)

---

## 1. Memulai

### 1.1. Masuk ke Sistem

1. Buka dashboard Moonjar PMS di browser (bisa juga di HP dan tablet).
2. Masuk menggunakan salah satu metode:
   - **Google OAuth** -- klik "Sign in with Google"
   - **Email dan kata sandi** -- masukkan kredensial Anda dan klik "Login"
3. Setelah autentikasi, sistem mengarahkan ke `/sorter-packer` -- dashboard Sortir & Packing.

### 1.2. Pemilihan Pabrik

Pabrik Anda biasanya terpilih otomatis. Jika Anda bekerja di beberapa lokasi, gunakan dropdown pabrik di pojok kanan atas.

### 1.3. Kemampuan Peran

Sebagai Sortir Packer, Anda dapat:

- Menyortir ubin yang telah dibakar berdasarkan grade kualitas
- Mengemas ubin yang sudah disortir ke dalam kardus
- Mengunggah foto packing sebagai bukti
- Memproses ubin untuk grinding (cacat minor)
- Menyelesaikan tugas yang diberikan
- Memisahkan posisi saat diperlukan (dengan persetujuan)
- Memeriksa ketersediaan stok

---

## 2. Ringkasan Dashboard

Dashboard Sortir Packer (`/sorter-packer`) dirancang untuk kesederhanaan dan penggunaan di perangkat mobile.

### 2.1. Kartu KPI

Tiga kartu ringkas di atas:

| KPI | Warna | Deskripsi |
|---|---|---|
| **Menunggu Sortir** | Oranye | Posisi yang dipindahkan ke sortir, menunggu Anda |
| **Sudah Dikemas** | Hijau | Posisi yang sudah Anda kemas |
| **Tugas Terbuka** | Biru | Tugas aktif yang ditugaskan kepada Anda |

### 2.2. Tab

| Tab | Tujuan |
|---|---|
| **Sortir** | Posisi yang menunggu disortir setelah pembakaran |
| **Packing** | Posisi yang siap dikemas ke dalam kardus |
| **Grinding** | Posisi yang dikirim untuk grinding (perbaikan cacat minor) |
| **Foto** | Pengunggahan dan manajemen foto packing |
| **Tugas** | Tugas yang ditugaskan ke peran Anda |

---

## 3. Alur Kerja Sortir

### 3.1. Ikhtisar

Setelah ubin keluar dari kiln dan lulus QC, ubin dipindahkan ke sortir. Tugas Anda adalah memeriksa setiap ubin, menilai kualitasnya, dan menyiapkan untuk pengemasan.

### 3.2. Menyortir Posisi

1. Buka tab **Sortir**.
2. Anda melihat posisi dengan status `transferred_to_sorting`.
3. Klik pada posisi untuk melihat detailnya:
   - Nomor pesanan, warna, ukuran, koleksi
   - Jumlah yang diharapkan
   - Catatan QC dari Quality Manager
4. Sortir ubin secara fisik.
5. Perbarui posisi:
   - Masukkan jumlah ubin grade A
   - Masukkan jumlah ubin grade B (jika ada)
   - Masukkan jumlah yang ditolak
   - Masukkan jumlah ubin yang dikirim ke grinding
6. Konfirmasi hasil sortir.

### 3.3. Yang Harus Diperiksa

Selama sortir, periksa setiap ubin untuk:

| Pemeriksaan | Lulus | Gagal |
|---|---|---|
| **Permukaan** | Halus, tanpa cacat | Lubang jarum, crawling, tonjolan |
| **Warna** | Konsisten, sesuai pesanan | Variasi, warna salah |
| **Tepi** | Bersih, tanpa gumpil | Gumpil, kasar |
| **Bentuk** | Datar, dimensi benar | Melengkung, terlalu besar/kecil |
| **Pola** | Jelas, posisi tepat | Smudged, tidak rata |

### 3.4. Menangani Ubin Cacat

Saat Anda menemukan ubin cacat:

- **Cacat permukaan minor** -- pertimbangkan kirim ke grinding
- **Variasi warna** -- pisahkan sebagai grade B jika masih bisa dijual
- **Cacat struktural** (retak, melengkung) -- tolak
- **Produk salah** -- laporkan ke PM segera

---

## 4. Penilaian Kualitas Saat Sortir

### 4.1. Definisi Grade

| Grade | Kriteria | Tujuan |
|---|---|---|
| **A** | Kualitas sempurna, memenuhi semua spesifikasi | Kemas untuk pelanggan |
| **B** | Masalah kosmetik minor, fungsional dan layak jual | Kemas terpisah, tandai sebagai grade B |
| **Tolak** | Tidak memenuhi standar kualitas minimum | Hapus |
| **Grinding** | Cacat permukaan minor yang bisa diperbaiki | Kirim ke tahap grinding |

### 4.2. Mencatat Grade

Untuk setiap posisi yang Anda sortir, sistem mengharapkan rincian:

```
Total diterima: 100 ubin
Grade A: 85 ubin
Grade B: 8 ubin
Grinding: 4 ubin
Ditolak: 3 ubin
```

Total harus sama dengan jumlah yang diterima dari pembakaran.

> **Penting**: Jujur dan konsisten dalam penilaian. Sistem melacak akurasi Anda dari waktu ke waktu, dan Anda mendapatkan poin untuk kerja yang presisi.

---

## 5. Alur Kerja Packing

### 5.1. Ikhtisar

Setelah sortir, ubin grade A dan grade B berpindah ke tab **Packing**.

### 5.2. Mengemas Posisi

1. Buka tab **Packing**.
2. Pilih posisi untuk dikemas.
3. Lihat spesifikasi packing:
   - **Jenis kardus** -- kardus mana yang digunakan (berdasarkan ukuran ubin)
   - **Ubin per kardus** -- berapa ubin muat dalam satu kardus
   - **Kebutuhan spacer** -- apakah spacer diperlukan antar ubin
   - **Total kardus yang dibutuhkan** -- dihitung dari jumlah dan kapasitas kardus
4. Kemas ubin secara fisik.
5. Di sistem, perbarui:
   - Jumlah kardus yang dikemas
   - Konfirmasi jumlah ubin per kardus
   - Catat masalah packing apa pun
6. Ubah status posisi menjadi **Dikemas**.

### 5.3. Jenis Kardus

Sistem memiliki jenis kardus yang dikonfigurasi dengan kapasitas tertentu:

| Jenis Kardus | Penggunaan Tipikal | Kapasitas |
|---|---|---|
| Kecil | Ubin hingga 10x10 cm | Bervariasi berdasarkan ketebalan ubin |
| Sedang | Ubin 10-20 cm | Bervariasi berdasarkan ketebalan ubin |
| Besar | Ubin 20-30 cm | Bervariasi berdasarkan ketebalan ubin |
| Kustom | Bentuk tidak beraturan, wastafel | Sesuai spesifikasi |

Kapasitas tepat bergantung pada ukuran ubin, ketebalan, dan kebutuhan spacer -- sistem menghitung ini untuk Anda.

### 5.4. Kebutuhan Spacer

Beberapa produk memerlukan spacer antar ubin untuk mencegah kerusakan:

- **Ubin berglasir** -- spacer diperlukan (glasir bisa tergores)
- **Ubin tanpa glasir** -- spacer mungkin tidak diperlukan
- **Pola halus** -- padding ekstra disarankan

Ikuti spesifikasi packing di sistem.

---

## 6. Tab Grinding

### 6.1. Ikhtisar

Ubin yang dikirim ke grinding selama sortir muncul di tab **Grinding**. Setelah grinding selesai:

1. Periksa ulang ubin.
2. Jika cacat sudah diperbaiki, tandai sebagai grade A atau grade B.
3. Jika cacat masih ada, tandai sebagai Ditolak.
4. Perbarui posisi di sistem.

### 6.2. Melacak Hasil Grinding

Untuk setiap ubin yang melalui grinding:

- Catat apakah grinding berhasil
- Perbarui grade (A, B, atau Tolak)
- Sistem menyesuaikan jumlah posisi

---

## 7. Foto Packing

### 7.1. Ikhtisar

Buka tab **Foto** untuk mengelola foto packing. Foto berfungsi sebagai bukti kualitas dan kuantitas packing.

### 7.2. Mengunggah Foto

1. Buka tab **Foto**.
2. Pilih posisi yang ingin Anda foto.
3. Klik **Unggah Foto** atau seret dan lepas.
4. Sistem menerima format JPEG, PNG, dan WebP.
5. Tambahkan keterangan jika diperlukan.

### 7.3. Apa yang Difoto

Untuk setiap posisi yang dikemas, ambil foto:

- **Kardus terbuka** -- menunjukkan ubin tersusun rapi di dalam
- **Label kardus** -- menunjukkan nomor pesanan, warna, ukuran, jumlah
- **Palet penuh** -- jika beberapa kardus, tunjukkan palet lengkap
- **Kerusakan apa pun** -- jika ubin rusak selama pengemasan

### 7.4. Tips Foto

- Pastikan pencahayaan yang baik
- Sertakan keempat sudut kardus dalam satu foto
- Buat label terbaca dalam foto
- Foto masalah apa pun sebelum melaporkannya

> **Tips**: Foto memberi Anda bonus poin di sistem gamifikasi (+2 poin per foto yang diverifikasi).

---

## 8. Tugas

### 8.1. Ikhtisar

Tab **Tugas** menampilkan tugas yang ditugaskan ke peran Sortir Packer. Jenis tugas umum:

| Jenis Tugas | Deskripsi |
|---|---|
| **Sortir batch** | Sortir batch tertentu dari ubin yang dibakar |
| **Kemas pesanan** | Kemas pesanan tertentu untuk pengiriman |
| **Sortir ulang** | Sortir ulang ubin yang dikembalikan dari QC |
| **Labeling kardus** | Tempel label pada kardus yang sudah dikemas |
| **Siapkan pengiriman** | Kumpulkan dan atur kardus untuk pengiriman |

### 8.2. Menyelesaikan Tugas

1. Klik pada tugas di tab Tugas.
2. Tinjau detail dan persyaratan tugas.
3. Lakukan pekerjaan.
4. Klik **Selesaikan Tugas**.
5. Tambahkan catatan tentang pekerjaan yang diselesaikan.

### 8.3. Prioritas Tugas

Tugas diberi kode warna berdasarkan prioritas:

| Prioritas | Warna | Arti |
|---|---|---|
| **Tinggi** | Merah | Mendesak, kerjakan dulu |
| **Sedang** | Kuning | Prioritas normal |
| **Rendah** | Abu-abu | Bisa menunggu |

Tugas pemblokir (yang mencegah produksi maju) ditandai dengan badge khusus.

---

## 9. Penanganan Koleksi Stok

### 9.1. Apa Itu Koleksi Stok?

Posisi yang ditandai sebagai "Stock" atau "Stok" termasuk dalam koleksi Stok -- ini adalah produk yang diproduksi untuk inventaris, bukan untuk pesanan pelanggan tertentu.

### 9.2. Penanganan Khusus

Item koleksi stok:

- Mungkin memiliki persyaratan packing yang berbeda
- Disimpan di gudang setelah dikemas (tidak langsung dikirim)
- Harus dilabeli dengan jelas sebagai item stok
- Mungkin tidak memiliki tenggat waktu tertentu

Sistem secara otomatis mendeteksi item koleksi Stok dan dapat menyesuaikan alur kerja.

---

## 10. Perintah Bot Telegram

| Perintah | Deskripsi |
|---|---|
| `/start` | Inisialisasi koneksi bot |
| `/mystats` | Lihat statistik sortir/packing Anda |
| `/points` | Periksa poin Anda saat ini |
| `/leaderboard` | Lihat peringkat Anda dibandingkan rekan |
| `/challenge` | Lihat tantangan harian hari ini |
| `/achievements` | Lihat lencana pencapaian Anda |
| `/help` | Daftar semua perintah yang tersedia |

### 10.1. Tantangan Harian

Sistem dapat memberikan tantangan harian seperti:

- "Kemas 50 kardus hari ini" (bonus poin jika selesai)
- "Nol penolakan dalam sortir hari ini"
- "Unggah foto untuk semua posisi yang dikemas"

Periksa `/challenge` setiap pagi.

### 10.2. Notifikasi Otomatis

Anda menerima notifikasi untuk:

- Batch baru siap untuk sortir
- Penugasan tugas
- Poin yang diperoleh
- Pencapaian terbuka
- Briefing pagi dengan rencana harian

---

## 11. Referensi Navigasi

| Halaman | URL | Tujuan |
|---|---|---|
| Dashboard Sortir Packer | `/sorter-packer` | Dashboard utama dengan semua tab |
| Pengaturan | `/settings` | Pengaturan akun pribadi |

Peran Sortir Packer memiliki satu dashboard terfokus dengan semua yang dapat diakses melalui tab.

---

## 12. Tips dan Praktik Terbaik

> **Sortir sebelum mengemas**: Jangan pernah mengemas ubin tanpa menyortirnya terlebih dahulu. Meskipun terlihat baik sekilas, setiap ubin harus diperiksa secara individual.

> **Konsisten dalam penilaian**: Batas antara grade A dan grade B harus konsisten dari hari ke hari. Jika Anda ragu, tanyakan Quality Manager untuk panduan.

> **Foto semuanya**: Foto packing adalah perlindungan Anda. Jika pelanggan mengklaim kerusakan selama pengiriman, foto Anda membuktikan produk meninggalkan pabrik dalam kondisi baik.

> **Tangani ubin dengan hati-hati**: Permukaan berglasir itu halus. Selalu gunakan sarung tangan dan letakkan ubin dengan lembut. Gumpil kecil di tahap ini membuang semua pekerjaan produksi sebelumnya.

> **Periksa tantangan Anda**: Tantangan harian adalah cara bagus untuk mendapatkan poin ekstra. Periksa bot Telegram setiap pagi untuk tantangan hari itu.

> **Laporkan anomali segera**: Jika Anda menerima ubin dari kiln yang terlihat salah (warna salah, ukuran salah, jumlah salah), laporkan ke Production Manager sebelum mulai menyortir. Jangan asumsikan itu benar.

> **Hitung dengan akurat**: Sistem membandingkan hitungan Anda dengan yang dikirim dari pembakaran. Ketidaksesuaian yang konsisten akan ditandai untuk investigasi.

> **Jaga area kerja bersih**: Meja sortir yang bersih berarti lebih sedikit kerusakan tidak sengaja dan pekerjaan lebih cepat. Bersihkan area Anda di akhir setiap shift.

---

*Panduan ini mencakup fitur Moonjar PMS v1.0 untuk peran Sortir Packer. Untuk dukungan teknis, hubungi administrator sistem.*
