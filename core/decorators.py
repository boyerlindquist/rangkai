"""
Decorators for workspace access control.
"""
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse


def workspace_required(view_func):
    """Ensure user has an active wedding workspace."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.wedding:
            return redirect(reverse('core:join_workspace'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def owner_required(view_func):
    """Ensure user is an owner or co-owner (not crew)."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.wedding:
            return redirect(reverse('core:join_workspace'))
        if request.wedding_role == 'crew':
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('Akses terbatas untuk peran Crew.')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
