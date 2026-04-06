# Panduan Administrator -- Moonjar PMS

> Versi: 1.0 | Tanggal: 2026-04-06
> Moonjar Production Management System

---

## Daftar Isi

1. [Memulai](#1-memulai)
2. [Ikhtisar Panel Admin](#2-ikhtisar-panel-admin)
3. [Manajemen Pengguna](#3-manajemen-pengguna)
4. [Manajemen Pabrik](#4-manajemen-pabrik)
5. [Konfigurasi Bot Telegram](#5-konfigurasi-bot-telegram)
6. [Keamanan: Log Audit & Sesi](#6-keamanan-log-audit--sesi)
7. [Manajemen Koleksi](#7-manajemen-koleksi)
8. [Warna & Koleksi Warna](#8-warna--koleksi-warna)
9. [Manajemen Ukuran](#9-manajemen-ukuran)
10. [Material & Grup Material](#10-material--grup-material)
11. [Manajemen Resep](#11-manajemen-resep)
12. [Profil Pembakaran](#12-profil-pembakaran)
13. [Grup Suhu](#13-grup-suhu)
14. [Aturan Konsumsi](#14-aturan-konsumsi)
15. [Bagian Gudang](#15-bagian-gudang)
16. [Jenis Kardus Pengemasan](#16-jenis-kardus-pengemasan)
17. [Supplier](#17-supplier)
18. [Jenis Aplikasi & Tempat](#18-jenis-aplikasi--tempat)
19. [Jenis Finishing](#19-jenis-finishing)
20. [Manajemen Tahapan](#20-manajemen-tahapan)
21. [Pengaturan Admin](#21-pengaturan-admin)
22. [Kontrol Akses Dashboard](#22-kontrol-akses-dashboard)
23. [Kalender Pabrik](#23-kalender-pabrik)
24. [Izin Pembersihan PM](#24-izin-pembersihan-pm)
25. [Stub Integrasi](#25-stub-integrasi)
26. [Referensi Navigasi](#26-referensi-navigasi)
27. [Tips dan Praktik Terbaik](#27-tips-dan-praktik-terbaik)

---

## 1. Memulai

### 1.1. Masuk ke Sistem

1. Buka dashboard Moonjar PMS di browser Anda.
2. Masuk menggunakan salah satu metode:
   - **Google OAuth** -- klik "Sign in with Google"
   - **Email dan kata sandi** -- masukkan kredensial Anda dan klik "Login"
3. Setelah autentikasi, sistem mendeteksi peran Anda dan mengarahkan ke `/admin` -- Panel Admin.

### 1.2. Kemampuan Peran

Sebagai Administrator, Anda mengelola semua konfigurasi sistem dan data referensi:

- Akun pengguna dan penugasan peran
- Konfigurasi pabrik (nama, lokasi, zona waktu, grup Telegram)
- Semua data referensi produk (koleksi, warna, ukuran, material, resep)
- Profil pembakaran dan grup suhu
- Bagian gudang dan aturan pengemasan
- Pengaturan sistem (aturan eskalasi, ambang batas cacat, lead time)
- Pemantauan keamanan (log audit, sesi aktif)
- Kontrol akses dashboard
- Konfigurasi bot Telegram

---

## 2. Ikhtisar Panel Admin

Panel Admin (`/admin`) adalah pusat utama untuk semua konfigurasi.

### 2.1. Tata Letak

1. **Kartu KPI** -- Jumlah Pengguna, Jumlah Pabrik, Pabrik Aktif
2. **Status Bot Telegram** -- status koneksi dan konfigurasi chat owner
3. **Bagian Pabrik** -- daftar pabrik dengan operasi CRUD
4. **Bagian Keamanan** -- tab Log Audit dan Sesi Aktif
5. **Stub Integrasi** -- toggle untuk integrasi pengembangan/pengujian
6. **Tautan Cepat** -- pintasan ke halaman Pengguna dan Tablo
7. **Data Referensi** -- tombol ke semua halaman manajemen data referensi
8. **Izin Pembersihan PM** -- izin penghapusan data sementara

---

## 3. Manajemen Pengguna

### 3.1. Mengakses Pengguna

Navigasi ke `/users` melalui bagian Tautan Cepat.

### 3.2. Peran Pengguna

Sistem mendukung 8 peran:

| Peran | Kode | Deskripsi |
|---|---|---|
| **Owner** | `owner` | Akses penuh ke semuanya, pengawasan strategis |
| **Administrator** | `administrator` | Konfigurasi sistem dan data referensi |
| **CEO** | `ceo` | Pengawasan operasional lintas pabrik |
| **Production Manager** | `production_manager` | Manajemen produksi harian |
| **Quality Manager** | `quality_manager` | Kontrol kualitas dan inspeksi |
| **Warehouse** | `warehouse` | Manajemen inventaris material |
| **Sorter Packer** | `sorter_packer` | Operasi sortir dan packing |
| **Purchaser** | `purchaser` | Pengadaan dan manajemen supplier |

### 3.3. Membuat Pengguna

1. Navigasi ke `/users`.
2. Klik **+ Tambah Pengguna**.
3. Isi:
   - **Email** -- alamat email unik
   - **Nama Lengkap** -- nama tampilan
   - **Peran** -- pilih dari 8 peran
   - **Kata Sandi** -- kata sandi awal (pengguna bisa ganti nanti)
   - **Penugasan Pabrik** -- pabrik mana yang bisa diakses pengguna
   - **Bahasa** -- bahasa yang diinginkan (en/id/ru) untuk bot Telegram
   - **ID Chat Telegram** -- untuk notifikasi bot (opsional, bisa diatur nanti)
4. Klik **Buat**.

### 3.4. Mengedit Pengguna

- Ubah peran, penugasan pabrik, bahasa, atau pengaturan Telegram
- Reset kata sandi
- Aktifkan atau nonaktifkan akun

> **Penting**: Menonaktifkan pengguna segera mencabut akses mereka. Sesi aktif dihentikan.

### 3.5. Aturan Penugasan Pabrik

- **Pengguna satu pabrik**: Hanya melihat data dari pabrik yang ditugaskan
- **Pengguna multi-pabrik**: Bisa beralih antar pabrik yang ditugaskan
- **Peran semua pabrik** (Owner, CEO, Administrator): Otomatis memiliki akses ke semua pabrik

---

## 4. Manajemen Pabrik

### 4.1. Daftar Pabrik

Bagian Pabrik di Panel Admin menampilkan semua pabrik yang dikonfigurasi.

| Kolom | Deskripsi |
|---|---|
| Nama | Nama tampilan pabrik |
| Lokasi | Lokasi fisik |
| Zona Waktu | Zona waktu untuk penjadwalan |
| Telegram | Grup chat yang dikonfigurasi (Masters, Purchaser) |
| Status | Aktif atau Tidak Aktif |
| Aksi | Edit, Hapus |

### 4.2. Membuat Pabrik

1. Klik **+ Tambah Pabrik**.
2. Isi Dialog Pabrik:
   - **Nama** -- nama pabrik (misal, "Moonjar Bali", "Moonjar Java")
   - **Lokasi** -- alamat fisik atau area
   - **Zona Waktu** -- zona waktu (misal, "Asia/Makassar" untuk Bali WITA)
   - **ID Chat Grup Masters** -- grup Telegram untuk master produksi
   - **ID Chat Purchaser** -- chat Telegram untuk peringatan purchaser
   - **Aktif** -- apakah pabrik beroperasi
3. Klik **Simpan**.

### 4.3. Mengedit Pabrik

Klik **Edit** pada baris pabrik mana pun untuk mengubah pengaturannya. Perubahan umum:

- Memperbarui ID chat Telegram saat grup berubah
- Mengubah zona waktu
- Menonaktifkan pabrik sementara

### 4.4. Menghapus Pabrik

> **Peringatan**: Menghapus pabrik bersifat permanen dan menghapus semua data terkait. Hanya hapus pabrik uji coba. Untuk menonaktifkan pabrik, nonaktifkan saja.

---

## 5. Konfigurasi Bot Telegram

### 5.1. Status Bot

Kartu Bot Telegram menampilkan:

- **Terhubung** (titik hijau): Bot aktif, menampilkan username
- **Tidak terhubung** (titik merah): Bot tidak dikonfigurasi atau token tidak valid

### 5.2. ID Chat Owner

Konfigurasi ID chat Telegram owner untuk menerima notifikasi kritis:

1. Masukkan ID chat di kolom input.
2. Klik **Test** untuk memverifikasi koneksi.
3. Jika berhasil, klik **Simpan**.

### 5.3. Menemukan ID Chat

Klik **Temukan ID Chat** untuk melihat chat terbaru yang telah menerima pesan dari bot:

1. Kirim pesan di grup Telegram target (di mana bot adalah anggota).
2. Klik **Temukan ID Chat**.
3. Salin ID chat yang relevan.
4. Tempel ke pengaturan Telegram pabrik.

---

## 6. Keamanan: Log Audit & Sesi

### 6.1. Log Audit

Penampil Log Audit menampilkan semua perubahan sistem yang ditangkap otomatis:

- Kejadian **INSERT** -- catatan baru dibuat
- Kejadian **UPDATE** -- catatan dimodifikasi
- Kejadian **DELETE** -- catatan dihapus

Untuk setiap kejadian:
- Timestamp
- Pengguna yang melakukan tindakan
- Tabel yang terpengaruh
- ID catatan
- Perubahan (nilai lama -> nilai baru)

### 6.2. Sesi Aktif

Penampil Sesi Aktif menampilkan pengguna yang saat ini login:

- Nama dan email pengguna
- Peran
- Waktu aktivitas terakhir
- Alamat IP
- Informasi perangkat/browser

Anda dapat menghentikan sesi yang mencurigakan dari tampilan ini.

---

## 7. Manajemen Koleksi

Navigasi ke `/admin/collections`.

### 7.1. Apa Itu Koleksi?

Koleksi mendefinisikan lini produk Moonjar:

- **Authentic** -- finishing batu alam
- **Creative** -- desain artistik
- **Stencil** -- pola berbasis stensil
- **Silkscreen** -- pencetakan sablon
- **Raku** -- teknik pembakaran tradisional Jepang
- **Gold** -- aplikasi daun emas
- **Exclusive** -- karya satu-satunya
- **Stock** -- item inventaris standar

### 7.2. Mengelola Koleksi

- **Buat**: Tambah koleksi baru dengan nama dan deskripsi
- **Edit**: Ubah nama atau deskripsi koleksi
- **Hapus**: Hapus koleksi (hanya jika tidak ada produk yang menggunakannya)

---

## 8. Warna & Koleksi Warna

### 8.1. Warna

Navigasi ke `/admin/colors`.

Kelola katalog warna:

- **Nama** -- nama warna (misal, "Ocean Blue", "Desert Sand")
- **Kode** -- kode referensi warna
- **Nilai Hex** -- kode warna hex untuk tampilan

### 8.2. Koleksi Warna

Navigasi ke `/admin/color-collections`.

Koleksi Warna mengelompokkan warna berdasarkan tema atau koleksi, memudahkan tim sales dan produksi menemukan warna yang tepat.

---

## 9. Manajemen Ukuran

Navigasi ke `/admin/sizes`.

### 9.1. Definisi Ukuran

Ukuran mendefinisikan dimensi produk dengan parameter khusus bentuk:

| Bentuk | Parameter |
|---|---|
| **Persegi Panjang** | Panjang (cm), Lebar (cm) |
| **Bulat** | Diameter (cm) |
| **Segitiga** | Sisi A, Sisi B, Sisi C (cm) |
| **Segi Delapan** | Lebar (cm) |
| **Bentuk Bebas** | Dimensi perkiraan |

---

## 10. Material & Grup Material

### 10.1. Grup Material

Navigasi ke `/admin/materials` untuk katalog material lengkap.

Material diorganisir dalam hierarki:

- **Jenis** (tingkat atas): Bahan Baku, Komponen Glasir, Engobe, Alat, dll.
- **Subkelompok** (tingkat kedua): Pigmen / Iron Oxide, Frit / Bebas Timbal, dll.

### 10.2. Kolom Material

| Kolom | Deskripsi |
|---|---|
| Nama | Nama deskriptif |
| Kode | Dibuat otomatis (M-0001, M-0002, ...) |
| Subkelompok | Kategori dalam hierarki |
| Satuan | kg, g, L, ml, pcs, m, m² |
| Supplier | Supplier default |
| Bagian Gudang | Lokasi penyimpanan |

### 10.3. Material vs. Stok

Perbedaan penting:

- **Material** (entri katalog): Definisi -- nama, jenis, satuan
- **MaterialStock** (per pabrik): Inventaris -- saldo, saldo minimum, ID pabrik

Satu material dapat memiliki entri stok di beberapa pabrik.

---

## 11. Manajemen Resep

Navigasi ke `/admin/recipes`.

### 11.1. Jenis Resep

| Jenis | Deskripsi |
|---|---|
| **Glasir** | Formulasi glasir untuk permukaan ubin |
| **Engobe** | Formulasi engobe (lapisan dasar di bawah glasir) |
| **Biskit** | Resep bodi/biskit (jika relevan) |

### 11.2. Struktur Resep

Sebuah resep terdiri dari:

- **Nama** -- pengidentifikasi resep
- **Jenis** -- glasir, engobe, atau biskit
- **Suhu** -- suhu pembakaran target
- **Bahan** -- daftar material dengan persentase (harus total 100%)
- **Catatan** -- instruksi persiapan

---

## 12. Profil Pembakaran

Navigasi ke `/admin/firing-profiles`.

### 12.1. Apa Itu Profil Pembakaran?

Profil pembakaran mendefinisikan kurva pemanasan dan pendinginan untuk pembakaran kiln:

- **Nama** -- pengidentifikasi profil (misal, "Standar 1050C", "Raku Cepat")
- **Suhu Target** -- suhu puncak dalam derajat Celsius
- **Total Durasi** -- total waktu pembakaran
- **Interval** -- daftar segmen suhu-waktu

### 12.2. Interval Profil

Setiap interval mendefinisikan:

| Kolom | Deskripsi |
|---|---|
| Suhu Awal | Suhu awal (C) |
| Suhu Akhir | Suhu target (C) |
| Durasi | Berapa lama segmen ini berlangsung (jam) |
| Laju Kenaikan | Derajat per jam |
| Tahan | Apakah menahan pada suhu akhir |
| Durasi Tahan | Berapa lama menahan (jam) |

---

## 13. Grup Suhu

Navigasi ke `/admin/temperature-groups`.

### 13.1. Tujuan

Grup suhu memungkinkan pembakaran bersama dari resep berbeda yang memiliki parameter pembakaran yang kompatibel. Ini memaksimalkan pemanfaatan kiln.

### 13.2. Mengelola Grup

- **Buat**: Definisikan grup dengan nama dan rentang suhu
- **Tugaskan Resep**: Tautkan resep ke grup
- **Lihat Resep**: Lihat resep mana yang termasuk setiap grup

---

## 14. Aturan Konsumsi

Navigasi ke `/admin/consumption-rules`.

### 14.1. Apa Itu Aturan Konsumsi?

Aturan konsumsi mendefinisikan berapa banyak material yang digunakan per meter persegi produksi:

| Kolom | Deskripsi |
|---|---|
| Material | Material mana |
| Metode Aplikasi | Cara diaplikasikan (semprot, celup, kuas) |
| Tingkat | Gram per meter persegi |
| Jenis Produk | Jenis produk mana aturan ini berlaku |

---

## 15. Bagian Gudang

Navigasi ke `/admin/warehouses`.

### 15.1. Tujuan

Bagian gudang mendefinisikan lokasi penyimpanan fisik dalam pabrik:

- Penyimpanan bahan baku
- Penyimpanan glasir
- Area barang jadi
- Penyimpanan alat

### 15.2. Mengelola Bagian

- **Buat**: Tambah bagian baru dengan nama, penugasan pabrik, dan deskripsi
- **Edit**: Perbarui nama atau deskripsi bagian
- **Hapus**: Hapus bagian (hanya jika tidak ada material yang tersimpan di sana)

---

## 16. Jenis Kardus Pengemasan

Navigasi ke `/admin/packaging`.

### 16.1. Definisi Jenis Kardus

| Kolom | Deskripsi |
|---|---|
| Nama | Nama jenis kardus |
| Dimensi Dalam | Panjang x Lebar x Tinggi (cm) |
| Kapasitas | Berapa ubin muat (bervariasi berdasarkan ukuran ubin) |
| Spacer Diperlukan | Apakah ubin memerlukan spacer |
| Batas Berat | Berat maksimum dalam kg |

---

## 17. Supplier

Navigasi ke `/admin/suppliers`.

### 17.1. Kolom Supplier

| Kolom | Deskripsi |
|---|---|
| Nama | Nama perusahaan |
| Orang Kontak | Kontak utama |
| Telepon | Telepon kontak |
| Email | Email kontak |
| Alamat | Alamat fisik |
| Material | Material mana yang mereka sediakan |
| Catatan | Informasi tambahan |

---

## 18. Jenis Aplikasi & Tempat

### 18.1. Jenis Aplikasi

Navigasi ke `/admin/application-types`.

Jenis aplikasi mendefinisikan cara glasir diaplikasikan:

- Semprot
- Celup
- Kuas
- Tuang
- Sablon
- Stensil

### 18.2. Tempat Aplikasi

Navigasi ke `/admin/places-of-application`.

Mendefinisikan di mana produk dipasang:

- Dinding
- Lantai
- Countertop
- Fasad
- Kolam
- Kamar mandi

---

## 19. Jenis Finishing

Navigasi ke `/admin/finishing-types`.

Mendefinisikan perlakuan permukaan akhir:

- Glossy
- Matte
- Satin
- Bertekstur
- Poles
- Mentah

---

## 20. Manajemen Tahapan

Navigasi ke `/admin/stages`.

### 20.1. Tahapan Produksi

Sistem melacak posisi melalui tahapan produksi:

| Tahap | Deskripsi |
|---|---|
| Direncanakan | Pesanan diterima, belum dimulai |
| Engobe | Aplikasi engobe |
| Glazing | Aplikasi glasir |
| Pengeringan | Pengeringan sebelum pembakaran |
| QC Pra-Kiln | Pemeriksaan kualitas sebelum pembakaran |
| Pembakaran | Di dalam kiln |
| Pendinginan | Pendinginan setelah pembakaran |
| QC Akhir | Pemeriksaan kualitas setelah pembakaran |
| Sortir | Penyortiran grade |
| Packing | Pengemasan dan pelabelan |
| Siap | Siap untuk pengiriman |

---

## 21. Pengaturan Admin

Navigasi ke `/admin/settings`.

### 21.1. Tab

| Tab | Tujuan |
|---|---|
| **Aturan Eskalasi** | Definisikan kapan dan bagaimana masalah dieskalasi |
| **Penerimaan** | Konfigurasi penerimaan material |
| **Ambang Batas Cacat** | Kapan memicu peringatan kualitas |
| **Konsolidasi Pembelian** | Aturan pengelompokan untuk pesanan pembelian |
| **Lead Time Layanan** | Durasi yang diharapkan untuk setiap jenis layanan |

### 21.2. Aturan Eskalasi

Konfigurasi kapan sistem harus mengeskalasi masalah:

- Ambang batas keterlambatan (jam sebelum eskalasi)
- Target notifikasi (siapa yang diberitahu)
- Tingkat eskalasi (PM -> CEO -> Owner)

### 21.3. Ambang Batas Cacat

Atur ambang batas untuk peringatan cacat otomatis:

- Tingkat posisi: peringatan saat tingkat cacat melebihi X% untuk satu posisi
- Tingkat pabrik: peringatan saat tingkat cacat keseluruhan melebihi Y%

---

## 22. Kontrol Akses Dashboard

Navigasi ke `/admin/dashboard-access`.

### 22.1. Tujuan

Kontrol Akses Dashboard memungkinkan Anda menyesuaikan bagian dashboard mana yang terlihat oleh setiap peran.

### 22.2. Konfigurasi

Untuk setiap peran, toggle visibilitas:

- Tab dashboard tertentu
- Kartu KPI
- Bagian laporan
- Tombol ekspor

---

## 23. Kalender Pabrik

Navigasi ke `/admin/factory-calendar`.

### 23.1. Tujuan

Kalender Pabrik mendefinisikan hari kerja dan hari libur per pabrik. Mesin penjadwalan menggunakan ini untuk menghitung tenggat waktu yang realistis.

### 23.2. Mengelola Kalender

- **Lihat**: Kalender setahun penuh dengan hari libur yang ditandai
- **Toggle**: Klik hari mana pun untuk beralih antara hari kerja dan non-kerja
- **Hari Libur**: Tambahkan hari libur bernama (hari libur nasional Indonesia, hari libur perusahaan)
- **Per Pabrik**: Setiap pabrik memiliki kalendernya sendiri

---

## 24. Izin Pembersihan PM

Panel Admin mencakup Izin Pembersihan PM per pabrik:

| Izin | Default | Deskripsi |
|---|---|---|
| PM dapat menghapus tugas | Mati | Izinkan PM menghapus tugas |
| PM dapat menghapus posisi | Mati | Izinkan PM menghapus posisi pesanan |

> **Praktik Terbaik**: Biarkan mati selama operasi normal. Aktifkan sementara hanya untuk pembersihan atau koreksi data.

---

## 25. Stub Integrasi

**Toggle Stub** memungkinkan mengaktifkan atau menonaktifkan stub integrasi untuk pengembangan dan pengujian:

- Saat diaktifkan, endpoint API tertentu mengembalikan data tiruan alih-alih data nyata
- Berguna selama pengembangan saat layanan eksternal tidak tersedia
- Harus selalu **dinonaktifkan** di production

---

## 26. Referensi Navigasi

| Halaman | URL | Tujuan |
|---|---|---|
| Panel Admin | `/admin` | Pusat konfigurasi utama |
| Pengguna | `/users` | Manajemen pengguna |
| Koleksi | `/admin/collections` | Koleksi produk |
| Koleksi Warna | `/admin/color-collections` | Pengelompokan warna |
| Warna | `/admin/colors` | Katalog warna |
| Jenis Aplikasi | `/admin/application-types` | Metode aplikasi |
| Tempat Aplikasi | `/admin/places-of-application` | Lokasi pemasangan |
| Jenis Finishing | `/admin/finishing-types` | Perlakuan permukaan |
| Grup Suhu | `/admin/temperature-groups` | Grup pembakaran bersama |
| Material | `/admin/materials` | Katalog material |
| Gudang | `/admin/warehouses` | Bagian gudang |
| Pengemasan | `/admin/packaging` | Definisi jenis kardus |
| Ukuran | `/admin/sizes` | Definisi ukuran produk |
| Aturan Konsumsi | `/admin/consumption-rules` | Tingkat penggunaan material |
| Profil Pembakaran | `/admin/firing-profiles` | Kurva pembakaran kiln |
| Resep | `/admin/recipes` | Resep glasir/engobe |
| Supplier | `/admin/suppliers` | Direktori supplier |
| Tahapan | `/admin/stages` | Definisi tahap produksi |
| Pengaturan Admin | `/admin/settings` | Eskalasi, ambang batas, lead time |
| Akses Dashboard | `/admin/dashboard-access` | Visibilitas dashboard per peran |
| Kalender Pabrik | `/admin/factory-calendar` | Hari kerja dan hari libur |
| Tablo | `/tablo` | Papan tampilan produksi |
| Pengaturan | `/settings` | Pengaturan akun pribadi |

---

## 27. Tips dan Praktik Terbaik

> **Data referensi dulu**: Sebelum sistem bisa memproses pesanan, Anda perlu mengatur: pabrik, koleksi, warna, ukuran, material, resep, profil pembakaran, aturan konsumsi, dan bagian gudang. Atur dalam urutan ini.

> **Uji dengan pabrik dummy**: Saat bereksperimen dengan pengaturan, buat pabrik uji coba. Ini menjaga data produksi tetap bersih.

> **Log audit adalah sahabat Anda**: Jika terjadi kesalahan, log audit adalah tempat pertama untuk diperiksa. Ini mencatat setiap perubahan, siapa yang membuatnya, dan kapan.

> **Jaga resep tetap terbaru**: Saat tim produksi menyesuaikan resep, perbarui di sistem segera. Resep yang ketinggalan zaman menyebabkan perhitungan konsumsi material yang salah.

> **Pemeliharaan kalender**: Di awal setiap tahun, atur semua hari libur yang diketahui di Kalender Pabrik. Ini mencegah kejutan penjadwalan.

> **Pemantauan sesi**: Periksa Sesi Aktif secara berkala. Jika Anda melihat sesi dari perangkat atau lokasi yang tidak dikenal, selidiki segera.

> **Kualitas data supplier**: Jaga kontak supplier tetap terkini. Nomor telepon dan email yang ketinggalan zaman menyebabkan keterlambatan pengadaan.

> **Minimalkan izin pembersihan**: Izin pembersihan PM harus bersifat sementara. Setelah pembersihan data selesai, nonaktifkan segera.

---

*Panduan ini mencakup fitur Moonjar PMS v1.0 untuk peran Administrator. Untuk dukungan teknis, hubungi pengembang sistem.*
