"""
Context processor to inject workspace data into all templates.
"""


def workspace_context(request):
    """Add wedding workspace and role to template context."""
    ctx = {
        'wedding': getattr(request, 'wedding', None),
        'wedding_role': getattr(request, 'wedding_role', None),
    }
    if ctx['wedding']:
        ctx['days_remaining'] = ctx['wedding'].days_remaining
    return ctx
