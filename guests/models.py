"""
Guest models: Guest database & CateringConfig.
"""
from django.db import models
from core.models import Wedding


class Guest(models.Model):
    """Individual guest entry in the wedding guest list."""
    SIDE_CHOICES = [
        ('groom_family', 'Keluarga Pria'),
        ('bride_family', 'Keluarga Wanita'),
        ('groom_friend', 'Teman Pria'),
        ('bride_friend', 'Teman Wanita'),
    ]

    CATEGORY_CHOICES = [
        ('regular', 'Reguler'),
        ('vip', 'VIP'),
        ('vvip', 'VVIP'),
    ]

    RSVP_CHOICES = [
        ('pending', 'Pending'),
        ('attending', 'Hadir'),
        ('declined', 'Berhalangan'),
    ]

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='guests',
    )
    name = models.CharField('Nama Tamu', max_length=200)
    phone = models.CharField('No. HP / WhatsApp', max_length=20, blank=True)
    relation_side = models.CharField(
        'Asal Relasi',
        max_length=15,
        choices=SIDE_CHOICES,
    )
    category = models.CharField(
        'Kategori',
        max_length=10,
        choices=CATEGORY_CHOICES,
        default='regular',
    )
    pax_allocation = models.PositiveIntegerField(
        'Jumlah Pax (Orang)',
        default=2,
        help_text='Estimasi jumlah orang yang hadir dari undangan ini.',
    )
    rsvp_status = models.CharField(
        'Status RSVP',
        max_length=10,
        choices=RSVP_CHOICES,
        default='pending',
    )
    checked_in = models.BooleanField('Sudah Check-in', default=False)
    notes = models.TextField('Catatan', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['relation_side', 'name']
        verbose_name = 'Guest'

    def __str__(self):
        return f"{self.name} ({self.get_relation_side_display()})"


class CateringConfig(models.Model):
    """
    Catering calculation parameters per wedding.
    Drives the Catering Portion & Safety Buffer Simulator.
    """
    wedding = models.OneToOneField(
        Wedding,
        on_delete=models.CASCADE,
        related_name='catering_config',
    )
    attendance_rate = models.DecimalField(
        'Attendance Rate (%)',
        max_digits=5,
        decimal_places=2,
        default=85.00,
    )
    pax_multiplier = models.DecimalField(
        'Pax Multiplier per Undangan',
        max_digits=3,
        decimal_places=1,
        default=2.0,
    )
    vip_buffer_rate = models.DecimalField(
        'VIP Buffer Rate (%)',
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text='Buffer tambahan untuk VIP/keluarga (default 10%).',
    )
    stall_portion_per_pax = models.PositiveIntegerField(
        'Porsi Stall per Pax',
        default=4,
        help_text='Rasio porsi gubukan per pax (default 4 porsi).',
    )
    stall_variety_count = models.PositiveIntegerField(
        'Jumlah Variasi Stall',
        default=5,
    )
    crew_count = models.PositiveIntegerField(
        'Jumlah Crew & Vendor',
        default=20,
        help_text='WO, Fotografer, MUA, Sound, Driver, dll.',
    )
    akad_pax = models.PositiveIntegerField(
        'Pax Sesi Akad / Pemberkatan',
        default=75,
    )

    class Meta:
        verbose_name = 'Catering Configuration'

    def __str__(self):
        return f"Catering Config — {self.wedding}"
