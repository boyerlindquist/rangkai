"""
Core models: AccountProfile, Wedding Workspace, Membership, Invitations, and Orders.
"""
import string
import secrets
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


def generate_invite_code():
    """Generate a unique 8-character alphanumeric invite code."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


def generate_order_code():
    """Generate a unique order code like RNK-20261119-A1B2."""
    date_part = timezone.now().strftime('%Y%m%d')
    alphabet = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(4))
    return f'RNK-{date_part}-{suffix}'


class AccountProfile(models.Model):
    """
    Platform-level profile defining account type, WO agency name, and project quota.
    """
    ACCOUNT_TYPE_CHOICES = [
        ('couple', 'Wedding Owner / Pengantin'),
        ('wo_manager', 'WO Manager'),
        ('crew', 'Crew / Operasional'),
        ('admin', 'Platform Admin'),
    ]
    PLAN_STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('pending', 'Menunggu Pembayaran'),
        ('expired', 'Kedaluwarsa'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    account_type = models.CharField(
        'Tipe Akun',
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default='couple',
    )
    organization_name = models.CharField(
        'Nama WO / Organisasi',
        max_length=120,
        blank=True,
    )
    project_quota = models.PositiveIntegerField(
        'Kuota Project Aktif',
        default=1,
        help_text='Maksimal project aktif. 0 = tidak terbatas (khusus Admin).',
    )
    plan_status = models.CharField(
        'Status Paket',
        max_length=20,
        choices=PLAN_STATUS_CHOICES,
        default='active',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Account Profile'
        verbose_name_plural = 'Account Profiles'

    def __str__(self):
        return f"{self.user.username} ({self.get_account_type_display()})"

    @property
    def is_platform_admin(self):
        return self.account_type == 'admin' or self.user.is_superuser

    @property
    def is_wo_account(self):
        return self.account_type == 'wo_manager'

    @property
    def active_managed_count(self):
        return Wedding.objects.filter(managed_by=self.user, status='active').count()

    @property
    def remaining_quota(self):
        if self.is_platform_admin or self.project_quota == 0:
            return None
        return max(self.project_quota - self.active_managed_count, 0)

    @property
    def can_create_wo_project(self):
        if self.is_platform_admin:
            return True
        if self.account_type != 'wo_manager':
            return False
        if self.project_quota == 0:
            return True
        return self.active_managed_count < self.project_quota


def get_or_create_profile(user):
    """Safely fetch or auto-create AccountProfile for any authenticated user without extra User queries."""
    profile, created = AccountProfile.objects.get_or_create(
        user=user,
        defaults={
            'account_type': 'admin' if user.is_superuser else 'couple',
            'project_quota': 0 if user.is_superuser else 1,
        },
    )
    # Attach already-loaded user instance to prevent an extra SELECT on auth_user
    profile.user = user
    if user.is_superuser and profile.account_type != 'admin':
        profile.account_type = 'admin'
        profile.project_quota = 0
        profile.save(update_fields=['account_type', 'project_quota'])
    return profile


class Wedding(models.Model):
    """
    Central workspace that holds all wedding-related data.
    Serves as the tenant isolation boundary (multi-tenancy).
    """
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('archived', 'Diarsipkan'),
    ]

    groom_name = models.CharField('Nama Pengantin Pria', max_length=100)
    bride_name = models.CharField('Nama Pengantin Wanita', max_length=100)
    wedding_date = models.DateField('Tanggal Pernikahan', null=True, blank=True)
    total_budget = models.DecimalField(
        'Target Total Budget (Rp)',
        max_digits=15,
        decimal_places=0,
        default=0,
    )
    budget_style = models.CharField(
        'Wedding Style Preset',
        max_length=20,
        choices=[
            ('foodie', 'Foodie Focus'),
            ('aesthetic', 'Aesthetic Focus'),
            ('balanced', 'Standard Balanced'),
        ],
        default='balanced',
    )
    invite_code = models.CharField(
        'Kode Undangan Kolaborasi',
        max_length=8,
        unique=True,
        default=generate_invite_code,
    )
    managed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_weddings',
        verbose_name='Dikelola oleh WO',
    )
    allow_wo_budget_access = models.BooleanField(
        'Izinkan WO Akses Anggaran & Kas',
        default=False,
    )
    allow_wo_notes_access = models.BooleanField(
        'Tampilkan Semua Catatan ke WO & Crew',
        default=False,
    )
    status = models.CharField(
        'Status Workspace',
        max_length=15,
        choices=STATUS_CHOICES,
        default='active',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='WeddingMembership',
        related_name='weddings',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Wedding Workspace'
        verbose_name_plural = 'Wedding Workspaces'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.groom_name} & {self.bride_name}"

    @property
    def days_remaining(self):
        """Calculate days until the wedding."""
        if not self.wedding_date:
            return None
        delta = self.wedding_date - timezone.now().date()
        return max(delta.days, 0)

    @property
    def has_wo_manager(self):
        return bool(self.managed_by_id) or self.memberships.filter(role='wo_manager').exists()

    def regenerate_invite_code(self):
        """Generate a new invite code."""
        self.invite_code = generate_invite_code()
        self.save(update_fields=['invite_code'])


class WeddingMembership(models.Model):
    """
    Through model for User <-> Wedding relationship.
    Supports roles: OWNER, CO_OWNER, WO_MANAGER, CREW.
    Business rule: a user can only hold owner/co_owner in at most 1 wedding.
    """
    ROLE_CHOICES = [
        ('owner', 'Wedding Owner'),
        ('co_owner', 'Co-Owner'),
        ('wo_manager', 'WO Manager'),
        ('crew', 'Crew / Operasional'),
    ]
    TUTORIAL_STATUS_CHOICES = [
        ('not_started', 'Belum Dimulai'),
        ('in_progress', 'Sedang Berjalan'),
        ('completed', 'Selesai'),
        ('dismissed', 'Dilewati'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wedding_memberships',
    )
    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(
        max_length=15,
        choices=ROLE_CHOICES,
        default='owner',
    )
    tutorial_status = models.CharField(
        'Status Tur Praktik',
        max_length=20,
        choices=TUTORIAL_STATUS_CHOICES,
        default='not_started',
    )
    tutorial_step = models.PositiveSmallIntegerField(
        'Langkah Tur Praktik',
        default=0,
    )
    tutorial_state = models.JSONField(
        'State Tur Praktik',
        default=dict,
        blank=True,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'wedding')
        verbose_name = 'Wedding Membership'

    def __str__(self):
        return f"{self.user.username} → {self.wedding} ({self.get_role_display()})"

    def clean(self):
        super().clean()
        if self.role in ('owner', 'co_owner') and self.user_id:
            existing = WeddingMembership.objects.filter(
                user_id=self.user_id,
                role__in=('owner', 'co_owner'),
            )
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(
                    'Akun pengantin (Owner / Co-Owner) hanya dapat memiliki 1 workspace pernikahan.'
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_owner_or_co_owner(self):
        return self.role in ('owner', 'co_owner')

    @property
    def is_wo_manager(self):
        return self.role == 'wo_manager'


class WorkspaceInvitation(models.Model):
    """
    Role-bound invitation code/link for onboarding couple (owner/co_owner),
    WO manager, or operational crew into a specific Wedding workspace.
    """
    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name='invitations',
    )
    code = models.CharField(
        'Kode Undangan',
        max_length=8,
        unique=True,
        default=generate_invite_code,
    )
    role = models.CharField(
        'Peran yang Diberikan',
        max_length=15,
        choices=WeddingMembership.ROLE_CHOICES,
        default='crew',
    )
    max_uses = models.PositiveIntegerField(
        'Batas Pemakaian',
        null=True,
        blank=True,
        help_text='Kosongkan untuk tanpa batas.',
    )
    uses_count = models.PositiveIntegerField('Jumlah Dipakai', default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_invitations',
    )
    is_active = models.BooleanField('Aktif', default=True)
    expires_at = models.DateTimeField('Kedaluwarsa', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Workspace Invitation'
        verbose_name_plural = 'Workspace Invitations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} → {self.wedding} ({self.get_role_display()})"

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False
        return True

    def resolve_role_for_join(self):
        """If role is 'owner' and the wedding already has an owner, assign 'co_owner'."""
        if self.role == 'owner' and self.wedding.memberships.filter(role='owner').exists():
            return 'co_owner'
        return self.role


class Order(models.Model):
    """
    Checkout order record (supports Sumopod Managed Payment QRIS and local dev simulation).
    """
    PLAN_CHOICES = [
        ('wedding_owner', 'Paket Wedding Owner'),
        ('wo_manager', 'Paket WO Manager'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('qris', 'QRIS (Instan)'),
        ('va_bca', 'Virtual Account BCA'),
        ('va_mandiri', 'Virtual Account Mandiri'),
        ('va_bni', 'Virtual Account BNI'),
        ('ewallet', 'E-Wallet (GoPay / OVO / DANA)'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Menunggu Pembayaran'),
        ('paid', 'Lunas'),
        ('expired', 'Kedaluwarsa'),
        ('failed', 'Gagal'),
        ('cancelled', 'Dibatalkan'),
    ]

    order_code = models.CharField(
        'Kode Order',
        max_length=24,
        unique=True,
        default=generate_order_code,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    customer_email = models.EmailField('Email Pembeli', blank=True)
    plan_type = models.CharField('Paket', max_length=20, choices=PLAN_CHOICES)
    amount = models.DecimalField('Total (Rp)', max_digits=12, decimal_places=0)
    gateway_fee = models.DecimalField('Biaya Gateway (Rp)', max_digits=12, decimal_places=0, default=0)
    net_amount = models.DecimalField('Nominal Bersih (Rp)', max_digits=12, decimal_places=0, default=0)
    payment_method = models.CharField(
        'Metode Pembayaran',
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='qris',
    )
    status = models.CharField(
        'Status',
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending',
    )
    gateway_ref = models.CharField('Referensi Gateway', max_length=100, blank=True)
    payment_link_url = models.URLField('URL Pembayaran', max_length=500, blank=True)
    expires_at = models.DateTimeField('Kedaluwarsa', null=True, blank=True)
    metadata = models.JSONField('Data Onboarding', default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_code} ({self.get_plan_type_display()} - {self.get_status_display()})"
