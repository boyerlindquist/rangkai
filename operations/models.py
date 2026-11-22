"""
Operations models: TaskMilestone, RundownEvent, AssetCustodian, FabricEntry.
"""
from datetime import timedelta
from django.conf import settings
from django.db import models
from core.models import Wedding


PHASE_COLOR_CHOICES = [
    ('emerald', 'Emerald'),
    ('blue', 'Biru'),
    ('violet', 'Ungu'),
    ('amber', 'Amber'),
    ('rose', 'Rose'),
    ('teal', 'Teal'),
    ('slate', 'Slate'),
]

DEFAULT_PHASE_RANGES = {
    'd360': (360, 181, 'emerald'),
    'd180': (180, 91, 'blue'),
    'd90': (90, 31, 'violet'),
    'd30': (30, 7, 'amber'),
    'dday': (6, -1, 'rose'),
}


def format_h_day(days_before):
    """Format signed days_before integer into Indonesian H-minus / Hari-H / H-plus label."""
    if days_before is None:
        return '-'
    val = int(days_before)
    if val == 0:
        return 'Hari-H'
    if val > 0:
        return f'H-{val}'
    return f'H+{abs(val)}'


class TimelinePhase(models.Model):
    """Customizable timeline phase per wedding workspace with non-overlapping H-minus day range."""
    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='timeline_phases',
    )
    key = models.CharField('Kode Fase', max_length=40)
    label = models.CharField('Nama Fase', max_length=120)
    start_day_before = models.IntegerField(
        'Mulai (H-)',
        default=360,
        help_text='Hari sebelum Hari-H fase dimulai (contoh: 360 untuk H-360, 0 untuk Hari-H, -1 untuk H+1).',
    )
    end_day_before = models.IntegerField(
        'Selesai (H-)',
        default=181,
        help_text='Hari sebelum Hari-H fase berakhir (harus <= Mulai).',
    )
    color = models.CharField(
        'Warna Penanda',
        max_length=20,
        choices=PHASE_COLOR_CHOICES,
        default='emerald',
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active_override = models.BooleanField('Fase Aktif Manual', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']
        unique_together = [('wedding', 'key')]
        verbose_name = 'Timeline Phase'

    def __str__(self):
        return f"{self.label} ({self.range_display})"

    @property
    def range_display(self):
        return f'{format_h_day(self.start_day_before)} s/d {format_h_day(self.end_day_before)}'

    def get_calendar_dates(self, wedding_date):
        """Return (start_date, end_date) for this phase given a wedding_date, or (None, None)."""
        if not wedding_date:
            return None, None
        start_dt = wedding_date - timedelta(days=self.start_day_before)
        end_dt = wedding_date - timedelta(days=self.end_day_before)
        return start_dt, end_dt

    def contains_days_before(self, days_before):
        """Return True if days_before (wedding_date - target_date) falls within this phase."""
        if days_before is None:
            return False
        return self.end_day_before <= days_before <= self.start_day_before


class TaskMilestone(models.Model):
    """Phased checklist item from D-360 to D-Day (or custom phases)."""
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
        max_length=40,
        default='d360',
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
    due_date = models.DateField('Tenggat Waktu', null=True, blank=True)
    is_custom = models.BooleanField('Custom Task', default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['phase', 'sort_order', 'title']
        verbose_name = 'Task Milestone'

    def get_phase_display(self):
        custom = self.wedding.timeline_phases.filter(key=self.phase).first() if self.wedding_id else None
        if custom:
            return custom.label
        return dict(self.PHASE_CHOICES).get(self.phase, self.phase)

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


class WeddingNote(models.Model):
    """Free-form notes & meeting minutes per wedding workspace with per-note & global privacy."""
    CATEGORY_CHOICES = [
        ('family_meeting', 'Meeting Keluarga'),
        ('vendor_survey', 'Survei Vendor'),
        ('tech_meeting', 'Technical Meeting'),
        ('ideas', 'Ide & Referensi'),
        ('general', 'Umum'),
    ]

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='notes',
    )
    title = models.CharField('Judul Catatan', max_length=200, blank=True, default='')
    content = models.TextField('Isi Catatan', blank=True, default='')
    category = models.CharField(
        'Kategori',
        max_length=24,
        choices=CATEGORY_CHOICES,
        default='general',
    )
    is_pinned = models.BooleanField('Sematkan', default=False)
    is_shared_with_team = models.BooleanField(
        'Tampilkan ke WO & Crew',
        default=False,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_wedding_notes',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_wedding_notes',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-updated_at']
        verbose_name = 'Wedding Note'

    def __str__(self):
        return self.title or 'Catatan Tanpa Judul'
