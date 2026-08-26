"""
Guest views: Guest List, Catering Simulator, HTMX endpoints.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q

from core.decorators import workspace_required, owner_required
from guests.models import Guest, CateringConfig
from guests.forms import GuestForm, CateringConfigForm


@login_required
@workspace_required
def guest_list(request):
    """Guest List & Catering Math hub."""
    wedding = request.wedding
    guests = Guest.objects.filter(wedding=wedding)

    # Filters
    side_filter = request.GET.get('side', '')
    category_filter = request.GET.get('category', '')
    rsvp_filter = request.GET.get('rsvp', '')

    if side_filter:
        guests = guests.filter(relation_side=side_filter)
    if category_filter:
        guests = guests.filter(category=category_filter)
    if rsvp_filter:
        guests = guests.filter(rsvp_status=rsvp_filter)

    # Stats
    all_guests = Guest.objects.filter(wedding=wedding)
    stats = all_guests.aggregate(
        total=Count('id'),
        total_pax=Sum('pax_allocation'),
        attending=Count('id', filter=Q(rsvp_status='attending')),
        attending_pax=Sum('pax_allocation', filter=Q(rsvp_status='attending')),
        checked_in=Count('id', filter=Q(checked_in=True)),
    )

    # Quota breakdown by side
    quota_breakdown = all_guests.values('relation_side').annotate(
        count=Count('id'),
        pax=Sum('pax_allocation'),
    ).order_by('relation_side')

    # Catering config
    config, _ = CateringConfig.objects.get_or_create(wedding=wedding)

    # Catering math (computed server-side for template display)
    total_invitations = stats['total'] or 0
    est_adult_pax = int(total_invitations * float(config.pax_multiplier) * float(config.attendance_rate) / 100)
    buffer_pax = int(est_adult_pax * (1 + float(config.vip_buffer_rate) / 100))
    buffet_portions = buffer_pax
    stall_total = buffer_pax * config.stall_portion_per_pax
    stall_per_variety = stall_total // max(config.stall_variety_count, 1)
    crew_meals = config.crew_count * 2

    context = {
        'guests': guests,
        'stats': stats,
        'quota_breakdown': quota_breakdown,
        'config': config,
        'catering': {
            'total_invitations': total_invitations,
            'est_adult_pax': est_adult_pax,
            'buffer_pax': buffer_pax,
            'buffet_portions': buffet_portions,
            'stall_total': stall_total,
            'stall_per_variety': stall_per_variety,
            'crew_meals': crew_meals,
            'akad_pax': config.akad_pax,
        },
        'form': GuestForm(),
        'config_form': CateringConfigForm(instance=config),
        'side_filter': side_filter,
        'category_filter': category_filter,
        'rsvp_filter': rsvp_filter,
    }
    return render(request, 'guests/guest_list.html', context)


@login_required
@owner_required
def add_guest(request):
    """HTMX endpoint: Add a new guest."""
    if request.method == 'POST':
        form = GuestForm(request.POST)
        if form.is_valid():
            guest = form.save(commit=False)
            guest.wedding = request.wedding
            guest.save()
            if request.htmx:
                guests = Guest.objects.filter(wedding=request.wedding)
                return render(request, 'guests/partials/guest_table.html', {'guests': guests})
            return redirect('guests:list')
    return redirect('guests:list')


@login_required
@owner_required
def update_guest(request, pk):
    """HTMX endpoint: Update guest."""
    guest = get_object_or_404(Guest, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        form = GuestForm(request.POST, instance=guest)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, 'guests/partials/guest_row.html', {'guest': guest})
            return redirect('guests:list')
    else:
        form = GuestForm(instance=guest)
    return render(request, 'guests/partials/guest_form.html', {'form': form, 'guest': guest})


@login_required
@owner_required
def delete_guest(request, pk):
    """HTMX endpoint: Delete guest."""
    guest = get_object_or_404(Guest, pk=pk, wedding=request.wedding)
    guest.delete()
    if request.htmx:
        guests = Guest.objects.filter(wedding=request.wedding)
        return render(request, 'guests/partials/guest_table.html', {'guests': guests})
    return redirect('guests:list')


@login_required
@owner_required
def toggle_rsvp(request, pk):
    """HTMX endpoint: Quick toggle RSVP status."""
    guest = get_object_or_404(Guest, pk=pk, wedding=request.wedding)
    cycle = ['pending', 'attending', 'declined']
    idx = cycle.index(guest.rsvp_status)
    guest.rsvp_status = cycle[(idx + 1) % len(cycle)]
    guest.save(update_fields=['rsvp_status'])
    if request.htmx:
        return render(request, 'guests/partials/guest_row.html', {'guest': guest})
    return redirect('guests:list')


@login_required
@owner_required
def update_catering_config(request):
    """HTMX endpoint: Update catering config."""
    config, _ = CateringConfig.objects.get_or_create(wedding=request.wedding)
    if request.method == 'POST':
        form = CateringConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, 'guests/partials/catering_summary.html', {'config': config})
            return redirect('guests:list')
    return redirect('guests:list')
