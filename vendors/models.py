"""
Vendor models: VendorCandidate for multi-factor scoring.
"""
from django.db import models
from core.models import Wedding


class VendorCandidate(models.Model):
    """Vendor comparison entry with weighted scoring parameters."""
    CATEGORY_CHOICES = [
        ('venue', 'Venue'),
        ('catering', 'Catering'),
        ('mua_attire', 'MUA & Attire'),
        ('decoration', 'Dekorasi'),
        ('documentation', 'Foto / Video'),
        ('entertainment', 'Entertainment / MC'),
        ('other', 'Lainnya'),
    ]

    STATUS_CHOICES = [
        ('shortlist', 'Shortlist'),
        ('booked', 'Booked'),
        ('rejected', 'Rejected'),
    ]

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='vendor_candidates',
    )
    name = models.CharField('Nama Vendor', max_length=200)
    category = models.CharField(
        'Kategori',
        max_length=15,
        choices=CATEGORY_CHOICES,
    )
    contact_pic = models.CharField('PIC / Kontak', max_length=200, blank=True)
    phone = models.CharField('No. HP / WhatsApp', max_length=20, blank=True)
    price_estimate = models.DecimalField(
        'Estimasi Harga (Rp)',
        max_digits=15,
        decimal_places=0,
        default=0,
    )
    offer_link = models.URLField('Link Penawaran', blank=True)
    status = models.CharField(
        'Status Keputusan',
        max_length=10,
        choices=STATUS_CHOICES,
        default='shortlist',
    )
    # Scoring parameters (Scale 1-5)
    score_price = models.PositiveIntegerField(
        'Skor Harga / Value',
        default=3,
        help_text='Skala 1–5. Bobot default: 35%',
    )
    score_quality = models.PositiveIntegerField(
        'Skor Kualitas / Portfolio',
        default=3,
        help_text='Skala 1–5. Bobot default: 30%',
    )
    score_facility = models.PositiveIntegerField(
        'Skor Fasilitas / Bonus',
        default=3,
        help_text='Skala 1–5. Bobot default: 20%',
    )
    score_reputation = models.PositiveIntegerField(
        'Skor Fleksibilitas & Reputasi',
        default=3,
        help_text='Skala 1–5. Bobot default: 15%',
    )
    # Custom weights (default from blueprint)
    weight_price = models.PositiveIntegerField(default=35)
    weight_quality = models.PositiveIntegerField(default=30)
    weight_facility = models.PositiveIntegerField(default=20)
    weight_reputation = models.PositiveIntegerField(default=15)

    notes = models.TextField('Catatan', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Store computed score for ordering
    weighted_total_score_db = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=60.0,
        editable=False,
    )

    class Meta:
        ordering = ['category', '-weighted_total_score_db']
        verbose_name = 'Vendor Candidate'

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    @property
    def weighted_total_score(self):
        """
        Calculate weighted total score (0-100).
        Each score is on 1-5 scale, weights sum to 100.
        Formula: (score/5 * weight) summed across all factors.
        """
        total_weight = (
            self.weight_price + self.weight_quality +
            self.weight_facility + self.weight_reputation
        )
        if total_weight == 0:
            return 0

        raw = (
            (self.score_price / 5 * self.weight_price) +
            (self.score_quality / 5 * self.weight_quality) +
            (self.score_facility / 5 * self.weight_facility) +
            (self.score_reputation / 5 * self.weight_reputation)
        )
        return int(round(raw / total_weight * 100))

    def save(self, *args, **kwargs):
        self.weighted_total_score_db = self.weighted_total_score
        super().save(*args, **kwargs)
