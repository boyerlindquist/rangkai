"""
Middleware for workspace injection into every request.
"""
from django.shortcuts import redirect
from django.urls import reverse
from core.models import WeddingMembership


# URLs that don't require a workspace
EXEMPT_URLS = [
    '/login/',
    '/register/',
    '/join/',
    '/admin/',
]


class WorkspaceMiddleware:
    """
    Inject active Wedding workspace into request object.
    Redirects authenticated users without a workspace to join/create one.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.wedding = None

        if request.user.is_authenticated:
            membership = (
                WeddingMembership.objects
                .filter(user=request.user)
                .select_related('wedding')
                .first()
            )
            if membership:
                request.wedding = membership.wedding
                request.wedding_role = membership.role
            else:
                request.wedding_role = None
                # Redirect to join/create workspace if not on exempt URL
                path = request.path
                if not any(path.startswith(url) for url in EXEMPT_URLS):
                    return redirect(reverse('core:join_workspace'))

        response = self.get_response(request)
        return response
