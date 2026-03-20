# Panduan Production Manager (PM) -- Moonjar PMS

> Versi: 1.0 | Tanggal: 2026-03-20
> Moonjar Production Management System

---

## Daftar Isi

1. [Memulai](#1-memulai)
2. [Ringkasan Dashboard](#2-ringkasan-dashboard)
3. [Pengelolaan Material](#3-pengelolaan-material)
4. [Pesanan dan Posisi](#4-pesanan-dan-posisi)
5. [Tugas](#5-tugas)
6. [Aturan Konsumsi](#6-aturan-konsumsi)
7. [Pengelolaan Jadwal](#7-pengelolaan-jadwal)
8. [Tips dan Praktik Terbaik](#8-tips-dan-praktik-terbaik)

---

## 1. Memulai

### 1.1. Masuk ke Sistem

1. Buka dashboard Moonjar PMS di browser Anda.
2. Masuk menggunakan salah satu metode berikut:
   - **Google OAuth** -- klik "Sign in with Google"
   - **Email dan password** -- masukkan kredensial Anda lalu klik "Login"
3. Setelah berhasil masuk, sistem mendeteksi peran Anda dan mengarahkan ke `/manager` -- dashboard PM.

### 1.2. Pemilihan Pabrik Otomatis

Saat Anda masuk, sistem memeriksa pabrik mana yang ditugaskan untuk Anda:

- **Satu pabrik ditugaskan**: Pabrik dipilih secara otomatis. Anda tidak akan melihat dropdown pabrik -- semua data sudah difilter untuk pabrik Anda.
- **Beberapa pabrik ditugaskan**: Dropdown **Factory Selector** muncul di pojok kanan atas setiap halaman. Pilih pabrik yang ingin Anda kelola.

> **Penting**: Banyak operasi (membuat pesanan, membentuk batch otomatis, menerima material) memerlukan pabrik tertentu dipilih. Jika Anda melihat pesan "Select a factory first," pilih pabrik dari dropdown.

### 1.3. Navigasi

Sebagai Production Manager, Anda memiliki akses ke halaman-halaman berikut:

| Halaman | URL | Fungsi |
|---|---|---|
| Dashboard PM | `/manager` | Panel kendali utama dengan tab untuk pesanan, tugas, material, defek, dan lainnya |
| Jadwal | `/manager/schedule` | Jadwal produksi per bagian (Glazing, Firing, Sorting, QC, Kilns) |
| Kiln | `/manager/kilns` | Pengelolaan kiln, pemeliharaan, aturan pemuatan |
| Material | `/manager/materials` | Inventaris material, penerimaan, audit, riwayat transaksi |
| Aturan Konsumsi | `/consumption-rules` | Tingkat konsumsi glaze/engobe per meter persegi |
| Detail Pesanan | `/orders/:id` | Tampilan detail pesanan tertentu beserta posisinya |

Bilah navigasi atas juga mencakup:

- **NotificationsBell** -- menampilkan notifikasi yang belum dibaca (pesanan baru, kerusakan kiln, peringatan stok rendah, permintaan dari sales)
- **Factory Selector** -- beralih antar pabrik (hanya terlihat jika Anda memiliki akses ke beberapa pabrik)

---

## 2. Ringkasan Dashboard

Dashboard PM (`/manager`) adalah pusat kendali Anda. Diorganisir sebagai antarmuka tab dengan bagian-bagian berikut.

### 2.1. Tab Orders (Pesanan)

Tab default. Menampilkan semua pesanan produksi untuk pabrik yang dipilih.

**Sub-tab**: Current / Archive

**Filter**:
- Cari berdasarkan nomor pesanan atau nama klien
- Filter berdasarkan status: New, In Production, Partially Ready, Ready for Shipment, Cancelled

**Tindakan yang tersedia**:
- **Create Order** -- membuat pesanan produksi baru secara manual
- **Upload PDF** -- mengunggah file PDF pesanan untuk parsing otomatis berbasis AI
- Klik baris pesanan mana pun untuk membuka halaman detailnya

**Kartu KPI** di bagian atas menampilkan:
- Total pesanan, pesanan dalam produksi, pesanan siap kirim

### 2.2. Tab Tasks (Tugas)

Daftar semua tugas yang ditugaskan kepada Anda atau tim Anda. Tugas diurutkan berdasarkan prioritas (tertinggi dulu), kemudian berdasarkan tanggal pembuatan.

**Filter**: berdasarkan status (pending, in_progress, done, cancelled), berdasarkan jenis tugas, berdasarkan peran yang ditugaskan.

Tugas yang memblokir ditandai secara visual -- tugas ini mencegah posisi bergerak maju dalam proses produksi.

### 2.3. Tab Materials

Ringkasan status material:

- **Low Stock** -- peringatan material dengan saldo di bawah ambang batas minimum
- **Purchase Requests** -- permintaan pembelian yang dikirim ke Purchaser
- **Consumption Adjustments** -- perbedaan antara penggunaan material yang dihitung dan aktual yang memerlukan persetujuan atau penolakan Anda

### 2.4. Tab Defects (Defek)

Pemantauan kualitas produksi:

- **DefectAlertBanner** -- muncul ketika tingkat defek melebihi ambang batas normal
- **AnomalyAlertBanner** -- muncul ketika konsumsi material menyimpang secara signifikan dari nilai yang diharapkan

### 2.5. Tab TPS (Toyota Production System)

Parameter sistem produksi untuk pemantauan efisiensi.

### 2.6. Tab TOC (Theory of Constraints)

Tampilan visual zona buffer menggunakan metodologi TOC/DBR:

| Zona | Kondisi | Tindakan |
|---|---|---|
| Hijau | delta >= -5% | Sesuai jadwal, lanjutkan pekerjaan normal |
| Kuning | -20% <= delta < -5% | Perhatikan, pertimbangkan menaikkan prioritas |
| Merah | delta < -20% atau deadline terlewat | Mendesak: naikkan prioritas, tambah sumber daya, selesaikan hambatan |

Komponen **BottleneckVisualization** menampilkan kiln mana yang menjadi hambatan saat ini.

### 2.7. Tab Stone (Batu)

Pengelolaan reservasi batu -- mereservasi blanko batu untuk posisi tertentu.

### 2.8. Tab Kilns

Ringkasan cepat semua kiln dan statusnya langsung dari dashboard.

### 2.9. Tab AI Chat

Asisten AI bawaan untuk pertanyaan cepat tentang produksi, pesanan, dan material.

### 2.10. Tab Dinamis

Tab tambahan muncul secara otomatis ketika ada data yang relevan:

- **Blocking** -- posisi yang diblokir karena kekurangan material, resep belum ada, stensil belum ada, pencocokan warna, atau penahanan QM
- **Cancellations** -- permintaan pembatalan dari Sales
- **Change Requests** -- permintaan perubahan pesanan dari Sales
- **Mismatch** -- posisi dengan ketidakcocokan warna yang memerlukan keputusan Anda

---

## 3. Pengelolaan Material

Ini adalah salah satu area terpenting untuk PM. Halaman Material (`/manager/materials`) memberikan kontrol inventaris penuh.

### 3.1. Tata Letak Halaman

Saat Anda membuka halaman Material, Anda melihat:

1. **Header** dengan judul halaman, badge jumlah stok rendah, dan tombol:
   - **Dashboard** -- kembali ke dashboard PM
   - **+ Add Material** -- membuat material baru
2. **Baris filter**:
   - Pemilih pabrik (jika Anda memiliki beberapa pabrik)
   - Kotak pencarian -- cari material berdasarkan nama
3. **Tab jenis** -- tab dinamis berdasarkan hierarki material (subgrup). Setiap tab menampilkan jumlah material dalam kategori tersebut. Klik tab untuk memfilter, atau pilih "All" untuk melihat semuanya.
4. **Tabel material** -- tabel data utama

### 3.2. Memahami Tabel Material

Tabel menampilkan kolom-kolom berikut:

| Kolom | Keterangan |
|---|---|
| **Code** | Kode material otomatis (contoh: M-0042) |
| **Type** | Subgrup material dengan ikon |
| **Balance** | Saldo stok saat ini (merah jika di bawah minimum) |
| **Min** | Ambang batas saldo minimum |
| **Unit** | Satuan pengukuran (kg, g, L, ml, pcs, m, m2) |
| **Status** | "OK" (hijau) atau jumlah defisit (merah) |
| **Actions** | Tombol Terima, Audit, Riwayat, Edit |

> **Catatan untuk PM**: Kolom Nama disembunyikan di tampilan Anda untuk antarmuka yang lebih bersih. Material diidentifikasi berdasarkan Kode. Anda tetap bisa melihat nama saat mengedit atau di dialog transaksi.

### 3.3. Membuat Material Baru

1. Klik **"+ Add Material"** (pojok kanan atas, atau tombol di tampilan kosong).
2. Isi formulir:
   - **Name** -- nama deskriptif (contoh: "Zinc Oxide ZnO")
   - **Subgroup** -- pilih dari hierarki (contoh: "Pigments / Iron Oxide"). Ini secara otomatis mengatur jenis material.
   - **Unit** -- kg, g, L, ml, pcs, m, atau m2
   - **Initial Balance** -- jumlah stok awal
   - **Min Balance** -- ambang batas untuk peringatan stok rendah
   - **Supplier** -- pilih dari daftar pemasok (opsional)
   - **Warehouse Section** -- lokasi penyimpanan material
3. Klik **"Create"**.

> **Catatan**: Jika tidak ada pabrik yang dipilih saat pembuatan, entri stok secara otomatis dibuat untuk SEMUA pabrik aktif dengan saldo dan saldo minimum yang ditentukan.

### 3.4. Mengedit Material

Sebagai PM, Anda dapat mengedit bidang-bidang berikut:

| Bidang | PM Bisa Edit? |
|---|---|
| Subgrup / Jenis | Ya |
| Bagian Gudang | Ya |
| Saldo Minimum | Ya |
| Pemasok | Ya |
| Nama | Tidak -- hubungi Admin |
| Saldo | Tidak -- gunakan Terima atau Audit Inventaris |
| Pabrik | Tidak -- hubungi Admin |
| Satuan | Tidak -- ditetapkan saat pembuatan |

**Cara mengedit**:
1. Temukan material di tabel.
2. Klik tombol **"Edit"** di kolom tindakan.
3. Dialog edit terbuka menampilkan saldo saat ini sebagai informasi saja. Di bawahnya: "To change balance, use Inventory Audit."
4. Ubah bidang yang diizinkan.
5. Klik **"Update"**.

### 3.5. Menerima Material

Saat material tiba di gudang, catat penerimaannya:

1. Temukan material di tabel.
2. Klik **tombol panah atas** di kolom tindakan. Ini membuka dialog Transaksi dalam mode "Receive" (Terima).
3. Dialog menampilkan saldo saat ini di bagian atas.
4. Masukkan **Quantity** (jumlah) yang diterima.
5. Opsional tambahkan **Notes** (catatan, contoh: referensi pengiriman, nomor batch).
6. Klik **"Receive"**.

Saldo langsung diperbarui setelah transaksi disimpan.

### 3.6. Audit Inventaris (Penghitungan Ulang Stok)

Fitur Audit Inventaris memungkinkan Anda mengoreksi saldo ketika jumlah fisik aktual berbeda dari yang ditampilkan sistem. Ini adalah cara yang benar untuk menyesuaikan saldo -- PM tidak bisa mengedit saldo secara langsung.

**Langkah demi langkah**:

1. Temukan material di tabel.
2. Klik **tombol tiga garis** (tombol audit) di kolom tindakan.
3. Dialog Transaksi terbuka dalam mode "Inventory Audit".
4. Anda melihat **saldo saat ini** ditampilkan di bagian atas.
5. Di bidang **"New actual balance"** (Saldo aktual baru), masukkan jumlah nyata yang Anda hitung.
6. Sistem secara otomatis menghitung dan menampilkan **selisih** (hijau untuk kelebihan, merah untuk kekurangan).
7. Isi bidang **Reason** (Alasan) -- ini **wajib diisi**. Jelaskan mengapa saldo berbeda (contoh: "Tumpah saat pemindahan," "Kesalahan pengukuran pada penghitungan sebelumnya," "Ditemukan stok tambahan di gudang sekunder").
8. Klik **"Confirm Audit"**.

**Apa yang terjadi di sistem**: Sistem membuat transaksi `inventory` dengan selisih yang dihitung (saldo baru dikurangi saldo saat ini). Catatan mencakup saldo sebelumnya, saldo baru, dan alasan Anda untuk audit.

> **Penting**: Selalu berikan alasan yang jelas dan jujur. Catatan audit inventaris merupakan bagian dari jejak audit dan ditinjau oleh manajemen.

### 3.7. Beralih Antara Terima dan Audit

Saat dialog Transaksi terbuka, Anda dapat beralih antar operasi:

- Klik **"Receive"** (tombol hijau) untuk mencatat material yang masuk
- Klik **"Inventory Audit"** (tombol kuning) untuk melakukan koreksi penghitungan stok

Bidang formulir berubah tergantung mode mana yang dipilih.

### 3.8. Riwayat Transaksi

Untuk melihat riwayat transaksi lengkap suatu material:

1. Klik tombol **"Hst"** di kolom tindakan.
2. Dialog terbuka menampilkan semua transaksi diurutkan berdasarkan tanggal (terbaru di atas).
3. Setiap transaksi menampilkan:
   - **Date** -- kapan transaksi terjadi
   - **Type** -- terima (hijau), konsumsi/hapus (merah), reservasi/batal reservasi (biru), audit (kuning)
   - **Qty** -- jumlah (+ untuk masuk, - untuk keluar)
   - **By** -- siapa yang melakukan transaksi
   - **Notes** -- komentar atau deskripsi otomatis

Jenis transaksi yang akan Anda lihat:

| Jenis | Keterangan | Warna |
|---|---|---|
| `receive` | Material diterima di gudang | Hijau |
| `consume` | Material dikonsumsi saat glazing | Merah |
| `manual_write_off` | Penghapusan manual | Merah |
| `reserve` | Direservasi untuk suatu posisi | Biru |
| `unreserve` | Reservasi dibatalkan | Biru |
| `audit` (inventory) | Koreksi audit inventaris | Kuning |

### 3.9. Peringatan Stok Rendah

Material dengan saldo di bawah ambang batas minimum ditandai:

- Latar belakang baris berubah merah di tabel.
- Kolom **Status** menampilkan "Deficit: X.X unit" dalam warna merah.
- Subjudul halaman menampilkan badge merah dengan jumlah material stok rendah.

Ketika Anda melihat peringatan stok rendah:
1. Periksa apakah material tersebut sudah memiliki permintaan pembelian aktif.
2. Jika belum, koordinasikan dengan Purchaser untuk memesan lebih banyak.
3. Jika kekurangan memblokir posisi, pertimbangkan apakah force-unblock diperlukan.

### 3.10. Mode Agregat (Semua Pabrik)

Jika Anda memiliki akses ke beberapa pabrik dan tidak memilih pabrik tertentu:

- Material ditampilkan dalam mode agregat dengan kolom **Factories** yang menunjukkan berapa banyak pabrik yang menyimpan material tersebut.
- Tombol **Terima** dan **Audit** dinonaktifkan -- Anda harus memilih pabrik tertentu untuk melakukan transaksi.
- Pesan "Select factory" muncul di kolom tindakan.

---

## 4. Pesanan dan Posisi

### 4.1. Melihat Pesanan

**Jalur**: Dashboard > Tab Orders

Pesanan ditampilkan sebagai tabel dengan:
- Nomor pesanan, nama klien, sumber (webhook / PDF / manual)
- Status (New, In Production, Partially Ready, Ready for Shipment, Shipped, Cancelled)
- Deadline
- Jumlah posisi

Klik baris pesanan mana pun untuk membuka halaman detailnya.

### 4.2. Membuat Pesanan

1. Klik **"Create Order"** di tab Orders.
2. Isi:
   - **Order Number** -- identifikasi unik
   - **Client** -- nama klien
   - **Factory** -- pilih Bali atau Java
   - **Deadline** -- tanggal pengiriman akhir
   - **Items** -- tambahkan item baris dengan: Color, Size, Application, Finishing, Quantity (pcs), Thickness (mm, default 11), Collection, Product Type (tile/sink/pebble), Shape (rectangle/round/triangle/octagon/freeform)
3. Klik **"Create"**.

Sistem secara otomatis membuat `OrderPosition` untuk setiap item dengan status `PLANNED`.

### 4.3. Mengunggah Pesanan dari PDF

1. Klik **"Upload PDF"**.
2. Pilih file PDF.
3. Parser AI mengekstrak data pesanan.
4. Tinjau dan konfirmasi data yang diparsing.

### 4.4. Status Pesanan

| Status | Arti |
|---|---|
| `new` | Semua posisi berstatus PLANNED |
| `in_production` | Setidaknya satu posisi sedang dalam proses |
| `partially_ready` | Sebagian posisi sudah selesai |
| `ready_for_shipment` | Semua posisi siap kirim |
| `shipped` | Semua posisi terkirim |
| `cancelled` | Semua posisi dibatalkan |

Status pesanan dihitung secara otomatis dari posisi-posisinya. PM dapat mengatur `status_override` untuk kontrol manual.

### 4.5. Siklus Hidup Posisi

Setiap item pesanan menjadi `OrderPosition` yang melewati tahapan-tahapan berikut:

```
PLANNED (Direncanakan)
  |
  +-- INSUFFICIENT_MATERIALS (diblokir: material tidak cukup)
  +-- AWAITING_RECIPE (diblokir: resep belum ditetapkan)
  +-- AWAITING_STENCIL_SILKSCREEN (diblokir: stensil belum ada)
  +-- AWAITING_COLOR_MATCHING (diblokir: pencocokan warna diperlukan)
  +-- AWAITING_SIZE_CONFIRMATION (diblokir: ukuran belum jelas)
  |
  v
SENT_TO_GLAZING -> ENGOBE_APPLIED -> ENGOBE_CHECK -> GLAZED
  |
  v
PRE_KILN_CHECK -> LOADED_IN_KILN -> FIRED
  |
  +-- REFIRE (perlu pembakaran ulang)
  +-- AWAITING_REGLAZE (perlu glazing ulang)
  |
  v
TRANSFERRED_TO_SORTING -> PACKED
  |
  v
SENT_TO_QUALITY_CHECK -> QUALITY_CHECK_DONE
  |
  +-- BLOCKED_BY_QM (ditahan oleh Quality Manager)
  |
  v
READY_FOR_SHIPMENT -> SHIPPED
```

### 4.6. Mengubah Status Posisi

1. Buka halaman detail pesanan atau halaman Jadwal.
2. Temukan posisinya.
3. Gunakan **Status Dropdown** untuk memilih status baru.
4. Sistem memvalidasi bahwa transisi diizinkan.
5. Ketika status berubah:
   - Status pesanan dihitung ulang secara otomatis.
   - Posisi dijadwalkan ulang.
   - Untuk status glazing, reservasi/konsumsi material terjadi.

### 4.7. Pemisahan Posisi (Split)

**Production Split**: Membagi posisi untuk memproses bagian-bagian secara terpisah (contoh: kiln berbeda).
- Membuat posisi anak dengan indeks split: `#1.1`, `#1.2`, dll.

**Sorting Split**: Membagi pada tahap sortir berdasarkan kategori kualitas (A-sort, B-sort, C-sort, showroom, repair, grinding, utilization).

**Merge**: Menggabungkan kembali posisi yang sebelumnya dipisah.

### 4.8. Force-Unblock (Buka Blokir Paksa)

Ketika posisi diblokir dan solusi standar tidak tersedia atau tidak praktis, Anda dapat melakukan force-unblock:

1. Temukan posisi yang diblokir (di tab **Blocking** atau di jadwal).
2. Klik **"Force Unblock"**.
3. **Masukkan alasan** di bidang Notes -- ini wajib untuk jejak audit.
4. Konfirmasi tindakan.

**Apa yang terjadi untuk setiap jenis blokir**:

| Blokir | Efek Force-Unblock |
|---|---|
| `insufficient_materials` | Reservasi paksa -- saldo bisa menjadi negatif |
| `awaiting_recipe` | Posisi pindah ke PLANNED (PM bertanggung jawab) |
| `awaiting_stencil_silkscreen` | Tugas pemblokir ditutup, posisi pindah ke PLANNED |
| `awaiting_color_matching` | Tugas pemblokir ditutup, posisi pindah ke PLANNED |
| `blocked_by_qm` | Tugas QM pemblokir ditutup, posisi pindah ke PLANNED |

> **Peringatan**: Force-unblock untuk `insufficient_materials` dapat menyebabkan saldo material negatif. Ini dilacak di tabel `negative_balances` dan akan muncul sebagai peringatan.

### 4.9. Permintaan Pembatalan dan Perubahan

Ketika Sales mengirim permintaan pembatalan atau perubahan, itu muncul di tab dinamis **Cancellations** atau **Change Requests**:

**Pembatalan**:
- **Accept** -- pesanan dibatalkan, semua posisi pindah ke CANCELLED, reservasi material dilepaskan.
- **Reject** -- pesanan terus diproduksi, Sales diberitahu.

**Permintaan Perubahan**:
- **Approve** -- perubahan diterapkan, posisi diperbarui, penjadwalan ulang dimulai.
- **Reject** -- tidak ada perubahan diterapkan, Sales diberitahu.

---

## 5. Tugas

### 5.1. Jenis Tugas

| Jenis | Keterangan | Penerima Tugas |
|---|---|---|
| `stencil_order` | Pesan stensil | PM / Purchaser |
| `silk_screen_order` | Pesan sablon | PM / Purchaser |
| `color_matching` | Pencocokan warna diperlukan | PM |
| `material_order` | Pesan material | Purchaser |
| `quality_check` | Inspeksi kualitas | Quality Manager |
| `kiln_maintenance` | Pemeliharaan kiln | PM |
| `showroom_transfer` | Transfer ke showroom | Gudang |
| `photographing` | Fotografi produk | Sorter/Packer |
| `packing_photo` | Fotografi kemasan | Sorter/Packer |
| `recipe_configuration` | Mengatur resep | PM / Admin |
| `stock_shortage` | Kekurangan stok batu | PM |
| `size_resolution` | Klarifikasi ukuran | PM |
| `glazing_board_needed` | Papan glazing khusus | PM |

### 5.2. Membuat Tugas

1. Buka Dashboard > Tab Tasks > klik **"Create Task"**.
2. Isi:
   - **Factory** -- pabrik mana
   - **Type** -- pilih dari daftar di atas
   - **Assignee** -- pengguna atau peran tertentu
   - **Related Order/Position** -- hubungkan ke pesanan atau posisi terkait (opsional)
   - **Blocking** -- centang jika tugas ini harus memblokir kemajuan posisi
   - **Description** -- apa yang perlu dilakukan
   - **Priority** -- 0 sampai 10 (10 = tertinggi)
3. Klik **"Create"**.

### 5.3. Menyelesaikan Tugas

**Penyelesaian standar**: Klik "Complete" pada tugas apa pun untuk menandainya sebagai selesai.

**Penyelesaian Kekurangan** (untuk tugas `stock_shortage`):
- **Manufacture** -- membuat posisi produksi baru untuk item yang kurang. Anda dapat menentukan jumlah dan pabrik tujuan.
- **Decline** -- menolak produksi, berikan alasan. Sales akan diberitahu.

**Penyelesaian Ukuran** (untuk tugas `size_resolution`):
- Pilih ukuran yang sudah ada dari database, atau
- Buat ukuran khusus baru (nama, lebar, tinggi, ketebalan, bentuk).
- Sistem secara otomatis menghitung kebutuhan papan glazing dan mungkin membuat tugas lanjutan `glazing_board_needed`.

### 5.4. Memantau Tugas

Filter tugas berdasarkan:
- **Status**: pending, in_progress, done, cancelled
- **Jenis**: jenis tugas apa pun
- **Peran yang ditugaskan**: production_manager, purchaser, warehouse, dll.
- **Pabrik**: filter berdasarkan pabrik

Tugas diurutkan berdasarkan prioritas (tertinggi dulu), kemudian berdasarkan tanggal pembuatan.

---

## 6. Aturan Konsumsi

### 6.1. Apa Itu Aturan Konsumsi?

Aturan Konsumsi (Consumption Rules) menentukan bagaimana glaze dan engobe diaplikasikan pada produk. **Metode aplikasi** adalah bidang kunci -- menentukan bidang tingkat mana dari resep yang digunakan untuk menghitung konsumsi material.

**Jalur**: `/consumption-rules`
**Akses**: Hanya PM dan Admin

### 6.2. Metode Aplikasi

Metode aplikasi adalah parameter terpenting. Ini memberi tahu sistem bagaimana engobe dan glaze diaplikasikan:

| Kode | Keterangan |
|---|---|
| `ss` | Semprot engobe + Semprot glaze -- menggunakan bidang semprot dari resep |
| `s` | Semprot glaze saja (tanpa engobe) -- menggunakan bidang semprot resep |
| `bs` | Kuas engobe + Semprot glaze |
| `sb` | Semprot engobe + Kuas glaze |
| `splashing` | Metode percikan -- menggunakan bidang percikan resep |
| `silk_screen` | Metode sablon -- menggunakan bidang sablon resep |
| `stencil` | Metode stensil -- menggunakan bidang semprot resep |
| `raku` | Metode raku -- menggunakan bidang semprot resep |
| `gold` | Aplikasi emas -- menggunakan bidang semprot resep |

### 6.3. Membuat Aturan

1. Klik **"+ Add Rule"**.
2. Isi formulir:
   - **Rule #** -- nomor urut (disarankan otomatis)
   - **Name** -- nama deskriptif (contoh: "SS standard tile 30x60")
   - **Description** -- kapan aturan ini berlaku
3. Atur **Kriteria Pencocokan** (sistem menggunakan ini untuk menemukan aturan yang tepat untuk setiap posisi):
   - Recipe Type (glaze / engobe)
   - Product Type (tile, sink, dll.)
   - Place of Application (permukaan saja, tepi, semua permukaan, dll.)
   - Size (pilih tunggal atau multi-pilih untuk membuat aturan untuk beberapa ukuran sekaligus)
   - Shape (persegi panjang, bulat, dll.)
   - Collection
   - Rentang ketebalan (min/maks mm)
   - Color Collection
4. Atur **Perhitungan Konsumsi**:
   - **Application Method** (wajib) -- ini adalah bidang kunci
   - **Coats** -- jumlah lapisan aplikasi (default: 1)
   - **Override recipe rates** (opsional, lanjutan) -- centang ini hanya jika tingkat resep tidak berlaku. Anda dapat mengatur tingkat ml/m2 khusus dan/atau penggantian berat jenis.
5. Atur **Priority** (angka lebih tinggi = diperiksa lebih dulu ketika beberapa aturan cocok).
6. Klik **"Create"**.

> **Mode multi-ukuran**: Saat membuat aturan baru, centang "Multi-size" untuk memilih beberapa ukuran. Sistem secara otomatis membuat aturan terpisah untuk setiap ukuran yang dipilih.

### 6.4. Mengedit Aturan

Klik **"Edit"** di sebelah aturan mana pun. Formulir yang sama terbuka dengan nilai saat ini. Ubah dan klik **"Update"**.

### 6.5. Menonaktifkan vs. Menghapus

- **Menonaktifkan**: Hapus centang kotak "Active". Aturan tetap di sistem tetapi tidak digunakan untuk pencocokan. Gunakan ini ketika Anda ingin menonaktifkan aturan sementara.
- **Menghapus**: Klik **"Delete"** dan konfirmasi. Ini permanen dan tidak dapat dibatalkan.

### 6.6. Kapan Mengganti Tingkat Resep

Secara default, tingkat berasal dari resep. Ganti hanya ketika:
- Produk memiliki sifat yang tidak biasa yang membuat tingkat standar tidak akurat.
- Anda telah mengukur konsumsi aktual dan secara konsisten berbeda dari nilai resep.
- Teknik aplikasi khusus memerlukan tingkat yang berbeda.

---

## 7. Pengelolaan Jadwal

### 7.1. Ringkasan Halaman Jadwal

**Jalur**: `/manager/schedule`

Jadwal dibagi menjadi lima tab bagian:

| Bagian | Posisi yang Ditampilkan |
|---|---|
| **Glazing** | Direncanakan, status blokir, tahap engobe, ter-glaze, pemeriksaan pra-kiln |
| **Firing** | Dimuat di kiln, terbakar, pembakaran ulang, menunggu glazing ulang |
| **Sorting** | Dipindahkan ke sortir, dikemas, siap kirim |
| **QC** | Dikirim ke pemeriksaan kualitas, pemeriksaan selesai, diblokir oleh QM |
| **Kilns** | Batch kiln (direncanakan / sedang berlangsung) |

Di bagian atas, **kartu KPI** menampilkan jumlah total untuk setiap bagian.

### 7.2. Kolom Tabel Posisi

Setiap bagian menampilkan posisi dalam tabel dengan kolom-kolom berikut:

| Kolom | Keterangan |
|---|---|
| Order | Nomor pesanan |
| # | Nomor posisi (contoh: #1, #1.1) |
| Color | Warna posisi |
| Size | Ukuran tile/produk |
| Thickness | Dalam mm |
| Shape | Persegi panjang, bulat, dll. |
| Glaze Place | Di mana glaze diaplikasikan (permukaan, tepi, semua sisi) |
| Edge | Informasi profil tepi |
| Application | Jenis aplikasi |
| Collection | Koleksi produk |
| Qty | Jumlah dalam potong |
| Status | Status saat ini (dropdown yang bisa diklik untuk mengubah) |
| Type | Jenis produk (tile, sink, dll.) |
| Priority | Nomor urut prioritas |

### 7.3. Mengubah Status dari Jadwal

Klik dropdown **Status** pada baris posisi mana pun untuk melihat transisi yang diizinkan. Pilih status baru. Sistem memvalidasi transisi dan memperbarui secara otomatis.

### 7.4. Pembentukan Batch Otomatis

Tersedia di tab **Firing** dan **Kilns**:

1. Pilih pabrik tertentu (wajib).
2. Klik **"Auto-Form Batches"**.
3. Konfirmasi tindakan.
4. Sistem:
   - Mengumpulkan posisi yang siap kiln (pre_kiln_check, glazed)
   - Mengelompokkan berdasarkan suhu pembakaran
   - Menempatkan ke kiln yang sesuai
   - Membuat batch

Pesan hasil menampilkan berapa banyak batch dan posisi yang ditugaskan.

### 7.5. Tab Kilns

Menampilkan setiap kiln sebagai kartu dengan:
- Nama kiln, badge status, jenis (big/small/raku)
- Kapasitas (m2) dan jumlah level
- Tabel batch terjadwal dengan: tanggal, status, jumlah posisi, jumlah potong, catatan

### 7.6. Menghapus Posisi (Mode Pembersihan)

Jika pabrik Anda memiliki mode pembersihan yang diaktifkan (dikonfigurasi oleh Admin), Anda akan melihat:
- Banner kuning: "Cleanup mode: delete buttons are visible on each position row."
- Ikon tempat sampah merah pada setiap baris posisi.

Untuk menghapus posisi:
1. Klik ikon tempat sampah.
2. Konfirmasi penghapusan.
3. Posisi dan semua tugas terkaitnya dihapus secara permanen.

> **Peringatan**: Penghapusan tidak dapat dibatalkan. Gunakan ini hanya untuk data uji coba atau entri yang salah.

---

## 8. Tips dan Praktik Terbaik

### 8.1. Rutinitas Harian

**Pagi (awal shift)**:
1. Periksa tab **Orders** -- ada pesanan baru?
2. Periksa tab **Blocking** -- berapa banyak posisi yang diblokir? Ada yang kritis?
3. Periksa tab **TOC** -- ada pesanan di zona merah?
4. Periksa tab **Materials** -- ada kekurangan stok yang kritis?
5. Periksa tab **Tasks** -- ada tugas yang terlambat?

**Selama hari kerja**:
6. Tinjau jadwal **Glazing** -- periksa antrean, sesuaikan prioritas jika perlu.
7. Bentuk batch di tab **Kilns** -- buat batch untuk pembakaran, mulai pembakaran.
8. Selesaikan blokir -- lakukan force-unblock atau atur solusi (pesan stensil, isi ulang stok material).
9. Pantau pembakaran -- periksa batch IN_PROGRESS, selesaikan yang sudah jadi.
10. Setujui **Consumption Adjustments** -- tinjau perbedaan antara penggunaan yang dihitung dan aktual.

**Sore (akhir shift)**:
11. Periksa penyelesaian harian -- berapa banyak posisi yang selesai hari ini?
12. Siapkan batch besok -- bentuk batch untuk hari berikutnya.
13. Tinjau permintaan Sales -- tangani Permintaan Pembatalan atau Perubahan yang tertunda.

**Mingguan**:
14. Periksa jadwal pemeliharaan kiln.
15. Tinjau dan perbarui aturan konsumsi jika diperlukan.
16. Pertimbangkan penjadwalan ulang pabrik penuh jika ada perubahan signifikan.

### 8.2. Praktik Terbaik Pemilih Pabrik

- Selalu pilih **pabrik tertentu** sebelum melakukan operasi yang mengubah data (membuat pesanan, membentuk batch, menerima material).
- Gunakan mode "All Factories" hanya untuk tinjauan umum dan pemantauan.
- Jika Anda hanya ditugaskan ke satu pabrik, pemilih disembunyikan dan pabrik Anda selalu aktif.

### 8.3. Menangani Kekurangan Material

1. Pertama, periksa riwayat transaksi untuk memahami tren konsumsi.
2. Verifikasi pengaturan min_balance masih akurat -- sesuaikan melalui Edit jika perlu.
3. Koordinasikan dengan Purchaser untuk memesan material yang kritis.
4. Gunakan force-unblock untuk kekurangan material hanya sebagai pilihan terakhir -- ini membuat saldo negatif.

### 8.4. Praktik Terbaik Audit Inventaris

- Lakukan audit berkala (mingguan atau bulanan) untuk material dengan perputaran tinggi.
- Selalu masukkan alasan yang jelas dan spesifik -- "penghitungan ulang" tidak membantu; "Penghitungan ulang setelah tumpahan pada 15 Maret" lebih baik.
- Bandingkan selisih audit dengan riwayat transaksi terbaru untuk mengidentifikasi pola.
- Jika Anda secara konsisten melihat perbedaan, tinjau aturan konsumsi -- tingkatnya mungkin perlu disesuaikan.

### 8.5. Notifikasi

PM menerima notifikasi untuk:
- Pesanan baru yang masuk dari Sales webhook
- Kerusakan kiln
- Kekurangan material kritis
- Permintaan pembatalan dan perubahan dari Sales

**Bot Telegram** mengirim ringkasan harian pukul 21:00 (bahasa Indonesia) dengan:
- Daftar tugas lengkap untuk hari berikutnya
- KPI untuk hari ini

### 8.6. Tips Antarmuka

- Gunakan **kotak pencarian** di halaman Material untuk mencari material berdasarkan nama atau kode dengan cepat.
- Di halaman Jadwal, **Status Dropdown** hanya menampilkan transisi yang valid -- Anda tidak bisa salah memilih status yang tidak diizinkan.
- Dialog **Transaction History** bisa di-scroll -- transaksi lebih lama ada di bawah.
- Saat membuat aturan konsumsi dengan beberapa ukuran, gunakan **mode Multi-size** untuk menghemat waktu.

---

> **Ada pertanyaan?** Hubungi administrator sistem atau gunakan **AI Chat** bawaan di dashboard PM.
