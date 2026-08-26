# 🏛️ Wedding Planner Engine: System Architecture & Data Design

> Dokumen perencanaan arsitektur sistem, infrastruktur production (2 vCPU / 2 GB RAM), mekanisme multi-tenancy, relasi data model, dan pemetaan rute untuk platform SaaS Wedding Planner.

---

## 1. Strategi Infrastruktur & Ekosistem

### 1.1. Prinsip Desain: High-Headroom Lean Monolith
* **Kapasitas Server (2 vCPU / 2 GB RAM):** Memberikan throughput konkurensi yang stabil tanpa risiko bottleneck CPU atau crash memory.
* **Worker Optimization:** Menjalankan 4–5 workers dengan multi-threading (Gunicorn) untuk menangani request simultan dari pasangan dan tamu RSVP secara bersamaan.
* **Offloaded Database (Serverless Cloud DB):** Database relational tetap ditaruh di cloud serverless (Neon.tech / Supabase). RAM 2GB di VPS dialokasikan murni untuk web server, application runtime, caching, dan buffer OS.
* **No Node.js Runtime in Server:** Rendering antarmuka menggunakan server-side template standar. Interaktivitas dinamis mengandalkan micro-script berbasis CDN yang dieksekusi langsung di browser pengguna.

### 1.2. Resource Allocation Budget
* **OS & System Daemons:** ~150 – 200 MB RAM
* **Nginx Web Server & Static Cache:** ~50 – 80 MB RAM
* **Django Runtime + 4–5 Workers:** ~400 – 600 MB RAM
* **Free Buffer / Headroom:** ~1.1 – 1.3 GB RAM (Aman untuk traffic spike atau background scheduler)

### 1.3. Komponen Infrastruktur
* **Traffic & Security Layer:** Cloudflare mengelola DNS, proteksi DDoS, sertifikat SSL otomatis, dan caching aset visual.
* **Web Server Layer:** Reverse proxy Nginx meneruskan request port 80/443 ke WSGI runtime.
* **Application Core:** Django monolith menangani routing, session authentication, permission control, dan kalkulasi orkestrasi data.
* **Data Storage Layer:** Managed Serverless PostgreSQL (Neon.tech / Supabase) via connection pooling (PgBouncer) untuk menangani transaksi data secara aman dan terisolasi.

---

## 2. Mekanisme Multi-Tenancy & Autentikasi

Platform menggunakan pola **Shared Database, Shared Schema** dengan isolasi data berbasis *Tenant Workspace*.

### 2.1. Model Kepemilikan (Couple Workspace)
* Setiap baris data (Budget, Tamu, Vendor, Rundown) wajib terikat pada satu entitas `Wedding Workspace`.
* Satu `Wedding Workspace` dapat diakses bersamaan oleh dua akun utama: **Groom (Pria)** dan **Bride (Wanita)**.

### 2.2. Alur Registrasi & Kolaborasi Pasangan
1. **Pendaftaran Akun Pertama:** Pengguna mendaftar dan sistem membuat `Wedding Workspace` baru serta menerbitkan *Invite Code* acak yang unik.
2. **Koneksi Pasangan:** Pengguna membagikan *Invite Code* kepada pasangannya. Saat pasangan login dan memasukkan kode tersebut, sistem menautkan akunnya ke `Wedding Workspace` yang sama dengan hak akses penuh (*Co-Owner*).
3. **Akses Tamu / Panitia (Restricted Mode):** Workspace mendukung pembuatan token akses sementara untuk panitia/WO yang hanya bisa melihat data rundown dan logistik barang tanpa izin melihat data finansial.

---

## 3. Blueprint Relasi & Entitas Data (ERD Plan)

### 3.1. Domain: Autentikasi & Tenancy
* **Tabel `User`:** Menyimpan profil pengguna, email unik, status verifikasi, dan tier langganan (*Free / Premium SaaS*).
* **Tabel `Wedding`:** Workspace utama yang menyimpan tanggal pernikahan, nama pasangan, target total budget, kode undangan kolaborasi, dan relasi *many-to-many* ke tabel `User`.

### 3.2. Domain: Finansial & Cash Flow
* **Tabel `BudgetCategory`:** Master kategori pengeluaran (Catering, Venue, Attire & MUA, Dokumentasi, Musik & MC, Legalitas, Logistik, Dana Darurat).
* **Tabel `BudgetItem`:** Item rincian pengeluaran yang terikat pada Workspace dan Kategori. Menyimpan alokasi target, nominal kesepakatan (*actual cost*), nominal yang sudah dibayar, tanggal jatuh tempo pembayaran, dan penanggung jawab pembayaran (Pria / Wanita / Tabungan Bersama / Keluarga).

### 3.3. Domain: Tamu, RSVP & Katering
* **Tabel `Guest`:** Database tamu undangan yang terikat pada Workspace. Menyimpan nama tamu, asal relasi (Keluarga Pria, Keluarga Wanita, Teman Pria, Teman Wanita), kategori tamu (Reguler, VIP, VVIP), jumlah kuota kehadiran (*pax allocation*), status konfirmasi kehadiran (Pending, Hadir, Berhalangan), dan status *check-in* di lokasi.
* **Tabel `CateringConfig`:** Konfigurasi parameter kalkulator katering per pernikahan (rasio porsi buffet, multiplier porsi gubukan, dan jatah konsumsi panitia/vendor).

### 3.4. Domain: Keputusan Vendor
* **Tabel `VendorCandidate`:** Menyimpan daftar komparasi vendor per kategori. Menyimpan nama vendor, kontak PIC, tautan penawaran harga, estimasi biaya total, status keputusan (*Shortlist, Booked, Rejected*), serta nilai parameter bobot evaluasi (Harga, Rasa/Portofolio, Fasilitas, Reputasi).

### 3.5. Domain: Operasional & Logistik Hari-H
* **Tabel `TaskMilestone`:** Daftar tugas persiapan yang terikat pada fase waktu (D-360, D-180, D-90, D-30, D-Day). Menyimpan nama tugas, PIC penanggung jawab, status penyelesaian (*To-Do, In Progress, Done*), dan tautan menuju modul kalkulator terkait.
* **Tabel `RundownEvent`:** Jadwal susunan acara per menit pada Hari-H. Menyimpan jam mulai, jam selesai, nama agenda, lokasi, PIC teknis, dan catatan penting.
* **Tabel `AssetCustodian`:** Pelacak barang logistik berharga (Mahar, Cincin, Kotak Angpao, Souvenir). Menyimpan nama aset, identitas PIC pembawa, kontak darurat, penempatan kendaraan, dan status serah terima fisik di lokasi.

---

## 4. Pola Interaktivitas UI & Pertukaran Data

Untuk menjaga performa tinggi tanpa menggunakan framework frontend berat:

1. **Client-Side Reactive Logic (Alpine.js):** Modul seperti *Family Quota Slider*, *Fabric Yardage Calculator*, dan *Catering Ratio Simulator* dikalkulasi langsung di memori browser pengguna untuk respon instan (0 ms latency) tanpa perlu memanggil server.
2. **Server-Side Asynchronous Persistence (HTMX):** Interaksi seperti mencentang checklist, mengubah status bayar vendor, dan menyimpan data tamu dikirim via request latar belakang. Server Django memproses perubahan ke database dan mengembalikan potongan HTML baru untuk di-swap ke layar tanpa me-reload seluruh halaman.

---

## 5. Information Architecture & Route Mapping

Aplikasi menggunakan pola **Modular Multi-Page Hub** untuk menjaga fokus pengguna, mencegah layout mobile terlalu panjang (*infinite scroll*), dan memetakan fitur secara bersih ke dalam sub-aplikasi Django.

* **Route `/` (Overview Hub)**
  * Django App: `core`
  * Fitur: 4 Metric KPI Cards (D-Day Countdown, Sisa Budget, RSVP Hadir, Task Progress), Snapshot Tugas Fase Aktif, Urgent Due Date Alerts, Quick Action Shortcuts.
* **Route `/budgets/` (Finance & Cash Flow)**
  * Django App: `finances`
  * Fitur: Top-Down Budget Allocator (Pagu vs Actual Deal), Couple Split-Bill Breakdown (Siapa mendanai apa), Liquidity & Cash-Out Forecaster (Grafik kas keluar bulanan), Tabel Master Pengeluaran, DP, & Status Pembayaran.
* **Route `/guests/` (Guest List & Catering Math)**
  * Django App: `guests`
  * Fitur: Real-time Catering Math Simulator (Buffet & Stall Calculator), Family Quota Tug-of-War (Slider 4-arah terkoneksi), Tabel Database Tamu (Filter Sisi Pria/Wanita, VIP, Pax, Status RSVP).
* **Route `/vendors/` (Vendor Comparator & Scoring)**
  * Django App: `vendors`
  * Fitur: Multi-Factor Vendor Scoring Matrix (Komparasi berbobot 1-on-1), Directory Kontak PIC, Link Penawaran, & Kontrak Kerja Sama.
* **Route `/checklist/` (Phased Tasks & Milestones)**
  * Django App: `operations`
  * Fitur: Phased Accordion Checklist (D-360 sampai D-Day), Filter Penanggung Jawab (Groom / Bride / Both / Family), Progress Bar Real-time per Fase.
* **Route `/operations/` (D-Day Logistics & Safety)**
  * Django App: `operations`
  * Fitur: Fabric Yardage Calculator (Kalkulator meteran kain seragam), Rundown Sanity & Buffer Conflict Engine, Asset & Luggage Custodian Hub (Mapping mobil & PIC barang berharga), Restricted View Link untuk Crew WO / Panitia.

---

## 6. Roadmap Fase Pengembangan (Planning Milestones)

* **Fase 1: Workspace & Tenancy Foundation**
  * Setup master workspace, sistem registrasi email/password, dan alur pairing pasangan via `invite_code`.
* **Fase 2: Financial & Decision Engines**
  * Pembangunan modul Top-Down Budget Allocator, Vendor Scoring Matrix, dan Cash-Out Forecaster.
* **Fase 3: Guest Management & Catering Math**
  * Pembangunan modul alokasi kuota 4-arah, database tamu, dan kalkulator kebutuhan porsi makanan.
* **Fase 4: Operations & Safety Engines**
  * Pembangunan Interactive Phased Checklist, Timeline Rundown Validator, dan Asset Custodian Hub.
* **Fase 5: Production Deployment & SaaS Monetization Layer**
  * Konfigurasi Nginx + Gunicorn di VPS (2 vCPU / 2 GB RAM), integrasi Cloudflare SSL, pembatasan fitur untuk akun Free vs Premium, dan integrasi webhook payment gateway.