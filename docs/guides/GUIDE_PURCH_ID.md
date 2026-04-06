# Panduan Purchaser -- Moonjar PMS

> Versi: 1.0 | Tanggal: 2026-04-06
> Moonjar Production Management System

---

## Daftar Isi

1. [Memulai](#1-memulai)
2. [Ringkasan Dashboard](#2-ringkasan-dashboard)
3. [Permintaan Pembelian Aktif](#3-permintaan-pembelian-aktif)
4. [Manajemen Pengiriman](#4-manajemen-pengiriman)
5. [Defisit Material](#5-defisit-material)
6. [Manajemen Supplier](#6-manajemen-supplier)
7. [Pelacakan Biaya](#7-pelacakan-biaya)
8. [Konsolidasi Pembelian](#8-konsolidasi-pembelian)
9. [Perintah Bot Telegram](#9-perintah-bot-telegram)
10. [Referensi Navigasi](#10-referensi-navigasi)
11. [Tips dan Praktik Terbaik](#11-tips-dan-praktik-terbaik)

---

## 1. Memulai

### 1.1. Masuk ke Sistem

1. Buka dashboard Moonjar PMS di browser Anda.
2. Masuk menggunakan salah satu metode:
   - **Google OAuth** -- klik "Sign in with Google"
   - **Email dan kata sandi** -- masukkan kredensial Anda dan klik "Login"
3. Setelah autentikasi, sistem mengarahkan ke `/purchaser` -- dashboard Purchaser.

### 1.2. Pemilihan Pabrik

Saat login, sistem memeriksa penugasan pabrik Anda:

- **Satu pabrik**: Terpilih otomatis, dropdown tidak terlihat.
- **Beberapa pabrik**: Dropdown pemilih pabrik muncul di pojok kanan atas.

> **Penting**: Permintaan pembelian dan pengiriman supplier bersifat spesifik per pabrik. Pastikan pabrik yang benar terpilih.

### 1.3. Kemampuan Peran

Sebagai Purchaser, Anda dapat:

- Melihat dan mengelola permintaan pembelian
- Melacak pengiriman dari supplier
- Memantau defisit material di seluruh pabrik
- Mengelola informasi supplier
- Memperbarui status permintaan pembelian
- Berkoordinasi dengan gudang untuk penerimaan pengiriman

---

## 2. Ringkasan Dashboard

Dashboard Purchaser (`/purchaser`) adalah ruang kerja harian Anda untuk aktivitas pengadaan.

### 2.1. Kartu KPI

Empat metrik utama di atas:

| KPI | Warna | Deskripsi |
|---|---|---|
| **Permintaan Aktif** | Biru | Permintaan pembelian dalam status tertunda/disetujui/dikirim |
| **Menunggu Persetujuan** | Kuning | Permintaan yang menunggu persetujuan PM |
| **Dalam Perjalanan** | Ungu | Pengiriman yang sedang dalam perjalanan |
| **Material Defisit** | Merah | Material di bawah ambang batas stok minimum |

### 2.2. Tab

| Tab | Tujuan |
|---|---|
| **Aktif** | Permintaan pembelian yang perlu tindakan (tertunda, disetujui, dikirim) |
| **Pengiriman** | Pelacakan pengiriman untuk pesanan yang sudah dikirim |
| **Defisit** | Material yang saat ini di bawah stok minimum |
| **Supplier** | Informasi kontak dan manajemen supplier |

---

## 3. Permintaan Pembelian Aktif

### 3.1. Siklus Hidup Permintaan

Permintaan pembelian mengikuti siklus hidup ini:

| Status | Arti | Tindakan Anda |
|---|---|---|
| **Tertunda** | Dibuat, menunggu persetujuan | Tunggu atau tindak lanjuti dengan PM |
| **Disetujui** | PM menyetujui pembelian | Hubungi supplier, tempatkan pesanan |
| **Dikirim** | Pesanan ditempatkan ke supplier | Lacak pengiriman |
| **Diterima** | Material diterima di gudang | Verifikasi dengan staf gudang |
| **Dibatalkan** | Permintaan dibatalkan | Tidak perlu tindakan |

### 3.2. Melihat Detail Permintaan

Untuk setiap permintaan pembelian, Anda melihat:

| Kolom | Deskripsi |
|---|---|
| Material | Nama dan kode material |
| Jumlah | Jumlah yang diminta |
| Satuan | Satuan pengukuran |
| Stok Saat Ini | Saldo saat ini di gudang |
| Saldo Min | Ambang batas minimum |
| Defisit | Berapa di bawah minimum |
| Status | Status permintaan saat ini |
| Diminta Oleh | Siapa yang membuat permintaan |
| Tanggal | Kapan dibuat |
| Catatan | Konteks tambahan |

### 3.3. Memperbarui Status Permintaan

1. Temukan permintaan di tab **Aktif**.
2. Klik tombol perbarui status.
3. Pilih status baru:
   - **Disetujui** -> **Dikirim**: Setelah menempatkan pesanan ke supplier
   - **Dikirim** -> **Diterima**: Setelah gudang mengkonfirmasi penerimaan
4. Tambahkan catatan (nomor pesanan supplier, tanggal pengiriman yang diharapkan, dll.).
5. Konfirmasi.

### 3.4. Menghapus Permintaan

Jika permintaan tidak lagi diperlukan:

1. Klik tombol hapus pada permintaan.
2. Konfirmasi penghapusan.
3. Tambahkan alasan (opsional tapi disarankan).

> **Catatan**: Hanya permintaan tertunda yang bisa dihapus. Permintaan yang disetujui atau dikirim harus dibatalkan.

---

## 4. Manajemen Pengiriman

### 4.1. Pelacakan Pengiriman

Tab **Pengiriman** menampilkan semua pesanan yang telah dikirim ke supplier:

| Kolom | Deskripsi |
|---|---|
| Material | Apa yang dipesan |
| Supplier | Ke mana pesanan ditempatkan |
| Jumlah | Jumlah yang dipesan |
| Tanggal Pesanan | Kapan pesanan ditempatkan |
| Tanggal Diharapkan | Tanggal pengiriman yang diharapkan |
| Status | Dalam Perjalanan / Diterima / Terlambat |

### 4.2. Pengiriman Terlambat

Pengiriman yang melewati tanggal yang diharapkan ditandai merah. Saat Anda melihat pengiriman terlambat:

1. Hubungi supplier untuk pembaruan status
2. Perbarui tanggal pengiriman yang diharapkan di sistem
3. Jika material kritis (memblokir produksi), beritahu PM segera

### 4.3. Mengkonfirmasi Penerimaan

Saat pengiriman tiba di gudang:

1. Koordinasi dengan staf gudang untuk verifikasi jumlah
2. Perbarui status permintaan pembelian menjadi "Diterima"
3. Staf gudang akan menerima material ke inventaris

---

## 5. Defisit Material

### 5.1. Memahami Defisit

Tab **Defisit** menampilkan semua material yang stok saat ini di bawah ambang batas minimum:

| Kolom | Deskripsi |
|---|---|
| Material | Nama dan kode |
| Saldo Saat Ini | Apa yang ada di stok sekarang |
| Saldo Min | Ambang batas yang memicu peringatan |
| Jumlah Defisit | Berapa di bawah minimum |
| Satuan | Satuan pengukuran |
| Ada Permintaan Aktif | Apakah permintaan pembelian sudah ada |

### 5.2. Memprioritaskan Pembelian

Tidak semua defisit sama mendesaknya. Prioritaskan berdasarkan:

1. **Dampak produksi**: Apakah defisit memblokir posisi aktif?
2. **Waktu tunggu**: Berapa lama supplier perlu untuk mengirim?
3. **Ukuran defisit**: Seberapa jauh di bawah minimum stoknya?
4. **Kekritisan material**: Bisakah produksi berlanjut tanpa material ini?

> **Tips**: Periksa tab Pemblokir di dashboard PM untuk melihat posisi mana yang diblokir oleh kekurangan material. Ini sesuai dengan pembelian paling mendesak Anda.

### 5.3. Membuat Permintaan dari Defisit

1. Lihat material defisit.
2. Jika tidak ada permintaan aktif, klik **Buat Permintaan**.
3. Masukkan jumlah yang dipesan (pertimbangkan memesan di atas minimum untuk buffer kebutuhan masa depan).
4. Tambahkan catatan (supplier yang diinginkan, tingkat urgensi).
5. Kirim -- permintaan masuk ke PM untuk persetujuan.

---

## 6. Manajemen Supplier

### 6.1. Melihat Supplier

Tab **Supplier** mencantumkan semua supplier terdaftar:

| Kolom | Deskripsi |
|---|---|
| Nama | Nama perusahaan supplier |
| Kontak | Orang kontak utama |
| Telepon | Nomor telepon kontak |
| Email | Email kontak |
| Material | Material mana yang disediakan supplier ini |
| Rating | Rating kinerja (jika tersedia) |

### 6.2. Pemilihan Supplier

Saat menempatkan pesanan, pertimbangkan:

- **Harga**: Bandingkan penawaran dari beberapa supplier
- **Waktu tunggu**: Seberapa cepat mereka bisa mengirim?
- **Kualitas**: Pengalaman masa lalu dengan kualitas material
- **Keandalan**: Apakah mereka mengirim tepat waktu?
- **Pesanan minimum**: Apakah supplier memiliki persyaratan pesanan minimum?

### 6.3. Informasi Supplier

Navigasi ke `/admin/suppliers` untuk melihat direktori supplier lengkap. Sebagai Purchaser, Anda dapat melihat detail supplier tetapi tidak bisa mengubahnya -- hubungi Administrator untuk memperbarui informasi supplier.

---

## 7. Pelacakan Biaya

### 7.1. Biaya Pembelian

Untuk setiap permintaan pembelian, lacak:

- **Harga per unit**: Biaya per unit material
- **Total biaya**: Jumlah x harga per unit
- **Biaya pengiriman**: Jika berlaku
- **Syarat pembayaran**: Kapan pembayaran jatuh tempo

### 7.2. Kesadaran Anggaran

Pantau pengeluaran pembelian terhadap anggaran:

- Tinjau tren pengeluaran bulanan
- Bandingkan harga per unit antar supplier
- Identifikasi peluang pembelian massal
- Tandai kenaikan harga yang tidak biasa ke manajemen

> **Tips**: Jika supplier menaikkan harga secara signifikan, dokumentasikan kenaikan dan beritahu PM/CEO. Sistem melacak catatan keuangan, dan lonjakan biaya yang tidak bisa dijelaskan akan ditandai.

---

## 8. Konsolidasi Pembelian

### 8.1. Apa Itu Konsolidasi?

Halaman Pengaturan Admin mencakup fitur **Konsolidasi Pembelian** yang mengelompokkan permintaan pembelian kecil untuk supplier yang sama menjadi satu pesanan. Ini mengurangi biaya pengiriman dan menyederhanakan logistik.

### 8.2. Cara Kerjanya

1. Sistem menganalisis permintaan pembelian tertunda
2. Mengelompokkan permintaan berdasarkan supplier
3. Menyarankan pesanan yang dikonsolidasi
4. Anda meninjau dan menyetujui konsolidasi

### 8.3. Kapan Mengkonsolidasi

Konsolidasi ketika:

- Beberapa material berasal dari supplier yang sama
- Tidak ada item individual yang sangat dibutuhkan
- Biaya pengiriman signifikan relatif terhadap biaya material
- Supplier menawarkan diskon volume

JANGAN konsolidasi ketika:

- Material sangat dibutuhkan (memblokir produksi)
- Supplier memiliki persyaratan pesanan minimum yang sudah terpenuhi
- Material yang berbeda memiliki waktu tunggu yang sangat berbeda

---

## 9. Perintah Bot Telegram

| Perintah | Deskripsi |
|---|---|
| `/start` | Inisialisasi koneksi bot |
| `/stock` | Periksa level stok material |
| `/mystats` | Lihat statistik Anda |
| `/help` | Daftar semua perintah yang tersedia |

### 9.1. Notifikasi Otomatis

Sebagai Purchaser, Anda menerima notifikasi untuk:

- Permintaan pembelian baru yang dibuat
- Permintaan yang disetujui PM (siap untuk Anda tempatkan)
- Peringatan stok rendah untuk material kritis
- Pengingat pengiriman untuk kiriman yang terlambat
- Briefing pagi dengan ringkasan pengadaan

### 9.2. Peringatan Khusus Pabrik

Jika pabrik Anda memiliki chat Telegram purchaser yang dikonfigurasi, Anda menerima peringatan langsung di grup chat tersebut. Ini menjaga komunikasi pengadaan tetap terpusat.

---

## 10. Referensi Navigasi

| Halaman | URL | Tujuan |
|---|---|---|
| Dashboard Purchaser | `/purchaser` | Dashboard utama dengan permintaan, pengiriman, defisit, supplier |
| Direktori Supplier | `/admin/suppliers` | Daftar supplier lengkap (hanya lihat) |
| Pengaturan | `/settings` | Pengaturan akun pribadi |

---

## 11. Tips dan Praktik Terbaik

> **Tetap di depan defisit**: Jangan menunggu material mencapai nol sebelum memesan. Tinjau tab Defisit setiap hari dan tempatkan pesanan saat material mendekati ambang batas minimum.

> **Komunikasikan waktu tunggu**: Saat Anda tahu pengiriman akan terlambat, perbarui sistem segera. Ini memungkinkan PM menyesuaikan jadwal produksi sebelum posisi terblokir.

> **Bangun hubungan supplier**: Hubungan supplier yang baik berarti pengiriman lebih cepat, harga lebih baik, dan prioritas saat material langka. Kunjungi supplier kunci secara berkala.

> **Lacak tren harga**: Simpan catatan perubahan harga dari supplier. Jika harga naik, pertimbangkan memesan jumlah lebih besar dengan harga saat ini (jika penyimpanan memungkinkan dan material tidak kadaluarsa).

> **Konsolidasi dengan cerdas**: Gabungkan pesanan saat menghemat biaya, tetapi jangan pernah dengan mengorbankan produksi yang terblokir. Biaya pengiriman kecil selalu lebih murah daripada waktu kiln menganggur.

> **Dokumentasikan semuanya**: Simpan catatan semua komunikasi supplier, penawaran harga, dan janji pengiriman. Kolom catatan di sistem adalah jejak audit Anda.

> **Rutinitas pagi**: Mulai setiap hari dengan memeriksa: (1) Permintaan baru yang disetujui untuk ditempatkan, (2) Pengiriman terlambat untuk ditindaklanjuti, (3) Material defisit yang memerlukan perhatian.

> **Koordinasi dengan gudang**: Setelah menempatkan pesanan, beritahu tim gudang apa yang diharapkan dan kapan. Ini memastikan penerimaan yang lancar saat pengiriman tiba.

---

*Panduan ini mencakup fitur Moonjar PMS v1.0 untuk peran Purchaser. Untuk dukungan teknis, hubungi administrator sistem.*
