# 🚀 Panduan Deployment Rangkai ke VPS (Server: pain-and-agony)

Dokumentasi arsitektur dan langkah eksekusi deployment aplikasi **Rangkai (Smart Wedding Engine)** ke server VPS Jakarta (`43.173.40.113`).

---

## 🖥️ Ringkasan Server VPS
* **Server Name:** `pain-and-agony` (Region: Jakarta)
* **IP Public:** `43.173.40.113`
* **OS:** Ubuntu 24.04 LTS
* **Spesifikasi:** 2 vCPU, 4 GB RAM, 60 GB SSD
* **User SSH:** `ubuntu` (Port 22)
* **Stack:** Nginx (Reverse Proxy) + Gunicorn (5 Workers WSGI) + Systemd Daemon + Python 3.12 (venv)

---

## ⚡ Langkah Cepat Deployment (Step-by-Step)

### 1. Login ke VPS
Buka Terminal / PowerShell di laptopmu:
```bash
ssh ubuntu@43.173.40.113
```
*(Masukkan password VPS saat diminta: `Imammam128++`)*

---

### 2. Update Sistem & Install Paket yang Dibutuhkan
Jalankan perintah berikut di terminal VPS:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev git nginx curl ufw
```

Aktifkan firewall dasar:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

---

### 3. Buat Folder & Siapkan Kode Aplikasi
Buat direktori kerja di `/var/www/rangkai` dan beri izin ke user `ubuntu`:
```bash
sudo mkdir -p /var/www/rangkai
sudo chown -R ubuntu:ubuntu /var/www/rangkai
cd /var/www/rangkai
```

Clone repository kamu (atau clone via git):
```bash
git clone <URL_GIT_REPO_ANDA> .
```

Buat dan aktifkan Virtual Environment Python:
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Konfigurasi Environment Variables (`.env`)
Buat file konfigurasi `.env`:
```bash
nano /var/www/rangkai/.env
```

Tempel konfigurasi production berikut:
```ini
DJANGO_SECRET_KEY=b9w8#x$q2e*m91z+k4p!y6v7n^d3c5f@a8h2j0l-t4r6u8i1o3
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=43.173.40.113,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://43.173.40.113,https://43.173.40.113
```
*(Simpan: Tekan `Ctrl + O`, lalu `Enter`, lalu `Ctrl + X`)*.

Jalankan migrasi database dan pengumpulan file statis:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

Buat akun Superuser admin Rangkai pertama:
```bash
python manage.py createsuperuser
```

Pastikan izin folder database dan staticfiles bisa ditulis oleh web server:
```bash
sudo chown -R ubuntu:www-data /var/www/rangkai
sudo chmod -R 775 /var/www/rangkai
sudo chmod 664 /var/www/rangkai/db.sqlite3
```

---

### 5. Setup Gunicorn & Systemd Daemon
Karena server memiliki **2 vCPU dan 4 GB RAM**, kita mengonfigurasi **5 Gunicorn workers** agar mampu melayani puluhan tamu & keluarga secara bersamaan tanpa lag:

```bash
sudo nano /etc/systemd/system/rangkai.service
```

Tempel konfigurasi ini:
```ini
[Unit]
Description=Rangkai Wedding Planner Gunicorn Daemon
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/var/www/rangkai
ExecStart=/var/www/rangkai/venv/bin/gunicorn \
          --workers 5 \
          --bind unix:/var/www/rangkai/rangkai.sock \
          --access-logfile - \
          --error-logfile - \
          config.wsgi:application

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Nyalakan dan aktifkan service:
```bash
sudo systemctl daemon-reload
sudo systemctl start rangkai
sudo systemctl enable rangkai
sudo systemctl status rangkai
```
*(Pastikan tertulis `Active: active (running)` berwarna hijau. Untuk melihat real-time log aplikasi: `sudo journalctl -u rangkai -f`)*.

---

### 6. Setup Nginx Reverse Proxy
Buat virtual host Nginx:
```bash
sudo nano /etc/nginx/sites-available/rangkai
```

Tempel konfigurasi ini:
```nginx
server {
    listen 80;
    server_name 43.173.40.113;

    client_max_body_size 30M;

    # File Statis (CSS, JS, Logo SVG, Fonts)
    location /static/ {
        alias /var/www/rangkai/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    # File Media (Upload Bukti Transfer / Dokumen)
    location /media/ {
        alias /var/www/rangkai/media/;
        expires 30d;
    }

    # Proxy ke Gunicorn Socket
    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/rangkai/rangkai.sock;
    }
}
```

Aktifkan konfigurasi dan restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/rangkai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

### 7. Uji Coba Web Live!
Buka browser di laptop atau HP kamu:
👉 **`http://43.173.40.113/`** atau **`http://43.173.40.113/login/`**

Web Rangkai sudah langsung live dan dapat diakses dari internet!

---

### 8. (Opsional) Pasang Domain & HTTPS Gratis
Jika nanti kamu sudah membeli domain (misal `rangkai.id`):
1. Arahkan **A Record** `@` dan `www` di DNS domain ke IP `43.173.40.113`.
2. Tambahkan domain ke `/etc/nginx/sites-available/rangkai` pada baris `server_name`.
3. Tambahkan domain ke `.env` pada `DJANGO_ALLOWED_HOSTS` dan `DJANGO_CSRF_TRUSTED_ORIGINS`.
4. Jalankan Certbot untuk SSL gratis:
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d rangkai.id -d www.rangkai.id
   ```
   Web otomatis berubah menjadi **`https://rangkai.id`** dengan gembok hijau aman!
