"""
Operations models: TaskMilestone, RundownEvent, AssetCustodian, FabricEntry.
"""
from django.db import models
from core.models import Wedding


class TaskMilestone(models.Model):
    """Phased checklist item from D-360 to D-Day."""
    PHASE_CHOICES = [
        ('d360', 'Fase 1: D-360 s/d D-180'),
        ('d180', 'Fase 2: D-180 s/d D-90'),
        ('d90', 'Fase 3: D-90 s/d D-30'),
        ('d30', 'Fase 4: D-30 s/d D-7'),
        ('dday', 'Fase 5: D-Day & H+1'),
    ]

    ASSIGNEE_CHOICES = [
        ('groom', 'Groom'),
        ('bride', 'Bride'),
        ('both', 'Both'),
        ('family', 'Family / WO'),
    ]

    STATUS_CHOICES = [
        ('todo', 'To-Do'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ]

    CATEGORY_CHOICES = [
        ('finance', 'Finance'),
        ('venue', 'Venue'),
        ('legal', 'Legal & Admin'),
        ('vendor', 'Vendor'),
        ('guest', 'Guest'),
        ('logistic', 'Logistic'),
        ('fb', 'F&B / Catering'),
        ('rundown', 'Rundown'),
        ('asset', 'Asset & Barang'),
        ('post', 'Post-Event'),
        ('other', 'Lainnya'),
    ]

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    phase = models.CharField(
        'Fase',
        max_length=10,
        choices=PHASE_CHOICES,
    )
    category = models.CharField(
        'Kategori',
        max_length=10,
        choices=CATEGORY_CHOICES,
        default='other',
    )
    title = models.CharField('Judul Tugas', max_length=300)
    assignee = models.CharField(
        'Penanggung Jawab',
        max_length=10,
        choices=ASSIGNEE_CHOICES,
        default='both',
    )
    status = models.CharField(
        'Status',
        max_length=12,
        choices=STATUS_CHOICES,
        default='todo',
    )
    linked_tool = models.CharField(
        'Tool Terkait',
        max_length=100,
        blank=True,
        help_text='Nama modul kalkulator yang terhubung.',
    )
    is_critical = models.BooleanField('Tugas Kritis', default=False)
    is_custom = models.BooleanField('Custom Task', default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['phase', 'sort_order', 'title']
        verbose_name = 'Task Milestone'

    def __str__(self):
        return f"[{self.get_phase_display()}] {self.title}"


class RundownEvent(models.Model):
    """D-Day agenda timeline entry."""
    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='rundown_events',
    )
    start_time = models.TimeField('Jam Mulai')
    end_time = models.TimeField('Jam Selesai')
    activity = models.CharField('Nama Agenda', max_length=300)
    location = models.CharField('Lokasi', max_length=200, blank=True)
    pic = models.CharField('PIC Teknis', max_length=200, blank=True)
    notes = models.TextField('Catatan', blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['start_time', 'sort_order']
        verbose_name = 'Rundown Event'

    def __str__(self):
        return f"{self.start_time.strftime('%H:%M')} — {self.activity}"

    @property
    def duration_minutes(self):
        """Calculate agenda duration in minutes."""
        from datetime import datetime, timedelta
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        if end < start:
            end += timedelta(days=1)
        return int((end - start).total_seconds() / 60)


class AssetCustodian(models.Model):
    """D-Day asset tracking for valuable items and logistics."""
    CATEGORY_CHOICES = [
        ('critical', 'Kritis (Cincin, Mahar, Buku Nikah, Angpao)'),
        ('equipment', 'Perlengkapan (Seserahan, Souvenir, Baju Ganti)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Belum Dimuat'),
        ('loaded', 'Loaded at Origin'),
        ('received', 'Received at Venue'),
        ('handed', 'Handed to Bride/Groom'),
        ('packed', 'Post-Event Packed'),
    ]

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='assets',
    )
    name = models.CharField('Nama Barang', max_length=200)
    asset_category = models.CharField(
        'Kategori Aset',
        max_length=15,
        choices=CATEGORY_CHOICES,
        default='equipment',
    )
    pic_name = models.CharField('PIC Pembawa', max_length=200)
    pic_contact = models.CharField('Kontak WhatsApp PIC', max_length=20, blank=True)
    vehicle_info = models.CharField(
        'Kendaraan (Plat No / Driver)',
        max_length=200,
        blank=True,
    )
    status = models.CharField(
        'Status Serah Terima',
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
    )
    notes = models.TextField('Catatan', blank=True)

    class Meta:
        ordering = ['asset_category', 'name']
        verbose_name = 'Asset Custodian'

    def __str__(self):
        return f"{self.name} → {self.pic_name}"


class FabricEntry(models.Model):
    """Fabric yardage calculator entry for uniform planning."""
    GENDER_CHOICES = [
        ('female', 'Wanita'),
        ('male', 'Pria'),
    ]

    GARMENT_CHOICES_FEMALE = [
        ('kebaya_standard', 'Kebaya Standar'),
        ('kebaya_long', 'Kebaya Panjang'),
        ('dress_modern', 'Dress Modern'),
        ('hijab_style', 'Hijab Style'),
    ]

    GARMENT_CHOICES_MALE = [
        ('kemeja_panjang', 'Kemeja Lengan Panjang'),
        ('beskap_adat', 'Beskap Adat'),
        ('jas', 'Jas'),
    ]

    GARMENT_CHOICES = GARMENT_CHOICES_FEMALE + GARMENT_CHOICES_MALE

    SIZE_CHOICES = [
        ('standard', 'Standard (S–L)'),
        ('plus', 'Plus Size (XL–XXL)'),
        ('jumbo', 'Jumbo (>XXL)'),
    ]

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='fabric_entries',
    )
    recipient_name = models.CharField('Nama Penerima', max_length=200)
    gender = models.CharField('Gender', max_length=10, choices=GENDER_CHOICES)
    garment_type = models.CharField(
        'Model Baju',
        max_length=20,
        choices=GARMENT_CHOICES,
    )
    size_category = models.CharField(
        'Kategori Ukuran',
        max_length=10,
        choices=SIZE_CHOICES,
        default='standard',
    )

    class Meta:
        ordering = ['gender', 'recipient_name']
        verbose_name = 'Fabric Entry'
        verbose_name_plural = 'Fabric Entries'

    def __str__(self):
        return f"{self.recipient_name} — {self.get_garment_type_display()}"

    @property
    def yardage(self):
        """
        Calculate fabric requirements in meters based on blueprint rules.
        Returns dict with fabric types and meters needed.
        """
        size_mult = {'standard': 1.0, 'plus': 1.15, 'jumbo': 1.30}
        mult = size_mult.get(self.size_category, 1.0)

        if self.garment_type == 'kebaya_standard':
            return {
                'brokat': round(1.75 * mult, 2),
                'furing': round(2.0 * mult, 2),
                'bawahan': round(2.0 * mult, 2),
            }
        elif self.garment_type in ('kebaya_long', 'hijab_style'):
            return {
                'brokat': round(2.25 * mult, 2),
                'furing': round(2.5 * mult, 2),
                'bawahan': round(2.0 * mult, 2),
            }
        elif self.garment_type == 'dress_modern':
            return {
                'kain_utama': round(2.5 * mult, 2),
                'furing': round(2.5 * mult, 2),
            }
        elif self.garment_type == 'kemeja_panjang':
            return {
                'batik_polos': round(2.25 * mult, 2),
            }
        elif self.garment_type == 'beskap_adat':
            return {
                'kain_utama': round(2.5 * mult, 2),
                'furing': round(1.5 * mult, 2),
            }
        elif self.garment_type == 'jas':
            return {
                'kain_utama': round(3.0 * mult, 2),
                'furing': round(2.0 * mult, 2),
            }
        return {}



class DocumentRequirement(models.Model):
    """Checklist for KUA/Civil registration documents."""
    PARTY_CHOICES = [
        ('groom', 'Pihak Pria'),
        ('bride', 'Pihak Wanita'),
        ('both', 'Bersama'),
    ]
    STATUS_CHOICES = [
        ('todo', 'Belum Diurus'),
        ('process', 'Sedang Diproses'),
        ('done', 'Selesai / Tersedia'),
    ]

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    name = models.CharField('Nama Dokumen', max_length=200)
    party = models.CharField('Pihak', max_length=10, choices=PARTY_CHOICES)
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='todo')
    notes = models.TextField('Catatan / Lokasi Simpan', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['party', 'status', 'name']

    def __str__(self):
        return self.name


class SeserahanItem(models.Model):
    """Checklist for Seserahan/Hantaran items."""
    STATUS_CHOICES = [
        ('todo', 'Belum Beli'),
        ('process', 'Sudah Beli / Dikemas'),
        ('done', 'Selesai / Siap'),
    ]

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='seserahan_items',
    )
    name = models.CharField('Nama Barang', max_length=200)
    category = models.CharField('Kategori', max_length=100, blank=True)
    est_price = models.DecimalField('Estimasi Harga (Rp)', max_digits=15, decimal_places=0, default=0)
    actual_price = models.DecimalField('Harga Aktual (Rp)', max_digits=15, decimal_places=0, default=0)
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='todo')
    pic = models.CharField('PIC Pembawa', max_length=100, blank=True)
    notes = models.TextField('Catatan', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['status', 'category', 'name']

    def __str__(self):
        return self.name
