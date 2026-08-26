"""
Finance models: BudgetCategory, BudgetItem, ContributionShare.
"""
from django.db import models
from core.models import Wedding


class BudgetCategory(models.Model):
    """Master budget category with default allocation percentage."""
    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='budget_categories',
    )
    name = models.CharField('Nama Kategori', max_length=100)
    icon = models.CharField('Icon (emoji)', max_length=10, default='💰')
    allocation_percentage = models.DecimalField(
        'Alokasi Default (%)',
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Budget Category'
        verbose_name_plural = 'Budget Categories'

    def __str__(self):
        return f"{self.icon} {self.name}"

    @property
    def allocated_amount(self):
        """Calculate allocated amount from wedding total budget."""
        return (self.wedding.total_budget * self.allocation_percentage) / 100

    @property
    def total_actual(self):
        return self.items.aggregate(total=models.Sum('actual_cost'))['total'] or 0

    @property
    def total_paid(self):
        return self.items.aggregate(total=models.Sum('paid_amount'))['total'] or 0

    @property
    def variance(self):
        """Difference between allocated and actual. Positive = under budget."""
        return self.allocated_amount - self.total_actual


class BudgetItem(models.Model):
    """Individual expense item within a budget category."""
    PAYER_CHOICES = [
        ('groom', 'Pengantin Pria'),
        ('bride', 'Pengantin Wanita'),
        ('joint', 'Tabungan Bersama'),
        ('groom_family', 'Keluarga Pria'),
        ('bride_family', 'Keluarga Wanita'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Belum Dibayar'),
        ('dp_paid', 'DP Dibayar'),
        ('partial', 'Sebagian Dibayar'),
        ('settled', 'Lunas'),
    ]

    category = models.ForeignKey(
        BudgetCategory,
        on_delete=models.CASCADE,
        related_name='items',
    )
    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='budget_items',
    )
    name = models.CharField('Nama Item', max_length=200)
    vendor_name = models.CharField('Nama Vendor', max_length=200, blank=True)
    allocated_amount = models.DecimalField(
        'Alokasi Target (Rp)',
        max_digits=15,
        decimal_places=0,
        default=0,
    )
    actual_cost = models.DecimalField(
        'Harga Deal / Actual (Rp)',
        max_digits=15,
        decimal_places=0,
        default=0,
    )
    paid_amount = models.DecimalField(
        'Sudah Dibayar (Rp)',
        max_digits=15,
        decimal_places=0,
        default=0,
    )
    payer = models.CharField(
        'Penanggung Jawab Pembayaran',
        max_length=15,
        choices=PAYER_CHOICES,
        default='joint',
    )
    payment_status = models.CharField(
        'Status Pembayaran',
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid',
    )
    due_date = models.DateField('Tanggal Jatuh Tempo', null=True, blank=True)
    notes = models.TextField('Catatan', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'name']
        verbose_name = 'Budget Item'

    def __str__(self):
        return self.name

    @property
    def remaining(self):
        return self.actual_cost - self.paid_amount

    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.due_date and self.payment_status != 'settled':
            return self.due_date < timezone.now().date()
        return False


class ContributionShare(models.Model):
    """Split-bill configuration for each contributor."""
    CONTRIBUTOR_CHOICES = [
        ('groom', 'Pengantin Pria'),
        ('bride', 'Pengantin Wanita'),
        ('groom_family', 'Keluarga Pria'),
        ('bride_family', 'Keluarga Wanita'),
    ]

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='contribution_shares',
    )
    contributor = models.CharField(
        'Kontributor',
        max_length=15,
        choices=CONTRIBUTOR_CHOICES,
    )
    percentage = models.DecimalField(
        'Persentase Kontribusi (%)',
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    fixed_amount = models.DecimalField(
        'Nominal Tetap (Rp)',
        max_digits=15,
        decimal_places=0,
        default=0,
        help_text='Jika diisi, akan override persentase.',
    )

    class Meta:
        unique_together = ('wedding', 'contributor')
        verbose_name = 'Contribution Share'

    def __str__(self):
        return f"{self.get_contributor_display()} — {self.percentage}%"



class SavingsGoal(models.Model):
    """Tracker for joint savings goal."""
    wedding = models.OneToOneField(
        Wedding,
        on_delete=models.CASCADE,
        related_name='savings_goal',
    )
    target_amount = models.DecimalField(
        'Target Tabungan (Rp)',
        max_digits=15,
        decimal_places=0,
        default=0,
    )
    monthly_deposit = models.DecimalField(
        'Kesanggupan Tabung Per Bulan (Rp)',
        max_digits=15,
        decimal_places=0,
        default=0,
    )
    
    class Meta:
        verbose_name = 'Savings Goal'

    def __str__(self):
        return f"Goal for {self.wedding}"

    @property
    def total_saved(self):
        return self.deposits.aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def remaining(self):
        return max(0, self.target_amount - self.total_saved)


class SavingsDeposit(models.Model):
    """Individual deposit to the savings goal."""
    goal = models.ForeignKey(
        SavingsGoal,
        on_delete=models.CASCADE,
        related_name='deposits',
    )
    amount = models.DecimalField('Nominal Setoran (Rp)', max_digits=15, decimal_places=0)
    date = models.DateField('Tanggal Setoran')
    depositor = models.CharField('Penyetor (Pria/Wanita/Bersama)', max_length=50)
    notes = models.TextField('Catatan', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Rp {self.amount} on {self.date}"
