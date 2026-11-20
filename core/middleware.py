"""
Middleware for workspace & account profile injection into every request.
Supports multi-workspace switching for WO Managers, multi-project Crew, and Platform Admin.
"""
from django.shortcuts import redirect
from django.urls import reverse
from core.models import Wedding, WeddingMembership, get_or_create_profile


# URLs that don't require an active workspace
EXEMPT_URLS = [
    '/login/',
    '/logout/',
    '/register/',
    '/onboarding/',
    '/join/',
    '/landing/',
    '/checkout/',
    '/webhooks/',
    '/password-reset/',
    '/account/',
    '/wo/',
    '/platform-admin/',
    '/switch-workspace/',
    '/admin/',
    '/static/',
    '/media/',
]

# URLs allowed for authenticated users whose plan_status != 'active' (Layer-2 onboarding gate)
UNPAID_ALLOWED_URLS = [
    '/onboarding/',
    '/checkout/',
    '/join/',
    '/logout/',
    '/account/',
    '/landing/',
    '/static/',
    '/media/',
]

FULL_PAGE_REDIRECT_URLS = [
    '/login/',
    '/register/',
    '/onboarding/',
    '/join/',
    '/checkout/',
    '/webhooks/',
    '/password-reset/',
    '/admin/',
]


class WorkspaceMiddleware:
    """
    Inject active Wedding workspace, wedding_role, and account_profile into request object.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.wedding = None
        request.wedding_role = None
        request.account_profile = None
        request.is_platform_admin = False
        request.user_memberships = []

        if request.user.is_authenticated:
            profile = get_or_create_profile(request.user)
            request.account_profile = profile
            request.is_platform_admin = profile.is_platform_admin

            active_wedding_id = request.session.get('active_wedding_id')
            path = request.path
            is_exempt = any(path.startswith(url) for url in EXEMPT_URLS)

            # Layer-2 Gate: authenticated users without active access cannot enter Layer-3 app routes
            if not request.is_platform_admin and profile.plan_status != 'active':
                if not any(path.startswith(url) for url in UNPAID_ALLOWED_URLS):
                    return redirect(reverse('core:onboarding'))

            if request.is_platform_admin:
                # Platform Admin can inspect any wedding via session active_wedding_id
                if active_wedding_id:
                    target = Wedding.objects.filter(pk=active_wedding_id).first()
                    if target:
                        request.wedding = target
                        request.wedding_role = 'admin'
                    else:
                        request.session.pop('active_wedding_id', None)
                if not request.wedding:
                    membership = (
                        WeddingMembership.objects
                        .filter(user=request.user)
                        .select_related('wedding')
                        .first()
                    )
                    if membership:
                        request.wedding = membership.wedding
                        request.wedding_role = 'admin'
                    elif not is_exempt:
                        return redirect(reverse('core:admin_console'))
            else:
                # Fetch once and cache on request so context_processors never re-queries
                memberships = list(
                    WeddingMembership.objects
                    .filter(user=request.user)
                    .select_related('wedding')
                    .order_by('-wedding__created_at')
                )
                request.user_memberships = memberships

                membership = None
                if active_wedding_id:
                    membership = next((m for m in memberships if m.wedding_id == active_wedding_id), None)
                    if not membership:
                        request.session.pop('active_wedding_id', None)
                if not membership and memberships:
                    membership = memberships[0]

                if membership:
                    request.wedding = membership.wedding
                    request.wedding_role = membership.role
                elif not is_exempt:
                    if profile.is_wo_account:
                        return redirect(reverse('core:wo_portal'))
                    return redirect(reverse('core:onboarding'))

        response = self.get_response(request)

        # Prevent browser Back-Forward Cache (bfcache) on authenticated pages
        # so pressing Back after logout cannot display stale private workspace screens.
        if (
            request.user.is_authenticated
            and not request.path.startswith('/static/')
            and not request.path.startswith('/media/')
        ):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        # If an HTMX request gets redirected to an auth/full-page route, use HX-Redirect
        if request.headers.get('HX-Request') == 'true':
            if response.status_code in (301, 302) and 'Location' in response:
                loc = response['Location']
                if any(exempt in loc for exempt in FULL_PAGE_REDIRECT_URLS):
                    from django.http import HttpResponse
                    htmx_redirect = HttpResponse(status=200)
                    htmx_redirect['HX-Redirect'] = loc
                    return htmx_redirect
            elif any(request.path.startswith(url) for url in FULL_PAGE_REDIRECT_URLS):
                response['HX-Retarget'] = 'body'
                response['HX-Reselect'] = 'body'
                response['HX-Reswap'] = 'innerHTML'

        return response
