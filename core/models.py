"""
Core models: Wedding Workspace & Membership (Multi-Tenancy).
"""
import string
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone


def generate_invite_code():
    """Generate a unique 8-character alphanumeric invite code."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


class Wedding(models.Model):
    """
    Central workspace that holds all wedding-related data.
    Serves as the tenant isolation boundary (multi-tenancy).
    """
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

    def regenerate_invite_code(self):
        """Generate a new invite code."""
        self.invite_code = generate_invite_code()
        self.save(update_fields=['invite_code'])


class WeddingMembership(models.Model):
    """
    Through model for User <-> Wedding relationship.
    Supports roles: OWNER, CO_OWNER, CREW (restricted access).
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('co_owner', 'Co-Owner'),
        ('crew', 'Crew / Panitia'),
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
        max_length=10,
        choices=ROLE_CHOICES,
        default='owner',
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'wedding')
        verbose_name = 'Wedding Membership'

    def __str__(self):
        return f"{self.user.username} → {self.wedding} ({self.get_role_display()})"

    @property
    def is_owner_or_co_owner(self):
        return self.role in ('owner', 'co_owner')
