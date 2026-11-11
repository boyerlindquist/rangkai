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

    # Group for comparison view & sort by weighted_total_score descending
    vendor_groups = {}
    for v in vendors:
        cat = v.get_category_display()
        if cat not in vendor_groups:
            vendor_groups[cat] = []
        vendor_groups[cat].append(v)

    for cat in vendor_groups:
        vendor_groups[cat].sort(key=lambda x: x.weighted_total_score, reverse=True)

    first_vendor = VendorCandidate.objects.filter(wedding=wedding).first()
    weights = {
        'price': first_vendor.weight_price if first_vendor else 30,
        'quality': first_vendor.weight_quality if first_vendor else 30,
        'facility': first_vendor.weight_facility if first_vendor else 20,
        'reputation': first_vendor.weight_reputation if first_vendor else 20,
    }

    context = {
        'vendors': vendors,
        'vendor_groups': vendor_groups,
        'form': VendorCandidateForm(initial={
            'weight_price': weights['price'],
            'weight_quality': weights['quality'],
            'weight_facility': weights['facility'],
            'weight_reputation': weights['reputation'],
        }),
        'weights': weights,
        'category_filter': category_filter,
        'categories': VendorCandidate.CATEGORY_CHOICES,
    }
    return render(request, 'vendors/vendor_compare.html', context)


@login_required
@owner_required
def update_vendor_weights(request):
    """Update scoring weights across all vendor candidates in this workspace."""
    if request.method == 'POST':
        try:
            w_price = max(0, min(100, int(request.POST.get('weight_price', 30))))
            w_quality = max(0, min(100, int(request.POST.get('weight_quality', 30))))
            w_facility = max(0, min(100, int(request.POST.get('weight_facility', 20))))
            w_reputation = max(0, min(100, int(request.POST.get('weight_reputation', 20))))
            VendorCandidate.objects.filter(wedding=request.wedding).update(
                weight_price=w_price,
                weight_quality=w_quality,
                weight_facility=w_facility,
                weight_reputation=w_reputation,
            )
        except (ValueError, TypeError):
            pass
    return redirect('vendors:compare')


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
    if request.GET.get('cancel') == '1':
        return render(request, 'vendors/partials/vendor_card.html', {'vendor': vendor})
    if request.method == 'POST':
        form = VendorCandidateForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            return redirect('vendors:compare')
        response = render(request, 'vendors/partials/vendor_form.html', {'form': form, 'vendor': vendor})
        response['HX-Retarget'] = f'#edit-vendor-{vendor.pk}'
        response['HX-Reselect'] = f'#edit-vendor-{vendor.pk}'
        response['HX-Reswap'] = 'outerHTML'
        return response
    else:
        form = VendorCandidateForm(instance=vendor)
    return render(request, 'vendors/partials/vendor_form.html', {'form': form, 'vendor': vendor})


@login_required
@owner_required
def delete_vendor(request, pk):
    """HTMX endpoint: Delete vendor candidate."""
    vendor = get_object_or_404(VendorCandidate, pk=pk, wedding=request.wedding)
    vendor.delete()
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
