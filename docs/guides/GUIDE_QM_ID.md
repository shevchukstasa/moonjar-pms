# Panduan Quality Manager (QM) -- Moonjar PMS

> Versi: 1.0 | Tanggal: 2026-04-06
> Moonjar Production Management System

---

## Daftar Isi

1. [Memulai](#1-memulai)
2. [Ringkasan Dashboard](#2-ringkasan-dashboard)
3. [Antrian QC](#3-antrian-qc)
4. [Checklist QC Pra-Kiln](#4-checklist-qc-pra-kiln)
5. [Checklist QC Akhir](#5-checklist-qc-akhir)
6. [Blokir QM](#6-blokir-qm)
7. [Kartu Masalah](#7-kartu-masalah)
8. [Identifikasi & Klasifikasi Cacat](#8-identifikasi--klasifikasi-cacat)
9. [Matriks Koefisien Cacat](#9-matriks-koefisien-cacat)
10. [Keputusan Grinding](#10-keputusan-grinding)
11. [Foto Kualitas & Analisis](#11-foto-kualitas--analisis)
12. [Bekerja dengan Production Manager](#12-bekerja-dengan-production-manager)
13. [Inspeksi Kiln](#13-inspeksi-kiln)
14. [Perintah Bot Telegram](#14-perintah-bot-telegram)
15. [Laporan dan Analitik](#15-laporan-dan-analitik)
16. [Referensi Navigasi](#16-referensi-navigasi)
17. [Tips dan Praktik Terbaik](#17-tips-dan-praktik-terbaik)

---

## 1. Memulai

### 1.1. Masuk ke Sistem

1. Buka dashboard Moonjar PMS di browser Anda.
2. Masuk menggunakan salah satu metode:
   - **Google OAuth** -- klik "Sign in with Google"
   - **Email dan kata sandi** -- masukkan kredensial Anda dan klik "Login"
3. Setelah autentikasi, sistem mendeteksi peran Anda dan mengarahkan ke `/quality` -- dashboard Quality Manager.

### 1.2. Pemilihan Pabrik

Saat login, sistem memeriksa penugasan pabrik Anda:

- **Satu pabrik**: Terpilih otomatis, dropdown tidak terlihat.
- **Beberapa pabrik**: Dropdown pemilih pabrik muncul di pojok kanan atas.

> **Penting**: Pemeriksaan kualitas bersifat spesifik per pabrik. Selalu pastikan pabrik yang tepat terpilih sebelum melakukan inspeksi.

### 1.3. Kemampuan Peran

Sebagai Quality Manager, Anda dapat:

- Melakukan inspeksi QC Pra-Kiln dan QC Akhir
- Membuat dan menyelesaikan blokir QM pada posisi
- Membuat dan mengelola kartu masalah
- Mengklasifikasikan cacat dan menentukan tindakan korektif
- Membuat keputusan grinding pada produk cacat
- Berpartisipasi dalam inspeksi kiln
- Mengunggah dan meninjau foto kualitas

---

## 2. Ringkasan Dashboard

Dashboard QM (`/quality`) diatur dengan kartu KPI di atas dan antarmuka tab di bawah.

### 2.1. Kartu KPI

Empat metrik utama ditampilkan di atas:

| KPI | Warna | Deskripsi |
|---|---|---|
| **Menunggu QC** | Oranye | Posisi yang menunggu pemeriksaan kualitas |
| **Diblokir** | Merah | Posisi yang saat ini diblokir oleh QM |
| **Kartu Masalah** | Kuning | Kartu masalah terbuka yang memerlukan tindakan |
| **Pemeriksaan Hari Ini** | Hijau | Jumlah inspeksi yang selesai hari ini |

### 2.2. Tab

| Tab | Tujuan |
|---|---|
| **Antrian QC** | Posisi yang siap untuk inspeksi kualitas |
| **Blokir QM** | Blokir kualitas aktif pada posisi |
| **Kartu Masalah** | Pelacakan dan penyelesaian masalah |

---

## 3. Antrian QC

### 3.1. Ikhtisar

Antrian QC menampilkan semua posisi yang telah mencapai tahap pemeriksaan kualitas. Ini adalah posisi yang menunggu inspeksi Anda.

### 3.2. Informasi Posisi

Untuk setiap posisi dalam antrian, Anda melihat:

| Kolom | Deskripsi |
|---|---|
| Nomor Pesanan | Referensi pesanan induk |
| Warna | Warna/glasir produk |
| Ukuran | Dimensi produk |
| Koleksi | Koleksi produk |
| Jumlah | Jumlah potongan |
| Tahap | Tahap produksi saat ini |
| Status | Status posisi saat ini |

### 3.3. Melakukan Pemeriksaan Kualitas

1. Klik pada posisi di Antrian QC.
2. **Dialog Pemeriksaan Kualitas** terbuka dengan checklist lengkap.
3. Periksa setiap item checklist (lihat bagian 4 dan 5 untuk detail).
4. Tandai setiap item sebagai Lulus atau Gagal.
5. Untuk item yang gagal, tambahkan catatan yang menjelaskan masalah.
6. Unggah foto jika diperlukan (terutama untuk cacat).
7. Kirim hasil inspeksi:
   - **Lulus** -- posisi maju ke tahap berikutnya
   - **Gagal** -- posisi diblokir atau dikirim ke tindakan korektif

### 3.4. Operasi Massal

Saat beberapa posisi dari batch yang sama memiliki karakteristik kualitas identik, Anda dapat:

1. Inspeksi satu posisi secara menyeluruh
2. Terapkan hasil yang sama ke posisi lain dalam batch (jika produk identik)

> **Penting**: Jangan pernah meluluskan secara massal tanpa memeriksa fisik setidaknya sampel dari setiap posisi. Dokumentasikan ukuran sampel di catatan.

---

## 4. Checklist QC Pra-Kiln

QC Pra-Kiln dilakukan **sebelum** ubin dimasukkan ke kiln. Ini menangkap masalah yang akan menjadi permanen setelah pembakaran.

### 4.1. Item Checklist

| Item | Yang Diperiksa |
|---|---|
| **Kualitas Permukaan** | Tidak ada retakan, gumpil, atau goresan pada permukaan biskit |
| **Aplikasi Glasir** | Penutupan merata, ketebalan benar, tidak ada area kosong |
| **Kecocokan Warna Glasir** | Warna cocok dengan sampel yang disetujui |
| **Kualitas Tepi** | Tepi bersih, tidak ada gumpil, bentuk benar |
| **Ketebalan** | Dalam toleransi mm yang ditentukan |
| **Dimensi** | Panjang dan lebar dalam toleransi |
| **Lapisan Engobe** | Ada dan merata (jika ditentukan) |
| **Penempatan Stensil** | Pola diposisikan dengan benar (jika berlaku) |
| **Status Pengeringan** | Benar-benar kering sebelum pembakaran |

### 4.2. Kegagalan Pra-Kiln yang Umum

| Masalah | Tingkat Keparahan | Tindakan Tipikal |
|---|---|---|
| Glasir tidak merata | Sedang | Kembalikan ke tahap glazing |
| Warna salah | Tinggi | Blokir dan eskalasi ke PM |
| Biskit retak | Tinggi | Tolak dan hapus |
| Ubin basah | Rendah | Kembalikan ke pengeringan |
| Stensil salah | Tinggi | Blokir dan verifikasi dengan PM |

### 4.3. Mencatat Hasil

Untuk setiap item checklist:

1. Pilih **Lulus** (hijau) atau **Gagal** (merah)
2. Untuk kegagalan, pilih penyebab cacat dari dropdown
3. Tambahkan catatan deskriptif
4. Unggah foto yang menunjukkan cacat (disarankan untuk semua kegagalan)

---

## 5. Checklist QC Akhir

QC Akhir dilakukan **setelah** pembakaran, sebelum ubin berpindah ke sortir dan pengemasan.

### 5.1. Item Checklist

| Item | Yang Diperiksa |
|---|---|
| **Finishing Permukaan** | Halus, tanpa lubang jarum, tanpa crawling, tanpa blistering |
| **Konsistensi Warna** | Cocok dengan sampel yang disetujui, tanpa variasi warna dalam batch |
| **Adhesi Glasir** | Tidak mengelupas atau terdelaminasi |
| **Dimensi Pasca-Bakar** | Dalam toleransi penyusutan |
| **Lengkungan** | Ubin datar, tidak melengkung |
| **Gumpil Tepi** | Tidak ada gumpil dari penanganan kiln |
| **Retakan** | Tidak ada retakan pembakaran (dunting, kejutan termal) |
| **Crazing** | Tidak ada jaringan retakan halus di glasir |
| **Kualitas Pola** | Pola stensil/sablon utuh dan tajam (jika berlaku) |

### 5.2. Cacat Pasca-Pembakaran yang Umum

| Cacat | Deskripsi | Penyebab Tipikal |
|---|---|---|
| **Pinholing** | Lubang kecil di permukaan glasir | Gas keluar saat pembakaran |
| **Crawling** | Glasir menarik diri dari permukaan | Biskit kotor atau glasir terlalu tebal |
| **Blistering** | Gelembung terangkat di glasir | Pembakaran berlebihan atau kontaminasi |
| **Dunting** | Retakan dari tekanan termal | Pendinginan terlalu cepat |
| **Crazing** | Jaringan retakan halus | Ketidakcocokan ekspansi glasir-bodi |
| **Lengkungan** | Ubin tidak datar | Suhu kiln tidak merata atau penyangga |
| **Pergeseran warna** | Berbeda dari warna yang diharapkan | Deviasi suhu atau atmosfer |
| **Black coring** | Pusat gelap pada penampang | Pembakaran kurang, bahan organik tidak terbakar habis |

### 5.3. Penilaian Grade

Setelah inspeksi, berikan grade kualitas:

| Grade | Deskripsi | Tindakan |
|---|---|---|
| **A** | Sempurna, memenuhi semua spesifikasi | Lulus ke pengemasan |
| **B** | Masalah kosmetik minor, masih bisa dijual | Lulus ke pengemasan (tandai sebagai grade B) |
| **C** | Masalah signifikan, perlu tindakan korektif | Pertimbangkan grinding atau tolak |
| **Tolak** | Tidak bisa dipakai, tidak memenuhi standar minimum | Hapus, catat data cacat |

---

## 6. Blokir QM

### 6.1. Apa Itu Blokir QM?

Blokir QM adalah penahanan yang ditempatkan pada posisi oleh Quality Manager. Ini mencegah posisi maju dalam produksi sampai masalah kualitas diselesaikan.

### 6.2. Membuat Blokir QM

1. Dari Antrian QC, temukan posisi dengan masalah kualitas.
2. Klik tombol aksi **Blokir**.
3. Isi:
   - **Alasan** -- mengapa Anda memblokir (wajib)
   - **Kategori** -- jenis masalah kualitas
   - **Foto** -- lampirkan foto bukti (disarankan)
4. Kirim blokir.

Status posisi berubah untuk menyertakan penahanan QM, dan tugas pemblokir dibuat.

### 6.3. Menyelesaikan Blokir QM

1. Buka tab **Blokir QM**.
2. Temukan blokir yang ingin diselesaikan.
3. Klik **Selesaikan**.
4. Isi:
   - **Resolusi** -- apa yang dilakukan untuk memperbaiki masalah
   - **Hasil** -- lulus (lanjutkan produksi) atau tolak (hapus)
5. Kirim resolusi.

### 6.4. Jenis Blokir

| Kategori | Deskripsi |
|---|---|
| **Ketidakcocokan Warna** | Warna produk tidak sesuai spesifikasi |
| **Cacat Permukaan** | Cacat fisik pada permukaan |
| **Masalah Dimensi** | Ukuran atau ketebalan di luar toleransi |
| **Penyimpangan Proses** | Proses produksi tidak diikuti dengan benar |
| **Masalah Material** | Kekhawatiran kualitas bahan baku |

---

## 7. Kartu Masalah

### 7.1. Ikhtisar

Kartu Masalah adalah cara formal untuk melacak masalah kualitas yang memerlukan investigasi dan tindakan korektif. Berbeda dengan Blokir QM (yang menahan posisi tertentu), Kartu Masalah menangani masalah sistemik.

### 7.2. Membuat Kartu Masalah

1. Buka tab **Kartu Masalah**.
2. Klik **+ Buat Kartu Masalah**.
3. Isi:
   - **Judul** -- deskripsi singkat masalah
   - **Deskripsi** -- penjelasan detail
   - **Tingkat Keparahan** -- rendah, sedang, tinggi, kritis
   - **Kategori** -- klasifikasi jenis cacat
   - **Pesanan Terkait** -- tautan ke pesanan tertentu (opsional)
4. Kirim.

### 7.3. Siklus Hidup Kartu Masalah

| Status | Deskripsi |
|---|---|
| **Terbuka** | Masalah teridentifikasi, investigasi belum dimulai |
| **Investigasi** | Analisis akar penyebab sedang berlangsung |
| **Tindakan Korektif** | Perbaikan sedang diterapkan |
| **Verifikasi** | Memeriksa apakah perbaikan berhasil |
| **Ditutup** | Masalah diselesaikan dan diverifikasi |

### 7.4. Memperbarui Kartu Masalah

1. Klik pada kartu masalah.
2. Tambahkan catatan investigasi, temuan akar penyebab, atau tindakan korektif.
3. Perbarui status seiring perkembangan investigasi.
4. Lampirkan foto atau dokumen pendukung.

> **Praktik terbaik**: Selalu dokumentasikan akar penyebab, bukan hanya gejalanya. "Glasir terlalu tebal" adalah gejala. "Tekanan spray gun terlalu tinggi karena nozzle aus" adalah akar penyebab.

---

## 8. Identifikasi & Klasifikasi Cacat

### 8.1. Kategori Cacat

Cacat di Moonjar PMS diorganisir secara hierarkis:

1. **Jenis Cacat** -- kategori luas (permukaan, struktural, dimensional, estetika)
2. **Penyebab Cacat** -- kode penyebab spesifik dengan deskripsi
3. **Tingkat Keparahan** -- rendah, sedang, tinggi, kritis

### 8.2. Mencatat Cacat

Saat Anda menemukan cacat selama QC:

1. Pilih penyebab cacat dari dropdown sistem
2. Masukkan jumlah potongan yang terkena dampak
3. Tambahkan catatan deskriptif
4. Unggah foto
5. Sistem mencatat ini terhadap posisi dan menghitung tingkat cacat

### 8.3. Pemantauan Tingkat Cacat

Sistem melacak tingkat cacat di berbagai tingkat:

- **Per posisi** -- tingkat cacat untuk produksi tertentu
- **Per pesanan** -- tingkat cacat agregat di semua posisi dalam pesanan
- **Per pabrik** -- tingkat cacat seluruh pabrik
- **Per glasir** -- tingkat cacat per jenis glasir (membantu mengidentifikasi resep bermasalah)

Saat tingkat cacat melebihi ambang batas yang dikonfigurasi, sistem:

1. Menampilkan **DefectAlertBanner** di dashboard PM
2. Membuat kartu masalah otomatis
3. Mengirim notifikasi Telegram

---

## 9. Matriks Koefisien Cacat

### 9.1. Apa Itu?

Koefisien Cacat adalah matriks 2D yang memprediksi tingkat cacat yang diharapkan berdasarkan dua faktor:

- **Jenis glasir** (baris)
- **Jenis produk** (kolom)

Ini menggantikan model 1D yang lebih sederhana yang hanya menggunakan ukuran produk.

### 9.2. Cara Kerjanya

Untuk setiap kombinasi glasir-produk, matriks menyimpan persentase cacat yang diharapkan. Contoh:

| Glasir \ Produk | Ubin 10x10 | Ubin 15x15 | Ubin 20x20 | Wastafel |
|---|---|---|---|---|
| **Authentic** | 3% | 4% | 5% | 8% |
| **Raku** | 8% | 10% | 12% | 15% |
| **Gold** | 5% | 7% | 9% | 12% |

### 9.3. Penggunaan

Koefisien cacat digunakan untuk:

1. **Merencanakan kelebihan produksi** -- jika tingkat cacat yang diharapkan 10%, produksi 10% lebih
2. **Menetapkan target kualitas** -- bandingkan tingkat cacat aktual dengan yang diharapkan
3. **Mengidentifikasi anomali** -- saat tingkat cacat aktual jauh melebihi yang diharapkan, sistem memicu peringatan

### 9.4. Memperbarui Koefisien

Sebagai Quality Manager, Anda dapat mengusulkan pembaruan matriks koefisien cacat berdasarkan data produksi aktual. Perubahan melalui admin untuk persetujuan.

> **Tips**: Tinjau dan usulkan pembaruan koefisien setiap kuartal. Seiring tim memperbaiki proses, tingkat cacat yang diharapkan seharusnya menurun.

---

## 10. Keputusan Grinding

### 10.1. Ikhtisar

Navigasi ke `/manager/grinding` untuk halaman Keputusan Grinding. Saat ubin yang sudah dibakar memiliki cacat permukaan minor, grinding terkadang dapat mengembalikan ke kondisi layak jual.

### 10.2. Alur Kerja Keputusan

1. Setelah QC Akhir, ubin cacat yang menjadi kandidat grinding muncul di antrian Keputusan Grinding.
2. Untuk setiap ubin/batch, evaluasi:
   - **Jenis cacat** -- apakah bisa di-grinding? (kekasaran permukaan, gumpil minor, glasir tidak merata)
   - **Kedalaman cacat** -- bisakah grinding menjangkau tanpa mengorbankan integritas ubin?
   - **Analisis biaya-manfaat** -- apakah grinding lebih murah daripada membuat ulang?
3. Pilih keputusan:
   - **Grinding** -- kirim ke tahap grinding
   - **Tolak** -- hapus (cacat terlalu parah)
   - **Bakar ulang** -- coba perbaiki dengan siklus pembakaran lagi

### 10.3. Cacat yang Tidak Bisa Di-Grinding

Cacat berikut tidak bisa diperbaiki dengan grinding:

- Retakan dalam (integritas struktural terganggu)
- Ketidakcocokan warna (grinding tidak mengubah warna)
- Lengkungan (grinding mengubah ketebalan, bukan kerataan)
- Crazing (retakan menembus lapisan glasir)
- Black coring (cacat internal)

### 10.4. Mencatat Hasil Grinding

Setelah grinding selesai, periksa hasilnya:

1. Lulus -- ubin memenuhi standar kualitas setelah grinding
2. Gagal -- grinding tidak memperbaiki masalah, ubin harus ditolak

Catat hasilnya di sistem untuk memperbarui status posisi dan pelacakan cacat.

---

## 11. Foto Kualitas & Analisis

### 11.1. Pengunggahan Foto

Foto adalah bagian penting dari dokumentasi kualitas. Unggah foto:

- Selama QC Pra-Kiln (masalah aplikasi glasir)
- Selama QC Akhir (cacat pembakaran)
- Saat membuat Blokir QM (bukti)
- Saat membuat Kartu Masalah (dokumentasi)

### 11.2. Analisis Foto Berbasis AI

Sistem menyertakan kemampuan AI vision untuk foto kualitas:

- **Deteksi cacat** -- AI dapat mengidentifikasi cacat umum dari foto
- **Pencocokan warna** -- AI membandingkan warna produk dengan sampel spesifikasi
- **Analisis permukaan** -- AI mengevaluasi keseragaman permukaan

Untuk menggunakan analisis AI:
1. Unggah foto yang jelas dan terang dari cacat atau produk
2. Sistem secara otomatis menjalankan analisis
3. Tinjau penilaian AI dan konfirmasi atau ubah

> **Tips**: Untuk hasil analisis AI terbaik, foto cacat dengan pencahayaan yang baik, sertakan kartu referensi warna, dan ambil dari depan (bukan dari sudut).

---

## 12. Bekerja dengan Production Manager

### 12.1. Alur Komunikasi

QM dan PM bekerja sama erat. Titik interaksi kunci:

| Situasi | Tindakan QM | Tindakan PM |
|---|---|---|
| Cacat ditemukan saat QC | Buat Blokir QM atau gagalkan posisi | Tinjau blokir, putuskan rework atau penolakan |
| Lonjakan tingkat cacat | Buat Kartu Masalah | Investigasi akar penyebab di produksi |
| Ketidakcocokan warna | Blokir posisi, unggah foto perbandingan | Periksa resep dan proses glazing |
| Masalah resep diduga | Dokumentasikan temuan, tautkan ke resep | Sesuaikan parameter resep |
| Force unblock diperlukan | Tinjau dan setujui aspek kualitas | Eksekusi force unblock |

### 12.2. Jalur Eskalasi

Jika masalah kualitas tidak ditangani:

1. Buat Kartu Masalah (jika belum)
2. Tingkatkan keparahan ke "Kritis"
3. Sistem mengirim notifikasi Telegram ke CEO
4. Jadwalkan rapat review dengan PM dan CEO

---

## 13. Inspeksi Kiln

### 13.1. Ikhtisar

Navigasi ke `/manager/kiln-inspections` untuk berpartisipasi dalam penilaian kondisi kiln mingguan.

### 13.2. Checklist Inspeksi

Inspeksi kiln memeriksa kondisi fisik kiln:

- Dinding dan langit-langit interior -- retakan, pengelupasan, keausan
- Elemen pemanas -- kerusakan yang terlihat, titik panas
- Segel pintu -- integritas, kebocoran panas
- Keseragaman suhu -- berdasarkan data log pembakaran
- Kondisi rak -- keausan, lengkungan, kontaminasi

---

## 14. Perintah Bot Telegram

| Perintah | Deskripsi |
|---|---|
| `/start` | Inisialisasi koneksi bot |
| `/mystats` | Lihat statistik QC Anda |
| `/stock` | Periksa level stok material |
| `/help` | Daftar semua perintah yang tersedia |

### 14.1. Notifikasi Otomatis

Sebagai QM, Anda menerima notifikasi untuk:

- Posisi baru yang siap untuk QC
- Ambang batas tingkat cacat terlampaui
- Perubahan status kartu masalah
- Briefing pagi dengan ringkasan kualitas

---

## 15. Laporan dan Analitik

### 15.1. Metrik Kualitas

Navigasi ke `/reports` untuk analitik kualitas:

- **Tren tingkat cacat** -- harian/mingguan/bulanan
- **Distribusi cacat berdasarkan jenis** -- cacat mana yang paling umum
- **Distribusi cacat berdasarkan glasir** -- glasir mana yang memiliki tingkat cacat tertinggi
- **Hasil lulus pertama** -- persentase posisi lulus QC pada percobaan pertama
- **Throughput QC** -- posisi yang diinspeksi per hari

---

## 16. Referensi Navigasi

| Halaman | URL | Tujuan |
|---|---|---|
| Dashboard QM | `/quality` | Dashboard utama dengan antrian QC, blokir, kartu masalah |
| Keputusan Grinding | `/manager/grinding` | Alur kerja keputusan grinding |
| Inspeksi Kiln | `/manager/kiln-inspections` | Penilaian kondisi kiln mingguan |
| Laporan | `/reports` | Analitik dan tren kualitas |
| Detail Pesanan | `/orders/:id` | Tampilan detail pesanan tertentu |
| Pengaturan | `/settings` | Pengaturan akun pribadi |

---

## 17. Tips dan Praktik Terbaik

> **Konsistensi adalah kunci**: Gunakan pencahayaan, sudut, dan titik referensi yang sama untuk semua foto kualitas. Ini membuat perbandingan dan analisis tren jauh lebih andal.

> **Dokumentasikan semuanya**: Meskipun Anda meluluskan posisi, tambahkan catatan jika Anda melihat sesuatu yang mendekati batas. Ini membuat jejak audit jika masalah muncul kembali.

> **Akar penyebab, bukan gejala**: Saat membuat kartu masalah, selalu gali mengapa cacat terjadi, bukan hanya apa cacatnya. Teknik "5 Mengapa" sangat efektif.

> **Kolaborasi dengan PM**: Kualitas adalah tanggung jawab bersama. Rapat singkat rutin dengan PM untuk meninjau tren cacat dan membahas perbaikan akan lebih berdampak daripada hanya memblokir posisi.

> **Gunakan koefisien cacat**: Ketika tingkat cacat untuk kombinasi glasir-produk tertentu secara konsisten menyimpang dari matriks, usulkan pembaruan. Koefisien yang akurat menghasilkan perencanaan produksi yang lebih baik.

> **Bukti foto untuk semua kegagalan**: Biasakan memotret setiap pemeriksaan QC yang gagal. Ini melindungi Anda dan tim produksi dengan membuat catatan objektif.

---

*Panduan ini mencakup fitur Moonjar PMS v1.0 untuk peran Quality Manager. Untuk dukungan teknis, hubungi administrator sistem.*
