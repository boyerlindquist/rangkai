"""
Vendor views: Vendor Comparator & Scoring Matrix, HTMX endpoints.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from core.decorators import workspace_required, owner_required
from vendors.models import VendorCandidate
from vendors.forms import VendorCandidateForm


@login_required
@workspace_required
def vendor_compare(request):
    """Vendor Comparator & Scoring hub."""
    wedding = request.wedding
    vendors = VendorCandidate.objects.filter(wedding=wedding)

    # Group vendors by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        vendors = vendors.filter(category=category_filter)

    # Group for comparison view
    vendor_groups = {}
    for v in vendors:
        cat = v.get_category_display()
        if cat not in vendor_groups:
            vendor_groups[cat] = []
        vendor_groups[cat].append(v)

    context = {
        'vendors': vendors,
        'vendor_groups': vendor_groups,
        'form': VendorCandidateForm(),
        'category_filter': category_filter,
        'categories': VendorCandidate.CATEGORY_CHOICES,
    }
    return render(request, 'vendors/vendor_compare.html', context)


@login_required
@owner_required
def add_vendor(request):
    """HTMX endpoint: Add vendor candidate."""
    if request.method == 'POST':
        form = VendorCandidateForm(request.POST)
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.wedding = request.wedding
            vendor.save()
            return redirect('vendors:compare')
    return redirect('vendors:compare')


@login_required
@owner_required
def update_vendor(request, pk):
    """HTMX endpoint: Update vendor candidate."""
    vendor = get_object_or_404(VendorCandidate, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        form = VendorCandidateForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, 'vendors/partials/vendor_card.html', {'vendor': vendor})
            return redirect('vendors:compare')
    else:
        form = VendorCandidateForm(instance=vendor)
    return render(request, 'vendors/partials/vendor_form.html', {'form': form, 'vendor': vendor})


@login_required
@owner_required
def delete_vendor(request, pk):
    """HTMX endpoint: Delete vendor candidate."""
    vendor = get_object_or_404(VendorCandidate, pk=pk, wedding=request.wedding)
    vendor.delete()
    if request.htmx:
        vendors = VendorCandidate.objects.filter(wedding=request.wedding)
        return render(request, 'vendors/partials/vendor_cards.html', {'vendors': vendors})
    return redirect('vendors:compare')


@login_required
@owner_required
def update_vendor_status(request, pk):
    """HTMX endpoint: Toggle vendor status."""
    vendor = get_object_or_404(VendorCandidate, pk=pk, wedding=request.wedding)
    cycle = ['shortlist', 'booked', 'rejected']
    idx = cycle.index(vendor.status)
    vendor.status = cycle[(idx + 1) % len(cycle)]
    vendor.save()
    if request.htmx:
        return render(request, 'vendors/partials/vendor_card.html', {'vendor': vendor})
    return redirect('vendors:compare')
