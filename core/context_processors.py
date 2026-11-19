"""
Context processor to inject workspace data into all templates.
"""


def workspace_context(request):
    """Add wedding workspace and role to template context."""
    role = getattr(request, 'wedding_role', None)
    ctx = {
        'wedding': getattr(request, 'wedding', None),
        'wedding_role': role,
        'is_crew': role == 'crew',
        'is_owner': role == 'owner',
        'is_couple': role in ('owner', 'co_owner'),
    }
    if ctx['wedding']:
        ctx['days_remaining'] = ctx['wedding'].days_remaining
    return ctx
