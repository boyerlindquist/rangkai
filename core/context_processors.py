"""
Context processor to inject workspace, role, privacy flags, and switcher data into all templates.
"""
from core.models import Wedding, WeddingMembership


def workspace_context(request):
    """Add wedding workspace, role, permission flags, and switcher options to template context."""
    wedding = getattr(request, 'wedding', None)
    role = getattr(request, 'wedding_role', None)
    profile = getattr(request, 'account_profile', None)
    is_platform_admin = getattr(request, 'is_platform_admin', False)
    is_wo_account = bool(profile and profile.is_wo_account)

    is_couple = role in ('owner', 'co_owner')
    is_wo_manager = role == 'wo_manager'
    is_crew = role == 'crew'

    can_access_savings = role in ('owner', 'co_owner', 'admin')
    can_access_vendors = role in ('owner', 'co_owner', 'wo_manager', 'admin')
    can_access_finance = (
        role in ('owner', 'co_owner', 'admin')
        or (role == 'wo_manager' and bool(wedding and wedding.allow_wo_budget_access))
    )
    is_finance_locked_for_wo = (role == 'wo_manager' and not can_access_finance)

    user_weddings = []
    show_workspace_switcher = False
    is_htmx = request.headers.get('HX-Request') == 'true'
    if request.user.is_authenticated and not is_htmx:
        if is_platform_admin:
            user_weddings = list(Wedding.objects.all().order_by('-created_at')[:30])
            show_workspace_switcher = True
        else:
            # Reuse memberships already fetched in WorkspaceMiddleware (0 extra queries!)
            memberships = getattr(request, 'user_memberships', None)
            if memberships is None:
                memberships = list(
                    WeddingMembership.objects
                    .filter(user=request.user)
                    .select_related('wedding')
                    .order_by('-wedding__created_at')
                )
            if is_wo_account:
                user_weddings = [m.wedding for m in memberships]
                show_workspace_switcher = True
            elif len(memberships) > 1:
                user_weddings = [m.wedding for m in memberships]
                show_workspace_switcher = True

    ctx = {
        'wedding': wedding,
        'wedding_role': role,
        'account_profile': profile,
        'is_platform_admin': is_platform_admin,
        'is_wo_account': is_wo_account,
        'is_wo_manager': is_wo_manager,
        'is_crew': is_crew,
        'is_owner': role == 'owner',
        'is_couple': is_couple,
        'can_access_savings': can_access_savings,
        'can_access_vendors': can_access_vendors,
        'can_access_finance': can_access_finance,
        'is_finance_locked_for_wo': is_finance_locked_for_wo,
        'user_weddings': user_weddings,
        'show_workspace_switcher': show_workspace_switcher,
    }
    if wedding:
        ctx['days_remaining'] = wedding.days_remaining
    return ctx
