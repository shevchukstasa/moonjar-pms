# Panduan Production Manager (PM) -- Moonjar PMS

> Versi: 1.1 | Tanggal: 2026-03-21
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
8. [Inspeksi Kiln](#8-inspeksi-kiln)
9. [Tugas Pengukuran Konsumsi](#9-tugas-pengukuran-konsumsi)
11. [Pemeliharaan Kiln](#11-pemeliharaan-kiln)
12. [Keputusan Grinding](#12-keputusan-grinding)
13. [Barang Jadi](#13-barang-jadi)
14. [Rekonsiliasi](#14-rekonsiliasi)
15. [Laporan dan Analitik](#15-laporan-dan-analitik)
16. [Kalender Pabrik](#16-kalender-pabrik)
17. [Pengelolaan Resep](#17-pengelolaan-resep)
18. [Profil Pembakaran](#18-profil-pembakaran)
19. [Grup Suhu](#19-grup-suhu)
20. [Pengelolaan Tahapan](#20-pengelolaan-tahapan)
21. [Jadwal Pembakaran](#21-jadwal-pembakaran)
22. [Pengelolaan Gudang](#22-pengelolaan-gudang)
23. [Pengelolaan Kemasan](#23-pengelolaan-kemasan)
24. [Pengelolaan Ukuran](#24-pengelolaan-ukuran)
25. [Tablo (Papan Tampilan Produksi)](#25-tablo-papan-tampilan-produksi)
26. [Tips dan Praktik Terbaik](#26-tips-dan-praktik-terbaik)

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
| Inspeksi Kiln | `/manager/kiln-inspections` | Penilaian kondisi kiln mingguan berbasis checklist |
| Pemeliharaan Kiln | `/manager/kiln-maintenance` | Pemeliharaan preventif dan korektif terjadwal |
| Grinding | `/manager/grinding` | Keputusan grinding untuk produk yang cacat |
| Material | `/manager/materials` | Inventaris material, penerimaan, audit, riwayat transaksi |
| Resep | `/admin/recipes` | Pengelolaan resep glaze, engobe, dan produk |
| Profil Pembakaran | `/admin/firing-profiles` | Kurva pemanasan/pendinginan multi-interval untuk kiln |
| Grup Suhu | `/admin/temperature-groups` | Definisi grup suhu untuk co-firing |
| Gudang | `/admin/warehouses` | Pengelolaan bagian gudang |
| Kemasan | `/admin/packaging` | Jenis box, kapasitas, dan definisi spacer |
| Ukuran | `/admin/sizes` | Definisi ukuran produk dengan dimensi spesifik per bentuk |
| Aturan Konsumsi | `/admin/consumption-rules` | Tingkat konsumsi glaze/engobe per meter persegi |
| Kalender Pabrik | `/admin/factory-calendar` | Hari kerja, hari libur, dan hari non-kerja per pabrik |
| Barang Jadi | `/warehouse/finished-goods` | Inventaris produk jadi dan pemeriksaan ketersediaan |
| Rekonsiliasi | `/warehouse/reconciliations` | Sesi penghitungan inventaris formal multi-material |
| Laporan | `/reports` | Ringkasan pesanan, utilisasi kiln, dan analitik produksi |
| Tablo | `/tablo` | Papan tampilan produksi layar penuh untuk monitor workshop |
| Detail Pesanan | `/orders/:id` | Tampilan detail pesanan tertentu beserta posisinya |
| Panduan | `/manager/guide` | Panduan PM ini (dalam aplikasi) |

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

- **Blocking** -- posisi yang diblokir karena kekurangan material, resep belum ada, stensil belum ada, pencocokan warna, data konsumsi belum ada (`AWAITING_CONSUMPTION_DATA`), atau penahanan QM
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
  +-- AWAITING_CONSUMPTION_DATA (diblokir: tingkat konsumsi resep belum ada)
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
| `awaiting_consumption_data` | Tugas pengukuran konsumsi ditutup, posisi pindah ke PLANNED (PM menerima risiko tingkat default) |
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
| `consumption_measurement` | Mengukur tingkat konsumsi (ml/m2) yang belum ada untuk suatu resep | PM |

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

## 8. Inspeksi Kiln

Inspeksi kiln secara rutin sangat penting untuk menjaga operasi pembakaran yang aman dan efisien. Fitur Inspeksi Kiln menyediakan alur kerja berbasis checklist yang terstruktur untuk mendokumentasikan kondisi kiln dan melacak perbaikan.

### 8.1. Ringkasan

Inspeksi kiln mingguan mencakup **8 kategori dengan 35 item inspeksi** secara total. Setiap inspeksi terkait dengan kiln tertentu dan dilakukan oleh Production Manager.

**Jalur**: `/manager/kiln-inspections`

### 8.2. Kategori Inspeksi

| # | Kategori | Item | Apa yang Diperiksa |
|---|---|---|---|
| 1 | Struktur Eksterior | 4-5 | Retakan, sambungan mortar, rangka logam, segel pintu, lubang ventilasi |
| 2 | Interior / Ruang Pembakaran | 4-5 | Lapisan bata, rak, tiang penyangga, kiln wash, kondisi lantai |
| 3 | Elemen Pemanas | 4-5 | Keutuhan elemen, koneksi, pembacaan resistansi, penyangga elemen |
| 4 | Kontrol Suhu | 4-5 | Akurasi thermocouple, fungsi controller, pyrometric cones, konsistensi zona |
| 5 | Sistem Kelistrikan | 4-5 | Pengkabelan, kontaktor, sekering, grounding, kondisi panel kontrol |
| 6 | Sistem Gas (jika ada) | 3-4 | Burner, saluran gas, regulator, sensor api, ventilasi |
| 7 | Peralatan Keselamatan | 3-4 | Tombol darurat, label peringatan, kedekatan alat pemadam, ketersediaan APD |
| 8 | Kesiapan Operasional | 3-4 | Inventaris perabotan kiln, alat pemuatan, buku log terkini, status kebersihan |

### 8.3. Cara Melakukan Inspeksi

1. Buka halaman **Kiln Inspections** (`/manager/kiln-inspections`).
2. Klik tab **New Inspection**.
3. **Pilih kiln** yang akan Anda inspeksi dari dropdown.
4. Checklist dimuat secara otomatis dengan semua 35 item yang dikelompokkan berdasarkan kategori.
5. Periksa setiap item dan pilih penilaian:

| Penilaian | Arti | Tindakan yang Diperlukan |
|---|---|---|
| **OK** | Item dalam kondisi baik | Tidak ada |
| **Not Applicable** | Item tidak berlaku untuk jenis kiln ini | Tidak ada |
| **Damaged** | Item rusak tetapi kiln masih bisa beroperasi dengan hati-hati | Otomatis ditandai untuk tindak lanjut |
| **Needs Repair** | Item memerlukan perbaikan sebelum penggunaan berikutnya | Otomatis ditandai untuk tindak lanjut, entri log perbaikan dibuat |

6. Tambahkan catatan opsional pada item apa pun untuk konteks tambahan (contoh: "Retakan kecil di pojok kiri atas, pantau minggu depan").
7. Klik **Submit Inspection** ketika semua item sudah dinilai.

> **Penting**: Item yang ditandai sebagai **Damaged** atau **Needs Repair** secara otomatis disorot dalam laporan inspeksi dan menghasilkan entri di Repair Log untuk pelacakan.

### 8.4. Meninjau Inspeksi Sebelumnya

- Tab **Inspection History** menampilkan semua inspeksi yang telah selesai diurutkan berdasarkan tanggal.
- Klik inspeksi mana pun untuk melihat laporan lengkap dengan semua penilaian dan catatan.
- Gunakan filter untuk melihat inspeksi kiln tertentu.
- Bandingkan inspeksi dari waktu ke waktu untuk melacak tren kerusakan.

### 8.5. Repair Log (Log Perbaikan)

Repair Log melacak setiap masalah yang diidentifikasi selama inspeksi dari laporan hingga penyelesaian.

**Status perbaikan**:

| Status | Arti |
|---|---|
| `open` | Masalah teridentifikasi, belum ditangani |
| `in_progress` | Pekerjaan perbaikan telah dimulai |
| `completed` | Perbaikan selesai dan terverifikasi |

**Alur kerja**:
1. Ketika item inspeksi dinilai **Damaged** atau **Needs Repair**, entri log perbaikan secara otomatis dibuat dengan status `open`.
2. Tugaskan perbaikan kepada orang atau tim yang sesuai.
3. Perbarui status menjadi `in_progress` ketika pekerjaan dimulai.
4. Tandai sebagai `completed` ketika perbaikan selesai dan terverifikasi.
5. Inspeksi kiln berikutnya harus mengkonfirmasi bahwa perbaikan efektif.

> **Praktik terbaik**: Tinjau Repair Log di awal setiap minggu. Prioritaskan item yang masih terbuka untuk kiln yang dijadwalkan untuk pembakaran mendatang.

---

## 9. Tugas Pengukuran Konsumsi

### 9.1. Apa Itu Tugas Pengukuran Konsumsi?

Ketika pesanan baru tiba dan posisi menggunakan metode aplikasi (contoh: SS, BS, SB) tetapi resep yang ditetapkan **tidak memiliki tingkat konsumsi yang diperlukan** (tingkat semprot atau kuas dalam ml/m2), sistem tidak dapat menghitung berapa banyak material yang perlu direservasi. Dalam hal ini, posisi diblokir dengan status `AWAITING_CONSUMPTION_DATA` dan **tugas pemblokir** bertipe `consumption_measurement` dibuat dan ditugaskan kepada PM.

### 9.2. Kapan Ini Terjadi?

Ini terjadi ketika **ketiga kondisi** terpenuhi:
1. Posisi memiliki resep yang ditetapkan (glaze atau engobe).
2. Aturan konsumsi menentukan metode aplikasi yang memerlukan tingkat tertentu (contoh: tingkat semprot untuk metode SS, tingkat kuas untuk metode BS).
3. Resep **tidak** memiliki bidang tingkat yang diperlukan terisi.

**Kode metode aplikasi dan tingkat yang dibutuhkan**:

| Kode | Nama Lengkap | Tingkat Engobe | Tingkat Glaze |
|---|---|---|---|
| `SS` | Semprot engobe + Semprot glaze | Tingkat semprot | Tingkat semprot |
| `BS` | Kuas engobe + Semprot glaze | Tingkat kuas | Tingkat semprot |
| `SB` | Semprot engobe + Kuas glaze | Tingkat semprot | Tingkat kuas |
| `S` | Semprot glaze saja (tanpa engobe) | -- | Tingkat semprot |
| `splashing` | Metode percikan | -- | Tingkat percikan |

### 9.3. Cara Menangani Tugas Pengukuran Konsumsi

**Langkah 1: Temukan tugas**

Tugas muncul di tab **Tasks** Anda dengan jenis `consumption_measurement`. Tugas ini ditandai sebagai **blocking**, artinya posisi terkait tidak dapat melanjutkan sampai tugas diselesaikan.

Deskripsi tugas mencakup:
- **Nama resep** -- resep mana yang belum memiliki tingkat
- **Jenis tingkat yang hilang** -- tingkat semprot (ml/m2) atau tingkat kuas (ml/m2)
- **Nomor pesanan dan posisi** -- pesanan mana yang menunggu

**Langkah 2: Ukur tingkat konsumsi secara fisik**

1. Siapkan potongan uji dengan ukuran dan material yang benar.
2. Aplikasikan glaze atau engobe menggunakan metode yang ditentukan (semprot atau kuas).
3. Ukur volume material yang digunakan (dalam ml).
4. Hitung luas potongan uji (dalam m2).
5. Bagi: **tingkat konsumsi = volume yang digunakan (ml) / luas (m2)**.

> **Tips**: Lakukan setidaknya 2-3 kali aplikasi uji dan rata-ratakan hasilnya untuk akurasi. Dokumentasikan kondisi pengujian (ukuran nozzle, tekanan, jarak untuk semprot; jenis kuas dan teknik untuk kuas).

**Langkah 3: Masukkan tingkat yang diukur**

1. Buka tugas dan klik tindakan untuk memasukkan tingkat konsumsi.
2. Masukkan tingkat yang diukur dalam **ml/m2**.
3. Konfirmasi entri.

**Langkah 4: Apa yang terjadi selanjutnya**

Setelah Anda memasukkan tingkat konsumsi:
- Resep diperbarui dengan nilai tingkat baru.
- Tugas pemblokir ditandai sebagai `done`.
- Status posisi berubah dari `AWAITING_CONSUMPTION_DATA` kembali ke `PLANNED`.
- Sistem melanjutkan reservasi material menggunakan tingkat yang baru dimasukkan.
- Semua posisi lain yang menggunakan resep dan metode aplikasi yang sama juga mendapat manfaat dari tingkat ini ke depannya.

### 9.4. Tips Praktis untuk Pengukuran

- **Simpan log pengukuran**: Catat semua pengukuran dengan tanggal, resep, metode, ukuran potongan uji, dan hasil. Ini membantu menyelesaikan perselisihan tentang tingkat di masa depan.
- **Standarkan kondisi**: Gunakan tekanan semprot, ukuran nozzle, dan jarak yang konsisten untuk hasil yang dapat direproduksi.
- **Untuk aplikasi kuas**: Catat jenis kuas dan teknik yang digunakan, karena ini sangat mempengaruhi tingkat.
- **Perbarui tingkat secara proaktif**: Jika Anda tahu resep akan digunakan dengan metode aplikasi baru, ukur tingkatnya terlebih dahulu untuk menghindari pemblokiran saat pesanan tiba.

---

## 11. Pemeliharaan Kiln

### 11.1. Ringkasan

Halaman Pemeliharaan Kiln menyediakan alur kerja terstruktur untuk menjadwalkan, melacak, dan menyelesaikan pemeliharaan preventif dan korektif pada kiln. Berbeda dengan Inspeksi Kiln (Bagian 8) yang fokus pada penilaian kondisi mingguan, Pemeliharaan Kiln mengelola pekerjaan terjadwal: penggantian elemen, kalibrasi thermocouple, perbaikan bata, pembersihan mendalam, dan lainnya.

**Jalur**: `/manager/kiln-maintenance`

### 11.2. Tab Halaman

| Tab | Fungsi |
|---|---|
| **Upcoming** | Menampilkan semua item pemeliharaan yang direncanakan diurutkan berdasarkan tanggal, dengan item yang terlambat disorot merah |
| **History** | Catatan pemeliharaan yang selesai dan dibatalkan |
| **Maintenance Types** | Mengelola katalog definisi jenis pemeliharaan (contoh: "Element replacement", "Deep clean") |

### 11.3. Menjadwalkan Pemeliharaan

1. Di tab **Upcoming**, klik **"+ Schedule Maintenance"**.
2. Isi formulir:
   - **Kiln** -- pilih kiln (difilter berdasarkan pabrik jika pabrik dipilih).
   - **Maintenance Type** -- pilih dari jenis yang telah ditentukan.
   - **Scheduled Date** -- kapan pemeliharaan harus dilakukan.
   - **Notes** -- instruksi tambahan.
3. Persyaratan diatur secara otomatis berdasarkan jenis pemeliharaan:
   - **Requires empty kiln** -- kiln harus dikosongkan sebelum pekerjaan dimulai.
   - **Requires cooled kiln** -- kiln harus pada suhu ruangan.
   - **Requires power off** -- pasokan listrik harus diputus.
4. Untuk pemeliharaan berulang, atur **Recurrence Interval** (dalam hari). Sistem secara otomatis menjadwalkan kejadian berikutnya setelah setiap penyelesaian.

### 11.4. Menyelesaikan Pemeliharaan

1. Temukan item pemeliharaan di tab **Upcoming**.
2. Klik **"Complete"**.
3. Opsional tambahkan **Completion Notes** yang menjelaskan apa yang telah dikerjakan.
4. Klik **"Confirm"**. Item berpindah ke tab History.
5. Jika item berulang, item terjadwal baru secara otomatis dibuat untuk interval berikutnya.

### 11.5. Kartu Ringkasan

Tab Upcoming menampilkan empat kartu ringkasan di bagian atas:

| Kartu | Keterangan |
|---|---|
| Total Scheduled | Semua item pemeliharaan yang direncanakan dalam 90 hari ke depan |
| Overdue | Item yang melewati tanggal jadwalnya (disorot merah) |
| Today | Item yang jatuh tempo hari ini (disorot kuning) |
| + Schedule | Tombol aksi cepat untuk menambah pemeliharaan baru |

### 11.6. Mengelola Jenis Pemeliharaan

Di tab **Maintenance Types** Anda dapat membuat, mengedit, dan menghapus definisi jenis. Setiap jenis memiliki:
- **Name** -- contoh: "Element replacement", "Thermocouple calibration"
- **Default requirements** -- apakah kiln harus kosong, dingin, atau listrik dimatikan
- **Default recurrence interval** -- periode pengulangan otomatis dalam hari

---

## 12. Keputusan Grinding

### 12.1. Ringkasan

Halaman Keputusan Grinding mengelola produk yang dikategorikan sebagai "grinding" selama tahap Sorting. Item-item ini memiliki cacat permukaan minor yang berpotensi dipulihkan dengan grinding atau, sebagai alternatif, dikirim ke Mana (pihak eksternal) untuk pembuangan atau pengerjaan ulang.

**Jalur**: `/manager/grinding`

### 12.2. Alur Status

Setiap item stok grinding memiliki salah satu dari tiga status:

| Status | Arti |
|---|---|
| **Pending** | Menunggu keputusan PM |
| **Grinding** | Diputuskan: akan di-grinding dan digunakan kembali |
| **Sent to Mana** | Diputuskan: dikirim ke pihak eksternal untuk pemrosesan |

### 12.3. Membuat Keputusan

Untuk setiap item yang tertunda, Anda melihat tiga tombol tindakan:

- **Grind** (hijau) -- tandai item untuk grinding internal dan penggunaan kembali.
- **Hold** (kuning) -- pertahankan item dalam status tertunda untuk keputusan nanti.
- **Mana** (merah) -- kirim ke Mana. Dialog konfirmasi muncul sebelum tindakan ini diselesaikan.

### 12.4. Kartu Ringkasan

Empat kartu KPI ditampilkan di bagian atas:

| Kartu | Keterangan |
|---|---|
| Total Items | Semua item stok grinding |
| Pending Decision | Item yang menunggu tindakan PM |
| Decided (Grind) | Item yang disetujui untuk grinding |
| Sent to Mana | Item yang dikirim ke pihak eksternal |

### 12.5. Filter

- **Tab status**: All / Pending / Decided (Grind) / Sent to Mana
- **Factory selector**: Filter berdasarkan pabrik
- **Pagination**: 50 item per halaman

---

## 13. Barang Jadi

### 13.1. Ringkasan

Halaman Barang Jadi (Finished Goods) melacak inventaris produk yang telah selesai dan siap untuk pengiriman atau penyimpanan. Halaman ini mencatat stok berdasarkan warna, ukuran, koleksi, jenis produk, dan pabrik.

**Jalur**: `/warehouse/finished-goods`

### 13.2. Tindakan Utama

- **+ Add Stock** -- menambah catatan barang jadi baru (pabrik, warna, ukuran, koleksi, jenis produk, jumlah, jumlah yang direservasi).
- **Edit** -- memperbarui jumlah atau jumlah yang direservasi untuk item yang sudah ada.
- **Check Availability** -- melakukan kueri di semua pabrik untuk melihat apakah kombinasi warna/ukuran tertentu tersedia dalam jumlah yang dibutuhkan. Sistem menampilkan pabrik mana yang memiliki stok yang cocok dan berapa banyak potongan yang tersedia.

### 13.3. Memahami Tabel

| Kolom | Keterangan |
|---|---|
| **Color** | Nama warna produk |
| **Size** | Ukuran produk |
| **Collection** | Koleksi produk |
| **Type** | Jenis produk (tile, sink, pebble) |
| **Factory** | Pabrik mana yang menyimpan stok |
| **Quantity** | Total potongan dalam stok |
| **Reserved** | Potongan yang direservasi untuk pesanan |
| **Available** | Jumlah dikurangi yang direservasi (kode warna: merah jika nol, kuning jika rendah, hijau jika cukup) |

### 13.4. Filter

- Dropdown **Factory** -- filter berdasarkan pabrik tertentu atau lihat semua.
- **Color search** -- cari berdasarkan nama warna (dengan debounce).
- **Pagination** -- 50 item per halaman.

### 13.5. Total

Total ringkasan di bagian bawah halaman menampilkan agregat Quantity, Reserved, dan Available untuk semua item yang terlihat.

---

## 14. Rekonsiliasi

### 14.1. Ringkasan

Halaman Rekonsiliasi (Reconciliations) mengelola sesi penghitungan inventaris formal. Berbeda dengan Audit Inventaris material tunggal (Bagian 3.6), Rekonsiliasi adalah acara terstruktur yang dapat mencakup beberapa material sekaligus. Digunakan untuk penghitungan stok penuh atau parsial secara berkala.

**Jalur**: `/warehouse/reconciliations`

### 14.2. Status Rekonsiliasi

| Status | Arti |
|---|---|
| **Scheduled** | Direncanakan untuk tanggal mendatang |
| **Draft** | Dibuat tetapi belum dimulai |
| **In Progress** | Sedang dalam proses penghitungan |
| **Completed** | Semua item dihitung dan penyesuaian diterapkan |
| **Cancelled** | Rekonsiliasi dibatalkan |

### 14.3. Membuat Rekonsiliasi

1. Klik **"+ New Reconciliation"**.
2. Pilih **Factory**.
3. Tambahkan **Notes** opsional (contoh: "Penghitungan stok bulanan -- gudang A").
4. Klik **"Create"**.

### 14.4. Bekerja dengan Rekonsiliasi

1. Klik baris rekonsiliasi untuk membukanya.
2. **Tambahkan item** -- pilih material yang akan dimasukkan dalam penghitungan.
3. Untuk setiap item, masukkan **jumlah aktual yang dihitung**.
4. Sistem menampilkan **saldo sistem** di samping jumlah yang dihitung dan menghitung **selisih**.
5. Ketika semua item dihitung, klik **"Complete"**.
6. Saat selesai, sistem menerapkan penyesuaian saldo sebagai transaksi audit inventaris.

### 14.5. Kartu Ringkasan

| Kartu | Keterangan |
|---|---|
| Total | Semua rekonsiliasi |
| In Progress | Rekonsiliasi aktif yang sedang dihitung |
| Completed | Rekonsiliasi yang telah selesai |
| Scheduled | Rekonsiliasi yang direncanakan untuk masa depan |

### 14.6. Filter

- **Factory Selector** -- filter berdasarkan pabrik.
- **Tab status** -- All / In Progress / Completed / Scheduled / Cancelled.

---

## 15. Laporan dan Analitik

### 15.1. Ringkasan

Halaman Laporan menyediakan metrik produksi yang diagregasi dengan filter rentang tanggal dan pabrik.

**Jalur**: `/reports`

### 15.2. Filter

- **Factory** -- pilih pabrik tertentu atau "All Factories".
- **Date range** -- pemilih tanggal Dari / Sampai (default 30 hari terakhir).

### 15.3. Ringkasan Pesanan

Empat kartu KPI di bagian atas:

| Kartu | Keterangan |
|---|---|
| **Total Orders** | Jumlah pesanan dalam periode yang dipilih (dengan jumlah yang sedang dalam proses sebagai subjudul) |
| **Completed** | Pesanan yang mencapai status shipped (dengan jumlah tepat waktu sebagai subjudul) |
| **On-time %** | Persentase pesanan yang selesai dan dikirim sesuai deadline. Hijau >= 80%, Kuning >= 50%, Merah < 50% |
| **Avg Days to Complete** | Rata-rata jumlah hari dari pembuatan pesanan hingga status shipped |

### 15.4. Utilisasi Kiln

Untuk setiap kiln, kartu menampilkan:

- **Nama kiln** dan badge persentase utilisasi (hijau >= 80%, kuning >= 50%, merah < 50%).
- **Progress bar** menampilkan utilisasi secara visual.
- **Total firings** jumlah pembakaran untuk periode tersebut.
- **Average load** (m2 per pembakaran).

Bagian ini membantu Anda mengidentifikasi kiln yang kurang dimanfaatkan yang bisa menerima batch tambahan dan kiln yang kelebihan beban yang mungkin memerlukan penyesuaian jadwal.

---

## 16. Kalender Pabrik

### 16.1. Ringkasan

Kalender Pabrik mengelola hari kerja, hari libur, dan hari non-kerja untuk setiap pabrik. Mesin penjadwalan menggunakan kalender ini untuk menghitung timeline produksi dan deadline yang akurat.

**Jalur**: `/admin/factory-calendar`

### 16.2. Tampilan Kalender

Halaman menampilkan grid kalender bulanan secara visual. Setiap hari diberi kode warna:

| Warna | Arti |
|---|---|
| **Putih** | Hari kerja normal |
| **Merah / ditandai** | Hari non-kerja (hari libur, hari istirahat) |

Klik hari mana pun untuk menambah atau menghapus entri hari libur. Klik dan seret untuk memilih rentang tanggal.

### 16.3. Navigasi

- **Panah bulan** -- maju atau mundur per bulan.
- **Panah tahun** -- maju atau mundur per tahun.
- **Factory selector** -- pilih kalender pabrik mana yang akan dikelola.

### 16.4. Preset Hari Libur Massal

Dua preset impor cepat tersedia:

- **Indonesian National Holidays** -- mengimpor hari libur nasional utama (Tahun Baru, Idul Fitri, Hari Kemerdekaan, Natal, dll.).
- **Balinese Holidays** -- mengimpor Nyepi, Galungan, Kuningan, dan hari upacara Bali lainnya.

Klik preset untuk melihat pratinjau tanggal, lalu konfirmasi untuk menambahkan semuanya sekaligus. Entri yang sudah ada tidak akan diduplikasi.

### 16.5. Menambah dan Menghapus Hari Libur

**Menambah**: Klik hari di kalender, masukkan nama (contoh: "Nyepi"), dan simpan.

**Menghapus**: Klik hari libur yang sudah ada dan konfirmasi penghapusan.

> **Penting**: Perubahan pada kalender pabrik dapat mempengaruhi timeline produksi yang terjadwal. Setelah perubahan kalender yang signifikan, pertimbangkan untuk memicu penjadwalan ulang dari halaman Schedule.

---

## 17. Pengelolaan Resep

### 17.1. Ringkasan

Halaman Resep memungkinkan PM untuk melihat dan mengelola resep glaze, engobe, dan produk. Setiap resep mendefinisikan bahan-bahannya dengan jumlah, tingkat aplikasi (semprot, kuas, percikan, sablon), dan tautan ke grup suhu untuk pembakaran.

**Jalur**: `/admin/recipes`

### 17.2. Bidang Resep

| Bidang | Keterangan |
|---|---|
| **Name** | Nama resep (contoh: "Moonjar White Glaze M-01") |
| **Type** | Product, Glaze, atau Engobe |
| **Color Collection** | Koleksi warna yang dimiliki resep ini |
| **Client** | Nama klien (jika resep khusus klien) |
| **Specific Gravity** | Kepadatan glaze/engobe yang dicampur (g/ml) |
| **Spray Rate** | Tingkat konsumsi untuk aplikasi semprot (ml/m2) |
| **Brush Rate** | Tingkat konsumsi untuk aplikasi kuas (ml/m2) |
| **Default** | Apakah resep ini adalah default untuk jenisnya |
| **Active** | Apakah resep saat ini sedang digunakan |

### 17.3. Bahan-bahan

Setiap resep memiliki daftar bahan yang dikelompokkan berdasarkan jenis material (Frits, Pigments, Oxides/Carbonates, Other). Untuk setiap bahan:
- **Material** -- dipilih dari katalog material.
- **Quantity** -- berat dalam formula resep.
- **Per-ingredient rates** -- tingkat semprot, kuas, percikan, dan sablon dapat diatur secara individual.

### 17.4. Tindakan Utama

- **Create** -- menambah resep baru dengan bahan-bahan.
- **Edit** -- mengubah bidang resep atau daftar bahan.
- **Duplicate** -- menyalin resep yang ada untuk membuat varian.
- **CSV Import** -- impor resep secara massal dari file CSV.

### 17.5. Tautan Grup Suhu

Resep dapat dihubungkan ke satu atau lebih grup suhu. Ini menentukan suhu kiln mana yang kompatibel dengan resep dan digunakan oleh algoritma pembentukan batch saat mengelompokkan posisi untuk co-firing.

---

## 18. Profil Pembakaran

### 18.1. Ringkasan

Profil Pembakaran (Firing Profiles) mendefinisikan kurva pemanasan dan pendinginan yang digunakan selama pembakaran kiln. Setiap profil menentukan tahapan suhu multi-interval: seberapa cepat kiln dipanaskan dari satu suhu ke suhu lainnya, dan bagaimana pendinginannya setelah itu.

**Jalur**: `/admin/firing-profiles`

### 18.2. Bidang Profil

| Bidang | Keterangan |
|---|---|
| **Name** | Nama profil (contoh: "Standard 1012°C -- 14h") |
| **Temperature Group** | Untuk grup suhu mana profil ini |
| **Total Duration** | Perkiraan total waktu pembakaran dalam jam |
| **Active** | Apakah profil ini tersedia untuk digunakan |

### 18.3. Tahap Pemanasan dan Pendinginan

Setiap profil memiliki dua daftar tahapan suhu:

**Tahap pemanasan** (type = heating):
- **Start Temp** -- suhu awal dalam °C (tahap pertama biasanya dimulai dari ~20°C).
- **End Temp** -- suhu target untuk tahap ini.
- **Rate** -- laju pemanasan dalam °C per jam.

**Tahap pendinginan** (type = cooling):
- **Start Temp** -- suhu di awal pendinginan (biasanya suhu puncak pembakaran).
- **End Temp** -- suhu di akhir tahap pendinginan ini.
- **Rate** -- laju pendinginan dalam °C per jam.

Anda dapat menambahkan beberapa interval untuk membuat kurva yang kompleks. Contoh:
- Tahap 1: 20°C -> 600°C pada 100°C/jam (pemanasan awal lambat)
- Tahap 2: 600°C -> 1012°C pada 50°C/jam (pendekatan lambat ke target)
- Pendinginan 1: 1012°C -> 600°C pada 80°C/jam (pendinginan awal terkontrol)
- Pendinginan 2: 600°C -> 20°C pada 120°C/jam (pendinginan alami)

### 18.4. Tindakan Utama

- **Create** -- mendefinisikan profil baru dengan tahap pemanasan dan pendinginan.
- **Edit** -- mengubah tahapan, laju, atau durasi.
- **Activate / Deactivate** -- mengaktifkan/menonaktifkan ketersediaan profil.

---

## 19. Grup Suhu

### 19.1. Ringkasan

Grup Suhu (Temperature Groups) mengkategorikan suhu pembakaran. Setiap grup memiliki nama, suhu target (°C), dan urutan tampilan. Resep dan profil pembakaran dihubungkan ke grup suhu, memungkinkan sistem untuk secara otomatis mengelompokkan posisi yang kompatibel untuk co-firing.

**Jalur**: `/admin/temperature-groups`

### 19.2. Bidang

| Bidang | Keterangan |
|---|---|
| **Name** | Nama grup (contoh: "Standard 1012°C", "Low-fire 800°C") |
| **Temperature** | Suhu target pembakaran dalam °C |
| **Description** | Catatan opsional |
| **Display Order** | Posisi urutan dalam daftar |

### 19.3. Tautan Resep

Setiap grup suhu menampilkan resep-resep yang terhubung. Ini memudahkan untuk melihat glaze dan engobe mana yang dibakar pada suhu yang sama dan bisa berbagi batch kiln.

### 19.4. Tindakan Utama

- **Create** -- menambah grup suhu baru.
- **Edit** (inline) -- mengubah nama, suhu, deskripsi, atau urutan tampilan.
- **Delete** -- menghapus grup suhu (hanya jika tidak ada resep yang terhubung).
- **CSV Import** -- impor massal dari file CSV.

---

## 20. Pengelolaan Tahapan

### 20.1. Ringkasan

Halaman Tahapan (Stages) mengelola definisi tahapan produksi yang dilalui posisi. Setiap tahapan memiliki nama dan urutan yang menentukan posisinya dalam alur produksi.

**Jalur**: `/admin/stages`

### 20.2. Bidang

| Bidang | Keterangan |
|---|---|
| **Name** | Nama tahapan (contoh: "Glazing", "Firing", "Sorting", "QC") |
| **Order** | Posisi numerik dalam urutan produksi |

### 20.3. Tindakan Utama

- **Create** -- menambah tahapan produksi baru.
- **Edit** -- mengubah nama atau urutan.
- **Delete** -- menghapus tahapan (hanya jika tidak direferensikan oleh posisi aktif).

> **Catatan**: Definisi tahapan digunakan oleh mesin penjadwalan dan siklus hidup posisi. Mengubah urutan atau nama tahapan dapat mempengaruhi bagaimana posisi ditampilkan di halaman Schedule.

---

## 21. Jadwal Pembakaran

### 21.1. Ringkasan

Halaman Jadwal Pembakaran (Firing Schedules) mengelola template jadwal pembakaran per kiln. Jadwal pembakaran mendefinisikan parameter pembakaran yang direncanakan untuk kiln tertentu, termasuk data waktu dan konfigurasi.

**Jalur**: `/admin/firing-schedules`

### 21.2. Bidang

| Bidang | Keterangan |
|---|---|
| **Kiln** | Kiln mana yang menerapkan jadwal ini |
| **Name** | Nama jadwal (contoh: "Standard weekday firing") |
| **Schedule Data** | Konfigurasi JSON dengan parameter pembakaran |
| **Default** | Apakah ini jadwal default untuk kiln tersebut |

### 21.3. Filter

- **Dropdown Kiln** -- filter jadwal berdasarkan kiln.

### 21.4. Tindakan Utama

- **Create** -- menambah jadwal pembakaran baru untuk kiln.
- **Edit** -- mengubah parameter jadwal.
- **Set as Default** -- menandai jadwal sebagai default untuk kiln-nya.
- **Delete** -- menghapus jadwal.

---

## 22. Pengelolaan Gudang

### 22.1. Ringkasan

Halaman Gudang (Warehouses) mengelola bagian gudang tempat material disimpan. Setiap bagian milik suatu pabrik dan dapat ditugaskan kepada pengguna tertentu.

**Jalur**: `/admin/warehouses`

### 22.2. Bidang

| Bidang | Keterangan |
|---|---|
| **Name** | Nama bagian (contoh: "Raw Materials Store A") |
| **Code** | Kode identifikasi singkat |
| **Factory** | Pabrik mana yang memiliki bagian ini |
| **Type** | Section (fisik), Warehouse (gudang penuh), atau Virtual |
| **Managed By** | Pengguna yang bertanggung jawab atas bagian ini |
| **Display Order** | Posisi urutan |
| **Default** | Apakah ini bagian default untuk pabriknya |
| **Active** | Apakah bagian saat ini sedang digunakan |

### 22.3. Tindakan Utama

- **Create** -- menambah bagian gudang baru.
- **Edit** -- mengubah detail bagian.
- **Delete** -- menghapus bagian.
- **CSV Import** -- impor massal dari file CSV.

---

## 23. Pengelolaan Kemasan

### 23.1. Ringkasan

Halaman Kemasan (Packaging) mengelola definisi jenis box dan kapasitasnya. Setiap jenis box menentukan berapa banyak potongan dari setiap ukuran yang muat per box, dan material spacer mana yang digunakan.

**Jalur**: `/admin/packaging`

### 23.2. Konsep Utama

- **Box Type** -- jenis box kemasan tertentu yang terhubung ke material (box itu sendiri adalah material dalam inventaris).
- **Capacity** -- untuk setiap ukuran produk, mendefinisikan jumlah potongan per box dan luas (m2) per box.
- **Spacers** -- untuk setiap ukuran produk, mendefinisikan material spacer mana yang digunakan dan berapa banyak spacer dalam setiap box.

### 23.3. Tindakan Utama

- **Create** -- menambah jenis box baru dengan kapasitas dan definisi spacer.
- **Edit** -- mengubah kapasitas atau konfigurasi spacer.
- **CSV Import** -- impor definisi kemasan secara massal.

---

## 24. Pengelolaan Ukuran

### 24.1. Ringkasan

Halaman Ukuran (Sizes) mengelola definisi ukuran produk. Setiap ukuran memiliki dimensi, bentuk, dan luas yang dihitung secara otomatis yang digunakan untuk perhitungan konsumsi material.

**Jalur**: `/admin/sizes`

### 24.2. Bidang

| Bidang | Keterangan |
|---|---|
| **Name** | Nama ukuran (contoh: "30x60", "20x20 round") |
| **Width** | Lebar dalam mm |
| **Height** | Tinggi dalam mm |
| **Thickness** | Ketebalan default dalam mm |
| **Shape** | Rectangle, Round, Triangle, Octagon, Freeform |
| **Shape Dimensions** | Parameter dimensi tambahan untuk bentuk non-persegi panjang |
| **Area** | Luas yang dihitung dalam cm2 (otomatis berdasarkan bentuk dan dimensi) |
| **Custom** | Apakah ini ukuran khusus sekali pakai |

### 24.3. Tindakan Utama

- **Create** -- menambah definisi ukuran baru dengan editor dimensi spesifik per bentuk.
- **Edit** -- mengubah dimensi atau bentuk.
- **Delete** -- menghapus ukuran (hanya jika tidak digunakan oleh posisi aktif).
- **CSV Import** -- impor ukuran secara massal.

---

## 25. Tablo (Papan Tampilan Produksi)

### 25.1. Ringkasan

Halaman Tablo adalah papan tampilan produksi layar penuh yang dirancang untuk ditampilkan di TV atau monitor workshop. Halaman ini menyediakan ringkasan status produksi secara real-time tanpa memerlukan interaksi.

**Jalur**: `/tablo`

### 25.2. Penggunaan

- Buka halaman Tablo di layar khusus di area produksi.
- Tampilan diperbarui secara otomatis untuk menampilkan status produksi terkini.
- Tidak diperlukan tindakan autentikasi di halaman ini -- ini adalah tampilan hanya-baca.

---

## 26. Tips dan Praktik Terbaik

### 26.1. Rutinitas Harian

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
14. **Lakukan inspeksi kiln** -- selesaikan checklist 35 item untuk setiap kiln aktif (lihat Bagian 8).
15. **Tinjau Repair Log** -- tindak lanjuti item perbaikan yang terbuka dan sedang dalam proses.
16. Periksa jadwal pemeliharaan kiln.
17. Tinjau dan perbarui aturan konsumsi jika diperlukan.
18. Pertimbangkan penjadwalan ulang pabrik penuh jika ada perubahan signifikan.

### 26.2. Praktik Terbaik Pemilih Pabrik

- Selalu pilih **pabrik tertentu** sebelum melakukan operasi yang mengubah data (membuat pesanan, membentuk batch, menerima material).
- Gunakan mode "All Factories" hanya untuk tinjauan umum dan pemantauan.
- Jika Anda hanya ditugaskan ke satu pabrik, pemilih disembunyikan dan pabrik Anda selalu aktif.

### 26.3. Menangani Kekurangan Material

1. Pertama, periksa riwayat transaksi untuk memahami tren konsumsi.
2. Verifikasi pengaturan min_balance masih akurat -- sesuaikan melalui Edit jika perlu.
3. Koordinasikan dengan Purchaser untuk memesan material yang kritis.
4. Gunakan force-unblock untuk kekurangan material hanya sebagai pilihan terakhir -- ini membuat saldo negatif.

### 26.4. Praktik Terbaik Audit Inventaris

- Lakukan audit berkala (mingguan atau bulanan) untuk material dengan perputaran tinggi.
- Selalu masukkan alasan yang jelas dan spesifik -- "penghitungan ulang" tidak membantu; "Penghitungan ulang setelah tumpahan pada 15 Maret" lebih baik.
- Bandingkan selisih audit dengan riwayat transaksi terbaru untuk mengidentifikasi pola.
- Jika Anda secara konsisten melihat perbedaan, tinjau aturan konsumsi -- tingkatnya mungkin perlu disesuaikan.

### 26.5. Notifikasi

PM menerima notifikasi untuk:
- Pesanan baru yang masuk dari Sales webhook
- Kerusakan kiln
- Kekurangan material kritis
- Permintaan pembatalan dan perubahan dari Sales

**Bot Telegram** mengirim ringkasan harian pukul 21:00 (bahasa Indonesia) dengan:
- Daftar tugas lengkap untuk hari berikutnya
- KPI untuk hari ini

### 26.6. Tips Antarmuka

- Gunakan **kotak pencarian** di halaman Material untuk mencari material berdasarkan nama atau kode dengan cepat.
- Di halaman Jadwal, **Status Dropdown** hanya menampilkan transisi yang valid -- Anda tidak bisa salah memilih status yang tidak diizinkan.
- Dialog **Transaction History** bisa di-scroll -- transaksi lebih lama ada di bawah.
- Saat membuat aturan konsumsi dengan beberapa ukuran, gunakan **mode Multi-size** untuk menghemat waktu.

---

> **Ada pertanyaan?** Hubungi administrator sistem atau gunakan **AI Chat** bawaan di dashboard PM.
