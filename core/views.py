"""
Core views: Landing, Checkout (Sumopod QRIS + Dev Simulation), Webhooks, Auth,
WO Portal, Admin Console, Workspace Switcher, Dashboard, Join Workspace,
Settings, and Role-Bound Invitations.
"""
import json
import logging
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.services import sumopod

logger = logging.getLogger(__name__)

from core.models import (
    AccountProfile,
    Wedding,
    WeddingMembership,
    WorkspaceInvitation,
    Order,
    get_or_create_profile,
)
from core.forms import (
    RegisterForm,
    CheckoutForm,
    WOProjectCreateForm,
    LoginForm,
    JoinWorkspaceForm,
    WeddingSettingsForm,
    resolve_invite_code,
)
from core.decorators import (
    workspace_required,
    owner_required,
    couple_only_required,
    wo_portal_required,
    platform_admin_required,
)


PRICING_PLANS = {
    'wedding_owner': {
        'slug': 'wedding_owner',
        'name': 'Paket Wedding Owner',
        'badge': 'Untuk Calon Pengantin',
        'price': 149000,
        'price_display': 'Rp 149.000',
        'period': 'sekali bayar sampai hari-H',
        'quota': 1,
        'account_type': 'couple',
        'summary': '1 workspace pernikahan lengkap untuk pasangan bersama keluarga dan tim operasional.',
        'features': [
            '1 Workspace Pernikahan aktif penuh sampai hari-H',
            'Undang 1 Co-Owner (pasangan) dan Crew Operasional tanpa batas',
            'Tabungan Pribadi terkunci khusus pengantin',
            'Budget & Cash-Flow Sankey, Vendor Scoring, Tamu, Checklist & Rundown',
        ],
    },
    'wo_manager': {
        'slug': 'wo_manager',
        'name': 'Paket WO Manager',
        'badge': 'Untuk Wedding Organizer',
        'price': 499000,
        'price_display': 'Rp 499.000',
        'period': 'per bulan (hingga 10 project aktif)',
        'quota': 10,
        'account_type': 'wo_manager',
        'summary': 'Kelola banyak project pernikahan klien sekaligus dari satu Portal WO dengan privasi klien tetap terjaga.',
        'features': [
            'Hingga 10 Workspace Pernikahan klien aktif bersamaan',
            'Portal WO Dashboard + Workspace Switcher instan di sidebar',
            'Generate link undangan privat Pengantin (data Tabungan klien tetap privat)',
            'Undang dan kelola Crew lapangan lintas project klien',
        ],
    },
}


DEFAULT_BUDGET_CATEGORIES = [
    {'name': 'Catering & F&B', 'icon': '<i data-lucide="utensils"></i>', 'allocation': {'foodie': 45, 'aesthetic': 30, 'balanced': 38}},
    {'name': 'Venue & Gedung', 'icon': '<i data-lucide="building"></i>', 'allocation': {'foodie': 10, 'aesthetic': 20, 'balanced': 12}},
    {'name': 'Dekorasi', 'icon': '<i data-lucide="sparkles"></i>', 'allocation': {'foodie': 10, 'aesthetic': 15, 'balanced': 10}},
    {'name': 'Attire & MUA', 'icon': '<i data-lucide="scissors"></i>', 'allocation': {'foodie': 10, 'aesthetic': 15, 'balanced': 12}},
    {'name': 'Dokumentasi', 'icon': '<i data-lucide="camera"></i>', 'allocation': {'foodie': 10, 'aesthetic': 10, 'balanced': 10}},
    {'name': 'Entertainment & MC', 'icon': '<i data-lucide="mic"></i>', 'allocation': {'foodie': 3, 'aesthetic': 3, 'balanced': 5}},
    {'name': 'Admin & Legalitas', 'icon': '<i data-lucide="file-text"></i>', 'allocation': {'foodie': 5, 'aesthetic': 3, 'balanced': 5}},
    {'name': 'Seserahan & Cincin', 'icon': '<i data-lucide="gem"></i>', 'allocation': {'foodie': 2, 'aesthetic': 2, 'balanced': 3}},
    {'name': 'Buffer / Darurat', 'icon': '<i data-lucide="shield"></i>', 'allocation': {'foodie': 5, 'aesthetic': 2, 'balanced': 5}},
]

DEFAULT_TASKS = [
    # Persiapan Awal
    {'phase': 'd360', 'category': 'other', 'title': 'Pertemuan keluarga (Perkenalan & Silaturahmi)', 'assignee': 'both', 'is_critical': True},
    {'phase': 'd360', 'category': 'rundown', 'title': 'Menentukan tanggal pernikahan', 'assignee': 'both', 'is_critical': True},
    {'phase': 'd360', 'category': 'other', 'title': 'Menentukan tema & konsep pernikahan', 'assignee': 'both'},
    {'phase': 'd360', 'category': 'rundown', 'title': 'Menentukan tanggal lamaran (jika ada)', 'assignee': 'both'},
    {'phase': 'd360', 'category': 'finance', 'title': 'Menentukan target total budget & skema split-bill', 'assignee': 'both', 'linked_tool': 'Top-Down Allocator', 'is_critical': True},
    {'phase': 'd360', 'category': 'guest', 'title': 'Menentukan estimasi jumlah tamu', 'assignee': 'both'},
    
    # Tempat, Dekorasi, Vendor Utama
    {'phase': 'd360', 'category': 'venue', 'title': 'Survey & booking venue (Akad & Resepsi)', 'assignee': 'both', 'linked_tool': 'Vendor Scoring', 'is_critical': True},
    {'phase': 'd360', 'category': 'vendor', 'title': 'Riset & shortlist vendor Catering', 'assignee': 'both', 'linked_tool': 'Vendor Scoring'},
    {'phase': 'd360', 'category': 'vendor', 'title': 'Riset & shortlist vendor Dekorasi', 'assignee': 'both', 'linked_tool': 'Vendor Scoring'},
    {'phase': 'd360', 'category': 'vendor', 'title': 'Riset & shortlist vendor MUA & Busana', 'assignee': 'bride', 'linked_tool': 'Vendor Scoring'},
    {'phase': 'd360', 'category': 'vendor', 'title': 'Riset & shortlist vendor Dokumentasi (Foto/Video)', 'assignee': 'both', 'linked_tool': 'Vendor Scoring'},
    
    # Administrasi Persiapan Pernikahan
    {'phase': 'd180', 'category': 'legal', 'title': 'Siapkan Surat Pengantar dari RT/RW', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Siapkan Fotocopy KTP & KK (CPP dan CPW)', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Siapkan Fotocopy Akta kelahiran & Ijazah (CPP dan CPW)', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Siapkan Pas Foto 3x2 latar biru 5 lembar (CPP dan CPW)', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Pengurusan berkas N1-N4 di Kelurahan & Numpang Nikah', 'assignee': 'both', 'is_critical': True},
    {'phase': 'd180', 'category': 'legal', 'title': 'Siapkan Fotocopy KTP Wali Nikah & 2 Orang Saksi', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Suntik TT / Keterangan Vaksin TT (CPW)', 'assignee': 'bride'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Daftar nikah ke KUA', 'assignee': 'both', 'is_critical': True},
    {'phase': 'd180', 'category': 'legal', 'title': 'Mengikuti bimbingan pra-nikah', 'assignee': 'both'},

    # Mahar, Seserahan & Cincin
    {'phase': 'd180', 'category': 'other', 'title': 'Beli cincin couple / kawin', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'other', 'title': 'Pesan mahar & kotak cincin nikah', 'assignee': 'groom'},
    {'phase': 'd180', 'category': 'other', 'title': 'Beli & hias barang seserahan', 'assignee': 'both'},
    
    # Vendor Lanjutan
    {'phase': 'd180', 'category': 'vendor', 'title': 'Lock DP Katering, MUA, Dekor, dan Dokumentasi', 'assignee': 'both', 'linked_tool': 'Cash Flow Forecaster', 'is_critical': True},
    {'phase': 'd180', 'category': 'vendor', 'title': 'Pesan Baju pengantin akad & resepsi (CPP & CPW)', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'vendor', 'title': 'Fitting baju pengantin & seragam keluarga', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'vendor', 'title': 'Sesi prewedding foto/video', 'assignee': 'both'},
    
    # Undangan, Souvenir, & Tamu
    {'phase': 'd180', 'category': 'logistic', 'title': 'Pesan & cetak buku tamu', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'logistic', 'title': 'Pesan Souvenir pernikahan', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'guest', 'title': 'Finalisasi database tamu & alokasi kuota keluarga', 'assignee': 'both', 'linked_tool': 'Quota Tug-of-War', 'is_critical': True},
    {'phase': 'd90', 'category': 'logistic', 'title': 'Desain & cetak undangan digital/fisik', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'logistic', 'title': 'Kirim undangan fisik & digital', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'logistic', 'title': 'Beli kain seragam keluarga & bridesmaid', 'assignee': 'bride', 'linked_tool': 'Yardage Calculator'},
    
    # Acara & Hiburan
    {'phase': 'd90', 'category': 'vendor', 'title': 'Booking MC, Hiburan (Band/Penyanyi) & Photobooth', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'rundown', 'title': 'Pesan jasa qori / tilawah (jika ada)', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'rundown', 'title': 'Tentukan petugas sambutan dari perwakilan keluarga/tokoh', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'rundown', 'title': 'Persiapan & booking alat Acara Adat (jika ada)', 'assignee': 'family'},

    # Technical Meeting & Persiapan Mendekati Hari H
    {'phase': 'd90', 'category': 'vendor', 'title': 'Technical Meeting tahap 1 dengan semua vendor', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'fb', 'title': 'Finalisasi menu test food & fixasi rasio buffet/stall', 'assignee': 'both', 'linked_tool': 'Catering Simulator', 'is_critical': True},
    {'phase': 'd30', 'category': 'finance', 'title': 'Pelunasan seluruh vendor (H-7 to H-3)', 'assignee': 'both', 'linked_tool': 'Cash-Out Calendar', 'is_critical': True},
    {'phase': 'd30', 'category': 'guest', 'title': 'Final RSVP & konfirmasi kehadiran tamu', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'logistic', 'title': 'Packing logistik souvenir & seserahan', 'assignee': 'family'},
    
    # Panitia & Petugas Hari H
    {'phase': 'd30', 'category': 'rundown', 'title': 'Menyusun susunan panitia keluarga', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'rundown', 'title': 'Menunjuk pengiring pengantin wanita / bridesmaid', 'assignee': 'bride'},
    {'phase': 'd30', 'category': 'rundown', 'title': 'Menunjuk penjaga buku tamu & souvenir', 'assignee': 'family'},
    {'phase': 'd30', 'category': 'finance', 'title': 'Menunjuk penjaga & pemegang kunci kotak amplop', 'assignee': 'family', 'is_critical': True},
    {'phase': 'd30', 'category': 'fb', 'title': 'Menunjuk PIC penjaga makanan/prasmanan keluarga', 'assignee': 'family'},
    {'phase': 'd30', 'category': 'other', 'title': 'Koordinasi Tim Kebersihan & Keamanan (Parkir, dll)', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'logistic', 'title': 'Booking / atur Transportasi Calon Pengantin & Keluarga', 'assignee': 'both'},
    
    # Finalisasi
    {'phase': 'd30', 'category': 'rundown', 'title': 'Briefing / rapat panitia keluarga', 'assignee': 'both', 'is_critical': True},
    {'phase': 'd30', 'category': 'rundown', 'title': 'Final Technical Meeting (TM) & validasi rundown WO', 'assignee': 'both', 'linked_tool': 'Rundown Sanity', 'is_critical': True},
    {'phase': 'd30', 'category': 'logistic', 'title': 'Gladi bersih / rehearsal di venue', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'other', 'title': 'Booking & perawatan kuku (Nail art)', 'assignee': 'bride'},
    {'phase': 'd30', 'category': 'legal', 'title': 'Ajukan izin cuti menikah di tempat kerja', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'other', 'title': 'Jaga kesehatan & konsumsi vitamin', 'assignee': 'both'},

    # Hari H & Pasca Acara
    {'phase': 'dday', 'category': 'asset', 'title': 'Logistik: pastikan semua barang dibawa ke venue', 'assignee': 'family', 'linked_tool': 'Asset Custodian', 'is_critical': True},
    {'phase': 'dday', 'category': 'asset', 'title': 'Serah terima barang berharga ke PIC', 'assignee': 'both', 'linked_tool': 'Asset Custodian', 'is_critical': True},
    {'phase': 'dday', 'category': 'post', 'title': 'Pengembalian kotak seserahan sewa & busana adat', 'assignee': 'family'},
    {'phase': 'dday', 'category': 'post', 'title': 'Rekap amplop / angpao & hitung total', 'assignee': 'both'},
]


def _create_default_data(wedding):
    """Populate default budget categories and task milestones for a new workspace."""
    from finances.models import BudgetCategory
    from operations.models import TaskMilestone
    from guests.models import CateringConfig

    style = wedding.budget_style or 'balanced'

    # Create budget categories
    for i, cat in enumerate(DEFAULT_BUDGET_CATEGORIES):
        BudgetCategory.objects.create(
            wedding=wedding,
            name=cat['name'],
            icon=cat['icon'],
            allocation_percentage=cat['allocation'].get(style, 0),
            sort_order=i,
        )

    # Create default task milestones
    for i, task in enumerate(DEFAULT_TASKS):
        TaskMilestone.objects.create(
            wedding=wedding,
            phase=task['phase'],
            category=task.get('category', 'other'),
            title=task['title'],
            assignee=task.get('assignee', 'both'),
            linked_tool=task.get('linked_tool', ''),
            is_critical=task.get('is_critical', False),
            sort_order=i,
        )

    # Create default catering config
    CateringConfig.objects.create(wedding=wedding)


def _ensure_default_invitations(wedding, created_by=None, include_owner=False):
    """Ensure starter WorkspaceInvitation codes exist for a newly created wedding."""
    if include_owner and not wedding.invitations.filter(role='owner', is_active=True).exists():
        WorkspaceInvitation.objects.create(
            wedding=wedding,
            role='owner',
            max_uses=2,
            created_by=created_by,
        )
    if not include_owner and not wedding.invitations.filter(role='co_owner', is_active=True).exists():
        WorkspaceInvitation.objects.create(
            wedding=wedding,
            role='co_owner',
            max_uses=1,
            created_by=created_by,
        )
    if not wedding.invitations.filter(role='crew', is_active=True).exists():
        WorkspaceInvitation.objects.create(
            wedding=wedding,
            role='crew',
            max_uses=None,
            created_by=created_by,
        )


def landing_view(request):
    """Public landing page for Rangkai with pricing packages."""
    return render(request, 'core/landing.html', {
        'plans': PRICING_PLANS,
    })


def _get_effective_plans():
    """Return PRICING_PLANS with optional SUMOPOD_TEST_AMOUNT override for local testing."""
    test_amount = getattr(settings, 'SUMOPOD_TEST_AMOUNT', 0) or 0
    if test_amount > 0:
        formatted_test = f'Rp {test_amount:,}'.replace(',', '.')
        effective = {
            k: {**v, 'price': test_amount, 'price_display': formatted_test}
            for k, v in PRICING_PLANS.items()
        }
        return effective, test_amount
    return PRICING_PLANS, 0


def _get_active_pending_order(user):
    """Return latest non-expired pending Order with payment_link_url for user, or None."""
    pending_order = (
        Order.objects.filter(user=user, status='pending')
        .order_by('-created_at')
        .first()
    )
    if pending_order and pending_order.expires_at and timezone.now() > pending_order.expires_at:
        pending_order.status = 'expired'
        pending_order.save(update_fields=['status'])
        return None
    if pending_order and not pending_order.payment_link_url:
        return None
    return pending_order


def _extract_invite_preview(request, next_url=''):
    """Extract optional invite preview dict from ?code= or from ?next=/join/?code=XXXX."""
    from urllib.parse import urlparse, parse_qs

    code = (request.GET.get('code') or '').strip().upper()
    if not code and next_url:
        parsed = urlparse(next_url)
        qs = parse_qs(parsed.query)
        raw_codes = qs.get('code') or []
        if raw_codes:
            code = raw_codes[0].strip().upper()
    if not code:
        return None

    p_wedding, p_role, _, p_err = resolve_invite_code(code)
    if p_err:
        return {'code': code, 'error': p_err}
    if p_wedding:
        return {
            'code': code,
            'wedding': p_wedding,
            'role_label': dict(WeddingMembership.ROLE_CHOICES).get(p_role, p_role),
        }
    return None


def home_view(request):
    """Show public landing page to guests, or appropriate home to authenticated users."""
    if request.user.is_authenticated:
        if getattr(request, 'wedding', None):
            return dashboard_view(request)
        if getattr(request, 'is_platform_admin', False):
            return redirect('core:admin_console')
        profile = getattr(request, 'account_profile', None) or get_or_create_profile(request.user)
        if profile.plan_status != 'active':
            return redirect('core:onboarding')
        if profile.is_wo_account:
            return redirect('core:wo_portal')
        return redirect('core:onboarding')
    return landing_view(request)


@login_required
def onboarding_view(request):
    """
    Layer-2 Onboarding Hub for authenticated users who don't yet have active workspace access.
    Presents two equal paths side by side:
      A) Purchase a package (Wedding Owner or WO Manager) -> /checkout/
      B) Join an existing workspace via 8-char invite code (free) -> /join/
    """
    profile = get_or_create_profile(request.user)
    if profile.is_platform_admin:
        return redirect('core:admin_console')
    if profile.plan_status == 'active':
        if profile.is_wo_account:
            return redirect('core:wo_portal')
        if WeddingMembership.objects.filter(user=request.user).exists():
            return redirect('core:dashboard')

    effective_plans, test_amount = _get_effective_plans()
    active_pending_order = _get_active_pending_order(request.user)

    return render(request, 'core/onboarding.html', {
        'plans': effective_plans,
        'active_pending_order': active_pending_order,
        'join_form': JoinWorkspaceForm(),
        'test_amount': test_amount,
    })


def _fulfill_paid_order(order, paid_at=None, fee=None, net_amount=None):
    """
    Idempotently mark an Order as paid, activate the user's AccountProfile,
    and provision the Wedding workspace (if wedding_owner plan).
    Returns (order, wedding_or_none, newly_fulfilled_bool).
    """
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        user = locked_order.user
        plan_info = PRICING_PLANS.get(locked_order.plan_type, PRICING_PLANS['wedding_owner'])

        if locked_order.status == 'paid':
            existing_wedding = None
            if user and locked_order.plan_type == 'wedding_owner':
                membership = WeddingMembership.objects.filter(
                    user=user,
                    role__in=('owner', 'co_owner'),
                ).select_related('wedding').first()
                existing_wedding = membership.wedding if membership else None
            return locked_order, existing_wedding, False

        locked_order.status = 'paid'
        locked_order.paid_at = paid_at or timezone.now()
        update_fields = ['status', 'paid_at']
        if fee is not None:
            locked_order.gateway_fee = fee
            update_fields.append('gateway_fee')
        if net_amount is not None:
            locked_order.net_amount = net_amount
            update_fields.append('net_amount')
        locked_order.save(update_fields=update_fields)

        wedding = None
        if user:
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])

            profile = get_or_create_profile(user)
            profile.account_type = plan_info['account_type']
            profile.project_quota = plan_info['quota']
            profile.plan_status = 'active'
            meta = locked_order.metadata or {}
            if meta.get('organization_name') and not profile.organization_name:
                profile.organization_name = meta['organization_name']
            profile.save(update_fields=['account_type', 'project_quota', 'plan_status', 'organization_name'])

            if locked_order.plan_type == 'wedding_owner':
                existing_membership = WeddingMembership.objects.filter(
                    user=user,
                    role__in=('owner', 'co_owner'),
                ).select_related('wedding').first()
                if existing_membership:
                    wedding = existing_membership.wedding
                else:
                    raw_date = meta.get('wedding_date')
                    parsed_date = None
                    if raw_date:
                        try:
                            parsed_date = date.fromisoformat(str(raw_date))
                        except ValueError:
                            parsed_date = None
                    wedding = Wedding.objects.create(
                        groom_name=(meta.get('groom_name') or 'Pengantin Pria').strip(),
                        bride_name=(meta.get('bride_name') or 'Pengantin Wanita').strip(),
                        wedding_date=parsed_date,
                    )
                    WeddingMembership.objects.create(
                        user=user,
                        wedding=wedding,
                        role='owner',
                    )
                    _create_default_data(wedding)
                    _ensure_default_invitations(wedding, created_by=user, include_owner=False)

        return locked_order, wedding, True


def _sync_order_with_sumopod(order):
    """
    Query Sumopod GET /api/v1/payments/{payment_id} to verify latest payment status.
    Returns (updated_order, error_message_or_none).
    """
    if order.status != 'pending' or not order.gateway_ref or not sumopod.is_configured():
        return order, None

    try:
        remote = sumopod.get_payment_status(order.gateway_ref)
    except sumopod.SumopodError as exc:
        # Sumopod Managed Payment is webhook-driven and returns 404 on GET /payments/{id}.
        # Silently rely on local DB status (updated via webhook) without surfacing an error.
        if exc.status_code == 404:
            return order, None
        logger.warning('Failed to sync order %s with Sumopod: %s', order.order_code, exc)
        return order, str(exc)

    remote_status = remote.get('status', 'pending')
    if remote_status in ('completed', 'paid', 'settled'):
        order, _, _ = _fulfill_paid_order(
            order,
            paid_at=remote.get('paid_at'),
            fee=remote.get('fee'),
            net_amount=remote.get('net_amount'),
        )
    elif remote_status == 'expired':
        order.status = 'expired'
        order.save(update_fields=['status'])
    elif remote_status in ('failed', 'cancelled'):
        order.status = 'failed'
        order.save(update_fields=['status'])

    return order, None


def _can_access_order(request, order):
    """Allow order buyer (via session or authenticated account) or Platform Admin."""
    if request.session.get('pending_order_code') == order.order_code:
        return True
    if request.user.is_authenticated:
        if order.user_id == request.user.id or getattr(request, 'is_platform_admin', False):
            return True
    return False


def checkout_view(request):
    """
    Layer-2 Package Checkout (for authenticated users without an active paid plan).
    Guests are redirected to /register/?next=/checkout/... so account creation stays clean and separate.
    """
    if not request.user.is_authenticated:
        from urllib.parse import quote
        next_target = quote(request.get_full_path(), safe='')
        return redirect(f"{reverse('core:register')}?next={next_target}")

    profile = get_or_create_profile(request.user)
    if profile.is_platform_admin:
        return redirect('core:admin_console')
    if profile.plan_status == 'active':
        if profile.is_wo_account:
            return redirect('core:wo_portal')
        if WeddingMembership.objects.filter(user=request.user).exists():
            return redirect('core:dashboard')

    selected_plan = request.GET.get('plan') or request.POST.get('plan_type') or 'wedding_owner'
    if selected_plan not in PRICING_PLANS:
        selected_plan = 'wedding_owner'

    sumopod_enabled = sumopod.is_configured()
    effective_plans, test_amount = _get_effective_plans()
    active_pending_order = _get_active_pending_order(request.user)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            plan_key = form.cleaned_data['plan_type']
            plan_info = effective_plans[plan_key]
            wedding_date_val = form.cleaned_data.get('wedding_date')
            onboarding_meta = {
                'groom_name': (form.cleaned_data.get('groom_name') or '').strip(),
                'bride_name': (form.cleaned_data.get('bride_name') or '').strip(),
                'wedding_date': wedding_date_val.isoformat() if wedding_date_val else '',
                'organization_name': (form.cleaned_data.get('organization_name') or '').strip(),
            }

            user = request.user
            Order.objects.filter(user=user, status='pending').update(status='cancelled')
            order = Order.objects.create(
                user=user,
                customer_email=user.email,
                plan_type=plan_key,
                amount=plan_info['price'],
                payment_method=form.cleaned_data.get('payment_method') or 'qris',
                status='pending',
                metadata=onboarding_meta,
            )

            if sumopod_enabled:
                pay_path = reverse('core:checkout_pay', kwargs={'order_code': order.order_code})
                success_url = request.build_absolute_uri(f'{pay_path}?returned=1')
                cancel_url = request.build_absolute_uri(f'{pay_path}?cancelled=1')

                try:
                    payment = sumopod.create_payment(
                        order_id=order.order_code,
                        amount=int(order.amount),
                        success_return_url=success_url,
                        cancel_return_url=cancel_url,
                        payment_method_type_code='QRIS',
                    )
                except sumopod.SumopodError as exc:
                    order.delete()
                    messages.error(
                        request,
                        f'Gagal membuat tagihan QRIS di Sumopod: {exc}. Silakan coba lagi.',
                    )
                    return render(request, 'core/checkout.html', {
                        'form': form,
                        'plans': effective_plans,
                        'selected_plan': plan_key,
                        'active_plan': plan_info,
                        'sumopod_enabled': sumopod_enabled,
                        'active_pending_order': active_pending_order,
                        'test_amount': test_amount,
                    })

                order.gateway_ref = payment['payment_id']
                order.payment_link_url = payment['payment_link_url']
                order.expires_at = payment['expires_at']
                order.gateway_fee = payment['fee']
                order.net_amount = payment['net_amount']
                order.save(update_fields=[
                    'gateway_ref', 'payment_link_url', 'expires_at', 'gateway_fee', 'net_amount',
                ])

                request.session['pending_order_code'] = order.order_code
                return redirect('core:checkout_pay', order_code=order.order_code)

            # Local dev fallback (simulated payment when SUMOPOD_API_KEY is empty)
            order.gateway_ref = f'SIM-{timezone.now().strftime("%H%M%S")}'
            order.save(update_fields=['gateway_ref'])
            order, wedding, _ = _fulfill_paid_order(order)
            if plan_key == 'wedding_owner' and wedding:
                request.session['active_wedding_id'] = wedding.pk
                messages.success(
                    request,
                    f'Pembayaran simulasi {order.order_code} berhasil! Workspace {wedding} siap digunakan.',
                )
                return redirect('core:dashboard')

            messages.success(
                request,
                f'Pembayaran simulasi {order.order_code} berhasil! Selamat datang di Portal WO {onboarding_meta["organization_name"]}.',
            )
            return redirect('core:wo_portal')
    else:
        latest_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
        prev_meta = (latest_order.metadata if latest_order and isinstance(latest_order.metadata, dict) else {}) or {}
        form = CheckoutForm(initial={
            'plan_type': selected_plan,
            'payment_method': 'qris',
            'groom_name': prev_meta.get('groom_name', ''),
            'bride_name': prev_meta.get('bride_name', ''),
            'wedding_date': prev_meta.get('wedding_date', ''),
            'organization_name': prev_meta.get('organization_name') or profile.organization_name or '',
        })

    return render(request, 'core/checkout.html', {
        'form': form,
        'plans': effective_plans,
        'selected_plan': selected_plan,
        'active_plan': effective_plans[selected_plan],
        'sumopod_enabled': sumopod_enabled,
        'active_pending_order': active_pending_order,
        'test_amount': test_amount,
    })


def checkout_select_plan_view(request):
    """Legacy URL alias redirecting cleanly to the Layer-2 Onboarding Hub."""
    if request.user.is_authenticated:
        return redirect('core:onboarding')
    return redirect('core:login')


def checkout_pay_view(request, order_code):
    """
    Native Rangkai payment page displaying embedded Sumopod QRIS payment frame,
    direct fallback link, countdown, and automatic status verification.
    """
    order = get_object_or_404(Order.objects.select_related('user'), order_code=order_code)
    if not _can_access_order(request, order):
        messages.info(request, 'Silakan masuk ke akun Anda untuk melihat status transaksi.')
        return redirect('core:login')

    sync_error = None
    if order.status == 'pending' and (request.GET.get('returned') == '1' or request.GET.get('check') == '1'):
        order, sync_error = _sync_order_with_sumopod(order)

    if order.status == 'paid':
        user = order.user
        if user and not request.user.is_authenticated and request.session.get('pending_order_code') == order.order_code:
            login(request, user)
            request.session.pop('pending_order_code', None)
            request.session.pop('unpaid_user_id', None)
        if user and order.plan_type == 'wedding_owner':
            membership = WeddingMembership.objects.filter(
                user=user,
                role__in=('owner', 'co_owner'),
            ).select_related('wedding').first()
            if membership:
                request.session['active_wedding_id'] = membership.wedding_id
            messages.success(
                request,
                f'Pembayaran QRIS {order.order_code} terkonfirmasi! Selamat datang di workspace Rangkai.click.',
            )
            return redirect('core:dashboard')
        messages.success(
            request,
            f'Pembayaran QRIS {order.order_code} terkonfirmasi! Selamat datang di Portal WO Rangkai.click.',
        )
        return redirect('core:wo_portal')

    plan_info = PRICING_PLANS.get(order.plan_type, PRICING_PLANS['wedding_owner'])
    return render(request, 'core/checkout_pay.html', {
        'order': order,
        'plan_info': plan_info,
        'cancelled': request.GET.get('cancelled') == '1',
        'sync_error': sync_error,
        'status_check_url': reverse('core:checkout_pay_status', kwargs={'order_code': order.order_code}),
        'expires_at_iso': order.expires_at.isoformat() if order.expires_at else '',
    })


def checkout_pay_status_view(request, order_code):
    """
    JSON polling endpoint used by checkout_pay.html every 5s and on manual click.
    Verifies payment status directly against Sumopod API when still pending.
    """
    order = get_object_or_404(Order.objects.select_related('user'), order_code=order_code)
    if not _can_access_order(request, order):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    sync_error = None
    if order.status == 'pending':
        order, sync_error = _sync_order_with_sumopod(order)

    return JsonResponse({
        'order_code': order.order_code,
        'status': order.status,
        'status_display': order.get_status_display(),
        'paid': order.status == 'paid',
        'redirect_url': reverse('core:checkout_pay', kwargs={'order_code': order.order_code}) if order.status == 'paid' else None,
        'error': sync_error,
    })


@csrf_exempt
@require_POST
def sumopod_webhook_view(request):
    """
    Sumopod Managed Payment webhook receiver.
    Supports both X-Webhook-Token (whtok_...) and Svix HMAC-SHA256 (whsec_...).
    Safely ignores non-RNK orders when sharing a Sumopod project with another app.
    """
    if not sumopod.verify_webhook_request(request.headers, request.body):
        logger.warning('Rejected Sumopod webhook with invalid token/signature.')
        return JsonResponse({'error': 'Invalid webhook authentication'}, status=401)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    event_type = str(payload.get('event_type') or payload.get('event') or '').strip().lower()
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}

    self_url = request.build_absolute_uri(request.path).rstrip('/')

    if event_type == 'payment.test':
        forward_url = getattr(settings, 'SUMOPOD_FORWARD_WEBHOOK_URL', '').strip()
        if forward_url and forward_url.rstrip('/') != self_url:
            sumopod.forward_webhook(forward_url, request.headers, request.body)
        return JsonResponse({'ok': True, 'event': 'payment.test'})

    order_id = str(data.get('order_id') or '').strip()
    payment_id = str(data.get('payment_id') or '').strip()

    # Shared-project routing: forward non-RNK events (e.g. TickerWatch) if configured,
    # otherwise safely acknowledge and ignore. Guard against accidental self-forwarding loop.
    if not order_id.startswith('RNK-'):
        forward_url = getattr(settings, 'SUMOPOD_FORWARD_WEBHOOK_URL', '').strip()
        if forward_url and forward_url.rstrip('/') != self_url:
            fwd_status, _ = sumopod.forward_webhook(forward_url, request.headers, request.body)
            return JsonResponse(
                {'ok': 200 <= fwd_status < 300, 'forwarded': True, 'downstream_status': fwd_status},
                status=fwd_status if 200 <= fwd_status < 600 else 502,
            )
        return JsonResponse({'ok': True, 'ignored': True, 'reason': 'non_rangkai_order'})

    order = Order.objects.filter(order_code=order_id).first()
    if not order and payment_id:
        order = Order.objects.filter(gateway_ref=payment_id).first()
    if not order:
        logger.info('Sumopod webhook order not found: %s', order_id)
        return JsonResponse({'ok': True, 'ignored': True, 'reason': 'order_not_found'})

    if event_type == 'payment.completed':
        paid_at = sumopod.parse_iso_datetime(data.get('paid_at') or data.get('completed_at'))
        _fulfill_paid_order(
            order,
            paid_at=paid_at,
            fee=data.get('fee'),
            net_amount=data.get('net_amount'),
        )
        return JsonResponse({'ok': True, 'order_code': order.order_code, 'status': 'paid'})

    if event_type == 'payment.expired':
        if order.status == 'pending':
            order.status = 'expired'
            order.save(update_fields=['status'])
        return JsonResponse({'ok': True, 'order_code': order.order_code, 'status': order.status})

    if event_type == 'payment.failed':
        if order.status == 'pending':
            order.status = 'failed'
            order.save(update_fields=['status'])
        return JsonResponse({'ok': True, 'order_code': order.order_code, 'status': order.status})

    return JsonResponse({'ok': True, 'ignored': True, 'event': event_type})


def register_view(request):
    """
    Layer-1 Pure Identity Registration (username, email, password only).
    Creates a pending account, logs the user in, and routes them either to ?next=
    (e.g. /checkout/?plan=... or /join/?code=...) or to the Layer-2 Onboarding Hub (/onboarding/).
    """
    from django.utils.http import url_has_allowed_host_and_scheme

    next_url = (request.POST.get('next') or request.GET.get('next') or '').strip()
    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                AccountProfile.objects.create(
                    user=user,
                    account_type='couple',
                    project_quota=0,
                    plan_status='pending',
                )
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            messages.success(
                request,
                f'Akun {user.username} berhasil dibuat! Pilih paket atau masukkan kode undangan untuk mulai.',
            )
            return redirect('core:onboarding')
    else:
        form = RegisterForm()

    invite_preview = _extract_invite_preview(request, next_url)
    return render(request, 'core/register.html', {
        'form': form,
        'next': next_url,
        'invite_preview': invite_preview,
    })


def login_view(request):
    """
    Layer-1 Pure Login.
    Authenticated users without active access (plan_status != 'active') are routed
    to Layer-2 (/onboarding/) and blocked from Layer-3 routes by WorkspaceMiddleware.
    """
    from django.utils.http import url_has_allowed_host_and_scheme

    next_url = (request.POST.get('next') or request.GET.get('next') or '').strip()
    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            profile = get_or_create_profile(user)
            if profile.is_platform_admin:
                messages.success(request, f'Selamat datang kembali, {user.username}!')
                return redirect('core:admin_console')
            if profile.plan_status != 'active':
                return redirect('core:onboarding')
            messages.success(request, f'Selamat datang kembali, {user.username}!')
            if profile.is_wo_account:
                return redirect('core:wo_portal')
            if WeddingMembership.objects.filter(user=user).exists():
                return redirect('core:dashboard')
            return redirect('core:onboarding')
    else:
        form = LoginForm()

    invite_preview = _extract_invite_preview(request, next_url)
    return render(request, 'core/login.html', {
        'form': form,
        'next': next_url,
        'invite_preview': invite_preview,
    })


def logout_view(request):
    """User logout."""
    logout(request)
    messages.info(request, 'Berhasil logout.')
    return redirect('core:login')


@login_required
def change_password_view(request):
    """Allow any authenticated user (Owner, Co-Owner, WO Manager, Crew, Admin) to change their password."""
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.forms import PasswordChangeForm

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password berhasil diperbarui!')
            return redirect('core:change_password')
    else:
        form = PasswordChangeForm(request.user)

    for field in form.fields.values():
        field.widget.attrs['class'] = 'wp-input'

    return render(request, 'core/change_password.html', {'form': form})


def join_workspace_view(request):
    """
    Layer-2 Join Workspace via role-bound 8-character invite code (free).
    Guests are redirected to /register/?next=/join/?code=... so account creation
    and invite joining stay cleanly decoupled.
    """
    if not request.user.is_authenticated:
        from urllib.parse import quote
        next_target = quote(request.get_full_path(), safe='')
        return redirect(f"{reverse('core:register')}?next={next_target}")

    prefill_code = (request.GET.get('code') or '').strip().upper()
    has_couple_wedding = WeddingMembership.objects.filter(
        user=request.user,
        role__in=('owner', 'co_owner'),
    ).exists()

    if request.method == 'POST':
        form = JoinWorkspaceForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['invite_code'].strip().upper()
            wedding, target_role, invitation, err = resolve_invite_code(code)
            if err:
                form.add_error('invite_code', err)
            elif WeddingMembership.objects.filter(user=request.user, wedding=wedding).exists():
                profile = get_or_create_profile(request.user)
                if profile.plan_status != 'active':
                    profile.plan_status = 'active'
                    profile.save(update_fields=['plan_status'])
                request.session['active_wedding_id'] = wedding.pk
                messages.info(request, f'Anda sudah tergabung di workspace {wedding}.')
                return redirect('core:dashboard')
            elif target_role in ('owner', 'co_owner') and has_couple_wedding:
                form.add_error(
                    'invite_code',
                    'Akun pengantin hanya bisa memiliki 1 workspace pernikahan. Untuk mengelola banyak acara, gunakan akun WO Manager.',
                )
            else:
                try:
                    WeddingMembership.objects.create(
                        user=request.user,
                        wedding=wedding,
                        role=target_role,
                    )
                except ValidationError as exc:
                    form.add_error('invite_code', exc.messages[0])
                else:
                    if invitation:
                        invitation.uses_count += 1
                        if invitation.max_uses and invitation.uses_count >= invitation.max_uses:
                            invitation.is_active = False
                        invitation.save(update_fields=['uses_count', 'is_active'])

                    # Activate pending accounts joining via valid invite code (free access)
                    profile = get_or_create_profile(request.user)
                    if profile.plan_status != 'active':
                        acc_type = 'couple' if target_role in ('owner', 'co_owner') else (
                            'wo_manager' if target_role == 'wo_manager' else 'crew'
                        )
                        profile.account_type = acc_type
                        profile.project_quota = 1 if acc_type == 'couple' else (10 if acc_type == 'wo_manager' else 0)
                        profile.plan_status = 'active'
                        profile.save(update_fields=['account_type', 'project_quota', 'plan_status'])
                        Order.objects.filter(user=request.user, status='pending').update(status='cancelled')

                    request.session['active_wedding_id'] = wedding.pk
                    role_label = dict(WeddingMembership.ROLE_CHOICES).get(target_role, target_role)
                    messages.success(request, f'Berhasil bergabung ke workspace {wedding} sebagai {role_label}!')
                    return redirect('core:dashboard')
    else:
        form = JoinWorkspaceForm(initial={'invite_code': prefill_code} if prefill_code else None)

    invite_preview = _extract_invite_preview(request)
    return render(request, 'core/join_workspace.html', {
        'form': form,
        'invite_preview': invite_preview,
    })


@login_required
def switch_workspace_view(request, pk):
    """Switch active Wedding workspace in session (for WO Manager, multi-project Crew, or Platform Admin)."""
    wedding = get_object_or_404(Wedding, pk=pk)
    if not getattr(request, 'is_platform_admin', False):
        if not WeddingMembership.objects.filter(user=request.user, wedding=wedding).exists():
            messages.error(request, 'Anda tidak memiliki akses ke workspace tersebut.')
            return redirect('core:dashboard')

    request.session['active_wedding_id'] = wedding.pk
    messages.success(request, f'Berpindah ke workspace {wedding}.')
    return redirect('core:dashboard')


@login_required
def exit_workspace_inspect_view(request):
    """Clear active workspace session and return to Admin Console or WO Portal."""
    request.session.pop('active_wedding_id', None)
    if getattr(request, 'is_platform_admin', False):
        return redirect('core:admin_console')
    profile = getattr(request, 'account_profile', None)
    if profile and profile.is_wo_account:
        return redirect('core:wo_portal')
    return redirect('core:dashboard')


@login_required
@wo_portal_required
def wo_portal_view(request):
    """Agency dashboard for WO Manager (and Platform Admin) to manage multiple client weddings."""
    profile = get_or_create_profile(request.user)
    if profile.is_platform_admin:
        weddings_qs = Wedding.objects.all().prefetch_related('memberships__user', 'invitations')
    else:
        weddings_qs = (
            Wedding.objects
            .filter(Q(managed_by=request.user) | Q(memberships__user=request.user, memberships__role='wo_manager'))
            .distinct()
            .prefetch_related('memberships__user', 'invitations')
        )

    from operations.models import TaskMilestone
    weddings_list = list(weddings_qs)
    task_counts_map = {
        row['wedding_id']: (row['total'], row['done'])
        for row in (
            TaskMilestone.objects
            .filter(wedding__in=weddings_list)
            .values('wedding_id')
            .annotate(total=Count('id'), done=Count('id', filter=Q(status='done')))
        )
    }

    projects = []
    nearest_days = None
    for w in weddings_list:
        total_tasks, done_tasks = task_counts_map.get(w.pk, (0, 0))
        progress = round((done_tasks / total_tasks) * 100) if total_tasks else 0

        couple_members = [m for m in w.memberships.all() if m.role in ('owner', 'co_owner')]
        crew_count = sum(1 for m in w.memberships.all() if m.role == 'crew')
        couple_invite = next((inv for inv in w.invitations.all() if inv.role == 'owner' and inv.is_valid), None)
        crew_invite = next((inv for inv in w.invitations.all() if inv.role == 'crew' and inv.is_valid), None)

        days = w.days_remaining
        if days is not None and (nearest_days is None or days < nearest_days):
            nearest_days = days

        projects.append({
            'wedding': w,
            'progress': progress,
            'done_tasks': done_tasks,
            'total_tasks': total_tasks,
            'couple_members': couple_members,
            'crew_count': crew_count,
            'couple_invite': couple_invite,
            'crew_invite': crew_invite,
            'days_remaining': days,
        })

    return render(request, 'core/wo_portal.html', {
        'profile': profile,
        'projects': projects,
        'active_count': len(projects),
        'nearest_days': nearest_days,
        'create_form': WOProjectCreateForm(),
    })


@login_required
@wo_portal_required
def wo_create_project_view(request):
    """Create a new client Wedding workspace under WO Manager account."""
    profile = get_or_create_profile(request.user)
    if request.method == 'POST':
        if not profile.can_create_wo_project:
            messages.error(
                request,
                f'Kuota project aktif Anda ({profile.project_quota}) sudah penuh. Upgrade paket atau arsipkan project lama.',
            )
            return redirect('core:wo_portal')

        form = WOProjectCreateForm(request.POST)
        if form.is_valid():
            wedding = form.save(commit=False)
            wedding.managed_by = request.user
            wedding.save()

            WeddingMembership.objects.create(
                user=request.user,
                wedding=wedding,
                role='wo_manager',
            )
            _create_default_data(wedding)
            _ensure_default_invitations(wedding, created_by=request.user, include_owner=True)

            messages.success(
                request,
                f'Project klien {wedding} berhasil dibuat! Bagikan kode Pengantin agar klien bisa masuk dengan ruang Tabungan privat.',
            )
        else:
            messages.error(request, 'Gagal membuat project. Periksa kembali data pengantin.')
    return redirect('core:wo_portal')


@login_required
@platform_admin_required
def admin_console_view(request):
    """Platform Admin Console with ALL access across workspaces, users, quotas, and orders."""
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            target_user = get_object_or_404(User, pk=request.POST.get('user_id'))
            prof = get_or_create_profile(target_user)
            new_type = request.POST.get('account_type')
            if new_type in dict(AccountProfile.ACCOUNT_TYPE_CHOICES):
                prof.account_type = new_type
                if new_type == 'admin':
                    target_user.is_staff = True
                    target_user.is_superuser = True
                    target_user.save(update_fields=['is_staff', 'is_superuser'])
            try:
                prof.project_quota = max(0, int(request.POST.get('project_quota', prof.project_quota)))
            except (TypeError, ValueError):
                pass
            prof.organization_name = (request.POST.get('organization_name') or '').strip()
            prof.save()
            messages.success(request, f'Profil akun {target_user.username} berhasil diperbarui.')
        elif action == 'reset_password':
            target_user = get_object_or_404(User, pk=request.POST.get('user_id'))
            new_pwd = (request.POST.get('new_password') or '').strip()
            if len(new_pwd) < 8:
                messages.error(request, 'Password baru minimal 8 karakter.')
            else:
                target_user.set_password(new_pwd)
                target_user.save(update_fields=['password'])
                messages.success(request, f'Password akun {target_user.username} berhasil di-reset oleh Platform Admin.')
        elif action == 'create_account':
            uname = (request.POST.get('username') or '').strip()
            email = (request.POST.get('email') or '').strip()
            pwd = request.POST.get('password') or ''
            acc_type = request.POST.get('account_type') or 'wo_manager'
            org_name = (request.POST.get('organization_name') or '').strip()
            try:
                quota = max(0, int(request.POST.get('project_quota') or (0 if acc_type == 'admin' else 10)))
            except (TypeError, ValueError):
                quota = 0 if acc_type == 'admin' else 10

            if not uname or len(pwd) < 8:
                messages.error(request, 'Username wajib diisi dan password minimal 8 karakter.')
            elif User.objects.filter(username=uname).exists():
                messages.error(request, f'Username "{uname}" sudah digunakan.')
            else:
                new_user = User.objects.create_user(username=uname, email=email, password=pwd)
                if acc_type == 'admin':
                    new_user.is_staff = True
                    new_user.is_superuser = True
                    new_user.save(update_fields=['is_staff', 'is_superuser'])
                AccountProfile.objects.create(
                    user=new_user,
                    account_type=acc_type,
                    organization_name=org_name,
                    project_quota=quota,
                )
                messages.success(request, f'Akun {uname} ({acc_type}) berhasil dibuat.')
        elif action == 'mark_order_paid':
            order_id = request.POST.get('order_id')
            target_order = get_object_or_404(Order, pk=order_id)
            if target_order.status == 'paid':
                messages.info(request, f'Order {target_order.order_code} sudah berstatus Lunas.')
            else:
                target_order, wedding, _ = _fulfill_paid_order(target_order)
                extra = f' & workspace {wedding} aktif.' if wedding else '.'
                messages.success(request, f'Order {target_order.order_code} ditandai Lunas secara manual{extra}')
        return redirect('core:admin_console')

    weddings = Wedding.objects.all().select_related('managed_by').prefetch_related('memberships__user')
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    for u in users:
        if not hasattr(u, 'profile'):
            get_or_create_profile(u)
    orders = Order.objects.all().select_related('user')[:50]

    total_revenue = Order.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'core/admin_console.html', {
        'weddings': weddings,
        'users': users,
        'orders': orders,
        'total_weddings': weddings.count(),
        'total_users': users.count(),
        'total_wo': AccountProfile.objects.filter(account_type='wo_manager').count(),
        'total_revenue': total_revenue,
        'account_type_choices': AccountProfile.ACCOUNT_TYPE_CHOICES,
    })


@login_required
@workspace_required
def dashboard_view(request):
    """Overview Hub with 4 KPI cards and active phase snapshot."""
    wedding = request.wedding

    # KPI 1: Days remaining
    days_remaining = wedding.days_remaining

    # KPI 2: Budget summary & Sankey Data — computed from single prefetch (0 duplicate BudgetItem queries)
    from finances.models import BudgetItem, BudgetCategory
    from vendors.models import VendorCandidate
    import json

    categories_with_items = list(
        BudgetCategory.objects.filter(wedding=wedding).prefetch_related('items')
    )

    total_actual = 0
    total_paid = 0
    sankey_data = []
    seen_item_names = {}  # track name usage to avoid Google Sankey node collision
    urgent_cutoff = timezone.now().date() + timedelta(days=7)
    overdue_items = []

    for cat in categories_with_items:
        cat_items = list(cat.items.all())
        items_with_cost = []
        cat_total = 0.0
        for item in cat_items:
            total_actual += item.actual_cost or 0
            total_paid += item.paid_amount or 0
            if item.actual_cost and item.actual_cost > 0:
                items_with_cost.append(item)
                cat_total += float(item.actual_cost)
            if item.due_date and item.due_date <= urgent_cutoff and item.payment_status != 'settled':
                overdue_items.append(item)

        if cat_total > 0:
            # Layer 1: Total Budget → Category
            sankey_data.append(['Total Budget', cat.name, cat_total])
            # Layer 2: Category → each Item
            for item in items_with_cost:
                base_name = item.name
                count = seen_item_names.get(base_name, 0)
                item_node = base_name + ('\u200b' * count)
                seen_item_names[base_name] = count + 1
                sankey_data.append([cat.name, item_node, float(item.actual_cost)])

    overdue_items.sort(key=lambda i: i.due_date)
    budget_remaining = wedding.total_budget - total_actual

    if budget_remaining > 0:
        sankey_data.append(['Total Budget', 'Sisa Budget', float(budget_remaining)])

    sankey_data_json = json.dumps(sankey_data)

    # Booked Vendors
    booked_vendors = list(VendorCandidate.objects.filter(wedding=wedding, status='booked'))

    # KPI 3: RSVP stats
    from guests.models import Guest
    guest_stats = Guest.objects.filter(wedding=wedding).aggregate(
        total_guests=Count('id'),
        attending=Count('id', filter=Q(rsvp_status='attending')),
        total_pax=Sum('pax_allocation'),
        attending_pax=Sum('pax_allocation', filter=Q(rsvp_status='attending')),
    )

    # KPI 4: Task progress + active tasks + today's exact TimelinePhase (if within any phase range)
    from operations.models import TaskMilestone
    from operations.views import _ensure_wedding_phases
    all_wedding_tasks = list(TaskMilestone.objects.filter(wedding=wedding))
    phase_objs = _ensure_wedding_phases(wedding, all_tasks_list=all_wedding_tasks)
    current_phase = None
    if wedding.wedding_date:
        days_before_today = (wedding.wedding_date - timezone.localdate()).days
        current_phase = next((p for p in phase_objs if p.contains_days_before(days_before_today)), None)

    done_count = sum(1 for t in all_wedding_tasks if t.status == 'done')
    in_progress_count = sum(1 for t in all_wedding_tasks if t.status == 'in_progress')
    task_stats = {
        'total': len(all_wedding_tasks),
        'done': done_count,
        'in_progress': in_progress_count,
    }
    task_total = task_stats['total'] or 1
    task_progress = round((done_count / task_total) * 100)
    active_tasks = [t for t in all_wedding_tasks if t.status in ('todo', 'in_progress')][:10]

    context = {
        'days_remaining': days_remaining,
        'current_phase': current_phase,
        'budget_remaining': budget_remaining,
        'total_actual': total_actual,
        'total_paid': total_paid,
        'sankey_data_json': sankey_data_json,
        'booked_vendors': booked_vendors,
        'guest_stats': guest_stats,
        'task_stats': task_stats,
        'task_progress': task_progress,
        'overdue_items': overdue_items,
        'active_tasks': active_tasks,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@owner_required
def settings_view(request):
    """Edit wedding workspace settings, role-bound invitations, privacy controls & collaborators."""
    wedding = request.wedding
    hide_budget_fields = (
        request.wedding_role == 'wo_manager' and not wedding.allow_wo_budget_access
    )

    if request.method == 'POST':
        form = WeddingSettingsForm(request.POST, instance=wedding, hide_budget_fields=hide_budget_fields)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pengaturan berhasil disimpan.')
            if request.htmx:
                return render(request, 'core/partials/settings_form.html', {'form': form})
            return redirect('core:settings')
    else:
        form = WeddingSettingsForm(instance=wedding, hide_budget_fields=hide_budget_fields)

    memberships = (
        WeddingMembership.objects
        .filter(wedding=wedding)
        .select_related('user')
        .order_by('joined_at')
    )
    invitations = (
        WorkspaceInvitation.objects
        .filter(wedding=wedding, is_active=True)
        .order_by('-created_at')
    )

    role = request.wedding_role
    if role in ('owner', 'admin'):
        allowed_invite_roles = [
            ('co_owner', 'Co-Owner (Pasangan)'),
            ('wo_manager', 'WO Manager'),
            ('crew', 'Crew / Operasional'),
        ]
    elif role == 'wo_manager':
        allowed_invite_roles = [
            ('owner', 'Wedding Owner (Pengantin, maks. 2 orang)'),
            ('crew', 'Crew / Operasional'),
        ]
    else:
        allowed_invite_roles = [
            ('crew', 'Crew / Operasional'),
        ]

    return render(request, 'core/settings.html', {
        'form': form,
        'memberships': memberships,
        'invitations': invitations,
        'allowed_invite_roles': allowed_invite_roles,
    })


@login_required
@owner_required
def regenerate_invite_code_view(request):
    """Generate a fresh 8-character legacy invite code."""
    if request.method == 'POST':
        request.wedding.regenerate_invite_code()
        messages.success(request, f'Kode undangan baru dibuat: {request.wedding.invite_code}')
    return redirect('core:settings')


@login_required
@owner_required
def create_invitation_view(request):
    """Create a role-bound WorkspaceInvitation code."""
    if request.method == 'POST':
        role_req = request.POST.get('role', 'crew')
        actor_role = request.wedding_role

        allowed = {'crew'}
        if actor_role in ('owner', 'admin'):
            allowed = {'co_owner', 'wo_manager', 'crew', 'owner'}
        elif actor_role == 'wo_manager':
            allowed = {'owner', 'crew'}

        if role_req not in allowed:
            messages.error(request, 'Anda tidak memiliki izin membuat undangan untuk peran tersebut.')
            return redirect('core:settings')

        max_uses = 2 if role_req == 'owner' else (1 if role_req == 'co_owner' else None)
        inv = WorkspaceInvitation.objects.create(
            wedding=request.wedding,
            role=role_req,
            max_uses=max_uses,
            created_by=request.user,
        )
        messages.success(request, f'Kode undangan {inv.get_role_display()} dibuat: {inv.code}')
    return redirect('core:settings')


@login_required
@owner_required
def revoke_invitation_view(request, pk):
    """Deactivate a WorkspaceInvitation."""
    if request.method == 'POST':
        inv = get_object_or_404(WorkspaceInvitation, pk=pk, wedding=request.wedding)
        inv.is_active = False
        inv.save(update_fields=['is_active'])
        messages.info(request, f'Kode undangan {inv.code} dinonaktifkan.')
    return redirect('core:settings')


@login_required
@couple_only_required
def toggle_wo_privacy_view(request):
    """Allow Wedding Owner / Co-Owner (or Admin) to toggle WO Manager access to Anggaran & Kas."""
    if request.method == 'POST':
        wedding = request.wedding
        wedding.allow_wo_budget_access = not wedding.allow_wo_budget_access
        wedding.save(update_fields=['allow_wo_budget_access'])
        state_text = 'diizinkan' if wedding.allow_wo_budget_access else 'dikunci (privat)'
        messages.success(request, f'Akses WO Manager ke Anggaran & Kas sekarang {state_text}. Tabungan tetap privat.')
    return redirect('core:settings')


@login_required
@owner_required
def manage_member_view(request, pk):
    """Update role or remove a workspace member (Owner/Admin full; WO Manager can remove crew)."""
    actor_role = request.wedding_role
    if actor_role not in ('owner', 'admin', 'wo_manager'):
        messages.error(request, 'Anda tidak memiliki izin untuk mengelola anggota.')
        return redirect('core:settings')

    if request.method == 'POST':
        member = get_object_or_404(WeddingMembership, pk=pk, wedding=request.wedding)
        if member.user_id == request.user.id or (member.role == 'owner' and actor_role != 'admin'):
            messages.error(request, 'Tidak dapat mengubah atau menghapus Owner utama workspace.')
            return redirect('core:settings')

        if actor_role == 'wo_manager' and member.role != 'crew':
            messages.error(request, 'WO Manager hanya dapat mengelola anggota dengan peran Crew.')
            return redirect('core:settings')

        action = request.POST.get('action')
        if action == 'remove':
            # Prevent owner from kicking the managing WO on an agency-managed project
            if actor_role == 'owner' and member.role == 'wo_manager' and request.wedding.managed_by_id == member.user_id:
                messages.error(request, 'WO pengelola utama tidak dapat dihapus dari project yang dikelola WO.')
                return redirect('core:settings')
            username = member.user.username
            member.delete()
            messages.success(request, f'{username} telah dihapus dari workspace.')
        elif action == 'set_role' and actor_role in ('owner', 'admin'):
            new_role = request.POST.get('role')
            if new_role in ('co_owner', 'wo_manager', 'crew'):
                try:
                    member.role = new_role
                    member.save()
                except ValidationError as exc:
                    messages.error(request, exc.messages[0])
                else:
                    messages.success(request, f'Peran {member.user.username} diperbarui menjadi {member.get_role_display()}.')
    return redirect('core:settings')

@login_required
@workspace_required
def guide_view(request):
    return render(request, 'core/guide.html')
