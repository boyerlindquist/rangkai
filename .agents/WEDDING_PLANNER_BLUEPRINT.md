# 💍 Smart Wedding Engine & Decision Support System (Functional Spec)

> Web application berbasis tools interaktif, kalkulator matematis, dan operational safety engines untuk perencanaan pernikahan presisi, anti-drama logistik, dan optimasi cash flow.

---

## 1. Financial & Cash Flow Engines

### 1.1. Top-Down Budget Allocator & Split-Bill Engine
* **Tujuan:** Menentukan pagu anggaran per kategori secara otomatis dari total target budget, serta membagi beban biaya antar pihak secara transparan.
* **Input Parameters:**
  * Total Target Budget (Rp).
  * Wedding Style / Priority Preset:
    * *Foodie Focus:* Catering 45%, Venue/Decor 20%, Attire/MUA 10%, Doc 10%, Misc 15%.
    * *Aesthetic Focus:* Decor/Venue 35%, Catering 30%, Attire/MUA 15%, Doc 10%, Misc 10%.
    * *Standard Balanced:* Catering 38%, Venue & Decor 22%, Attire & MUA 12%, Doc 10%, Entertainment/MC 5%, Admin/Seserahan/Ring 8%, Buffer/Contingency 5%.
  * Contribution Shares (% atau nominal fixed):
    * Groom Contribution
    * Bride Contribution
    * Groom's Family Contribution
    * Bride's Family Contribution
* **Output & Visuals:**
  * Pagu alokasi maksimal per kategori (dalam Rupiah).
  * Real-time Variance Tracker (Actual Deal vs Pagu Alokasi).
  * Split-Bill Breakdown Matrix: Menampilkan siapa mendanai kategori/vendor apa, progres setoran tabungan bersama, dan status balance dana.

### 1.2. Liquidity & Cash-Out Forecaster
* **Tujuan:** Memetakan jadwal pengeluaran kas bulanan agar tidak terjadi krisis likuiditas akibat jadwal pelunasan vendor yang menumpuk.
* **Input Parameters:**
  * Tanggal Event (D-Day).
  * Tanggal & Nominal DP, Termin 2, dan Pelunasan per vendor.
* **Engine Logic:**
  * Mengagregasi total kas keluar per minggu/bulan dari D-180 hingga D-Day.
  * Threshold Warning: Indikator merah jika proyeksi pengeluaran pada bulan tertentu melebihi kapasitas *cash reserve* bulanan.
* **Output:**
  * Interactive Bar Chart: Estimasi cash-out per bulan.
  * Payment Due Date Calendar dengan status: `Upcoming`, `Due This Week`, `Overdue`, `Settled`.

---

## 2. Guest List, Seating & Catering Math Engine

### 2.1. Catering Portion & Safety Buffer Simulator
* **Tujuan:** Menghitung estimasi kebutuhan porsi makanan utama (*buffet*) dan gubukan (*stall*) secara akurat untuk menghindari kekurangan makanan maupun *food waste*.
* **Formula & Standar Industri:**
  * $\text{Undangan Fisik/Digital Total} = N$
  * $\text{Estimasi Tamu Dewasa} = N \times 2 \times \text{Attendance Rate (default 85\%)}$
  * $\text{Buffer Pax (Keluarga & VIP)} = \text{Tamu Dewasa} \times 1.10$
* **Output Calculations:**
  * **Buffet Utama:** Dihitung $100\%$ dari Total Buffer Pax.
  * **Stall / Gubukan:** Dihitung dengan rasio $1 : 4$ atau $1 : 5$ porsi per pax ($\text{Total Pax} \times 4$ porsi stall, dibagi ke $4-6$ variasi menu).
  * **Panitia & Vendor Crew Meals:** Jumlah crew (WO, Fotografer, MUA, Sound, Driver) $\times 2$ sesi makan (Box terpisah, tidak memotong jatah buffet tamu).
  * **Akad / Holy Matrimony Snacks:** Jumlah tamu sesi pagi/akad (biasanya 50–100 pax) dengan menu coffee break / lontong cap gomeh / soto.

### 2.2. Family Quota Tug-of-War Allocator
* **Tujuan:** Menjaga alokasi undangan tetap adil dan terkontrol antara 4 pihak berkepentingan.
* **Input Parameters:**
  * Kapasitas Maksimal Venue (Pax) atau Batas Kuota Undangan ($N$).
* **Interactive Tool:**
  * 4-Way Connected Slider:
    1. Keluarga Pengantin Pria ($A\%$)
    2. Keluarga Pengantin Wanita ($B\%$)
    3. Teman / Relasi Pengantin Pria ($C\%$)
    4. Teman / Relasi Pengantin Wanita ($D\%$)
  * *Constraint Rule:* Total $A + B + C + D = 100\%$ ($N$ undangan). Jika satu slider digeser naik, 3 slider lainnya menyesuaikan secara proporsional.
  * Dynamic Alert jika penambahan tamu melampaui kapasitas gedung atau memicu kenaikan biaya katering per pax.

---

## 3. Decision Support & Comparison Tools

### 3.1. Multi-Factor Vendor Scoring Matrix
* **Tujuan:** Mengeliminasi bias emosional dalam memilih vendor melalui pembobotan kuantitatif.
* **Kategori Komparasi:** Venue, Catering, MUA/Attire, Dekorasi, Foto/Video.
* **Parameter Penilaian (Skala 1–5):**
  * Harga / Value for Money (Bobot default: 35%)
  * Kualitas Portofolio / Rasa Katering (Bobot default: 30%)
  * Kelengkapan Fasilitas / Bonus Item (Bobot default: 20%)
  * Fleksibilitas & Reputasi PIC (Bobot default: 15%)
* **Output:**
  * *Weighted Total Score* (0–100) per kandidat vendor.
  * Side-by-side Feature Comparison Table.
  * Rekomendasi "Best Value" vs "Lowest Cost".

### 3.2. Uniform & Fabric Yardage Calculator
* **Tujuan:** Menghitung total meter kain seragam keluarga, bridesmaid, dan bestman agar pas saat belanja ke pasar/toko tekstil.
* **Input Matrix:**
  * Daftar Penerima Seragam.
  * Kategori Gender & Model:
    * Wanita: Kebaya Standar / Kebaya Panjang / Dress Modern / Hijab Style.
    * Pria: Kemeja Panjang / Beskap Adat / Jas.
  * Size Postur: Standard (S–L), Plus Size (XL–XXL), Jumbo (>XXL).
* **Yardage Matrix Rules:**
  * Kebaya Standar: 1.75m brokat + 2.0m furing + 2.0m bawahan/batik.
  * Kebaya Panjang / Hijab: 2.25m brokat + 2.5m furing + 2.0m bawahan.
  * Kemeja Pria Lengan Panjang: 2.25m batik/polos.
* **Output:**
  * Total akumulasi panjang kain Brokat/Tulle, Kain Furing (Satin/Silk), dan Kain Batik (Meter).
  * Estimasi total biaya belanja kain berdasarkan harga rata-rata per meter.

---

## 4. Timeline, Safety & Operational Engines

### 4.1. Rundown Sanity & Buffer Conflict Engine
* **Tujuan:** Mencegah keterlambatan acara dengan memvalidasi kelayakan durasi setiap agenda D-Day.
* **Input & Builder:**
  * Drag-and-drop agenda waktu (Mulai, Selesai, Aktivitas, PIC, Lokasi).
* **Automated Rule Checks:**
  * *MUA Duration Check:* Alert jika waktu MUA Pengantin Wanita $< 120$ menit atau MUA Ibu $< 60$ menit.
  * *Transition Gap Check:* Alert jika jeda waktu antara sesi Akad/Pemberkatan ke Sesi Resepsi $< 60$ menit (resiko tamu sudah datang saat pengantin belum siap retouch).
  * *Photo Session Congestion:* Warning jika durasi foto bersama keluarga inti & VIP dialokasikan $< 2$ menit per grup.

### 4.2. Day-H Asset & Luggage Custodian Hub
* **Tujuan:** Memastikan barang-barang berharga dan logistik fisik tidak tertinggal atau tercecer saat perpindahan lokasi (Rumah $\rightarrow$ Hotel $\rightarrow$ Venue).
* **Asset Tracking Schema:**
  * **Kategori Kritis:** Cincin Nikah, Mahar/Mas Kawin, Buku Nikah/Akta, Kotak Angpao Kosong + Gembok & Kunci.
  * **Kategori Perlengkapan:** Kotak Seserahan, Souvenir Tamu, Baju Ganti/Jas Sesi 2, Sepatu Cadangan, Emergency Kit (Obat/Jarum/Peniti).
* **Parameter Assignment:**
  * Nama Barang & Foto Fisik.
  * Assigned Vehicle (Mobil Plat No / Driver).
  * Designated PIC (Nama & Kontak WhatsApp).
  * Status Checklist: `Loaded at Origin`, `Received at Venue`, `Handed to Bride/Groom`, `Post-Event Packed`.

### 4.3. Souvenir Batch & Safety Stock Calculator
* **Tujuan:** Menentukan jumlah produksi souvenir berdasarkan segmentasi tamu.
* **Formula:**
  * Reguler Guest: $1 \text{ Souvenir per Undangan fisik/digital}$.
  * VIP / VVIP Guest: Ditambahkan kuota souvenir premium khusus.
  * Breakage & Loss Safety Stock: Auto-add $7.5\%$ dari total produksi.
* **Output:**
  * Total unit pesanan vendor souvenir.
  * Rekomendasi pembagian alokasi per meja penerima tamu (Meja Sisi Pria vs Meja Sisi Wanita).

## 5. Dynamic Master Milestone & Interactive Checklist Engine

### 5.1. Timeline-Phased Interactive Checklist (D-360 to D-Day)
* **Tujuan:** Menyediakan panduan tugas operasional yang terstruktur berdasarkan fase waktu, dilengkapi auto-filter penanggung jawab dan dependency link.
* **Fitur & Interaktivitas Checkbox:**
  * **Phase Accordion:** Checklist terbagi rapi per fase:
    * `Fase 1: D-360 s/d D-180` (Konsep, Budgeting, Booking Venue/Katering/MUA).
    * `Fase 2: D-180 s/d D-90` (Fitting Baju, Prewedding, Desain Undangan, Administrasi KUA).
    * `Fase 3: D-90 s/d D-30` (Kirim Undangan, Technical Meeting Vendor, Beli Seserahan/Kain).
    * `Fase 4: D-30 s/d D-7` (Pelunasan Vendor, Final RSVP, Packing Logistik, Gladi Bersih).
    * `Fase 5: D-Day & H+1` (Operasional Acara & Serah Terima Pengembalian Sewa).
  * **Quick Filter Toggle:** Filter tugas berdasarkan *Assignee*: `[All]` `[Groom]` `[Bride]` `[Both]` `[Family/WO]`.
  * **Status Lifecycle:** `To-Do` $\rightarrow$ `In Progress` $\rightarrow$ `Done` (dengan visual progress bar real-time per fase).
  * **Engine Linking:** Item checklist tertentu memiliki tombol shortcut langsung ke kalkulator terkait (misal: checklist *"Tentukan Porsi Katering"* langsung membuka modul *Catering Math Engine*).

### 5.2. Pre-Populated Master Task Database (Default Data)

| Fase | Kategori | Item Checklist | Default PIC | Tool Terkait |
|---|---|---|---|---|
| **D-360** | Finance | Tentukan target total budget & skema split-bill | Both | Top-Down Allocator |
| **D-360** | Venue | Survey & booking venue (Akad & Resepsi) | Both | Vendor Scoring |
| **D-180** | Legal | Pengurusan berkas N1-N4 di Kelurahan & Numpang Nikah | Groom / Bride | - |
| **D-180** | Vendor | Lock DP Katering, MUA, dan Dokumentasi | Both | Cash Flow Forecaster |
| **D-90** | Guest | Finalisasi database tamu & alokasi kuota keluarga | Both | Quota Tug-of-War |
| **D-60** | Logistic | Beli kain seragam keluarga & bridesmaid | Bride | Yardage Calculator |
| **D-30** | F&B | Finalisasi menu test food & fixasi rasio buffet/stall | Both | Catering Simulator |
| **D-14** | Rundown | Final Technical Meeting (TM) & validasi rundown WO | Both | Rundown Sanity |
| **D-7** | Finance | Pelunasan seluruh vendor (H-7 to H-3) | Both | Cash-Out Calendar |
| **D-1** | Asset | Packing & serah terima barang berharga ke PIC | Both | Asset Custodian |
| **H+1** | Post-Event | Pengembalian kotak seserahan sewa & busana adat | Family / WO | - |

### 5.3. Custom Task & Dependency Logic
* User dapat menambah custom checklist per sub-kategori.
* **Auto-Alert Notification:** Notifikasi jika ada checklist bertipe *Critical* yang belum dicentang mendekati batas waktu fase.