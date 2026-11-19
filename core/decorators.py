"""
Decorators for workspace and platform-level access control.
Roles:
  - Platform level: 'admin' (ALL access), 'wo_manager' (WO Portal + multi-workspace), 'couple', 'crew'
  - Workspace level: 'admin' (inspect), 'owner', 'co_owner', 'wo_manager', 'crew'
"""
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from core.models import get_or_create_profile


def _is_platform_admin(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = get_or_create_profile(user)
    return profile.is_platform_admin


def workspace_required(view_func):
    """Ensure user has an active wedding workspace."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.wedding:
            if _is_platform_admin(request.user):
                return redirect(reverse('core:admin_console'))
            profile = get_or_create_profile(request.user) if request.user.is_authenticated else None
            if profile and profile.is_wo_account:
                return redirect(reverse('core:wo_portal'))
            return redirect(reverse('core:join_workspace'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def owner_required(view_func):
    """
    Ensure user is owner, co_owner, wo_manager, or platform admin (not crew).
    Used for operational management actions in guests, operations, and general settings.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.wedding:
            return redirect(reverse('core:join_workspace'))
        if request.wedding_role not in ('owner', 'co_owner', 'wo_manager', 'admin'):
            return HttpResponseForbidden('Akses terbatas untuk peran Crew / Operasional.')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def couple_only_required(view_func):
    """
    Strict private access: ONLY Wedding Owner, Co-Owner, and Platform Admin.
    Blocks WO Manager and Crew (used for private Savings Tracker & couple-only controls).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.wedding:
            return redirect(reverse('core:join_workspace'))
        if request.wedding_role not in ('owner', 'co_owner', 'admin'):
            return HttpResponseForbidden(
                'Data ini bersifat privat dan hanya dapat diakses oleh Pengantin (Owner / Co-Owner).'
            )
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def finance_access_required(view_func):
    """
    Access for Budget & Vendor modules:
    - Always allowed: owner, co_owner, admin
    - Conditionally allowed: wo_manager (only if wedding.allow_wo_budget_access is True)
    - Always blocked: crew
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.wedding:
            return redirect(reverse('core:join_workspace'))
        role = request.wedding_role
        if role in ('owner', 'co_owner', 'admin'):
            return view_func(request, *args, **kwargs)
        if role == 'wo_manager' and getattr(request.wedding, 'allow_wo_budget_access', False):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden(
            'Akses ke modul Budget & Vendor dinonaktifkan untuk peran Anda pada workspace ini.'
        )
    return _wrapped_view


def wo_portal_required(view_func):
    """Ensure user has a WO Manager account or is Platform Admin."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse('core:login'))
        profile = get_or_create_profile(request.user)
        if profile.is_platform_admin or profile.is_wo_account:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden('Halaman Portal WO khusus untuk akun WO Manager.')
    return _wrapped_view


def platform_admin_required(view_func):
    """Ensure user is a Platform Admin (ALL access)."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse('core:login'))
        if not _is_platform_admin(request.user):
            return HttpResponseForbidden('Halaman ini khusus untuk Platform Admin.')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
