"""
Vendor views: Vendor Comparator & Scoring Matrix, HTMX endpoints.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from core.decorators import owner_required
from vendors.models import VendorCandidate
from vendors.forms import VendorCandidateForm


@login_required
@owner_required
def vendor_compare(request):
    """Vendor Comparator & Scoring hub."""
    wedding = request.wedding
    vendors = VendorCandidate.objects.filter(wedding=wedding)

    # Group vendors by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        vendors = vendors.filter(category=category_filter)

    vendors_list = list(vendors)
    # Group for comparison view & sort by weighted_total_score descending
    vendor_groups = {}
    for v in vendors_list:
        cat = v.get_category_display()
        if cat not in vendor_groups:
            vendor_groups[cat] = []
        vendor_groups[cat].append(v)

    for cat in vendor_groups:
        vendor_groups[cat].sort(key=lambda x: x.weighted_total_score, reverse=True)

    first_vendor = vendors_list[0] if vendors_list else (
        VendorCandidate.objects.filter(wedding=wedding).first() if category_filter else None
    )
    weights = {
        'price': first_vendor.weight_price if first_vendor else 30,
        'quality': first_vendor.weight_quality if first_vendor else 30,
        'facility': first_vendor.weight_facility if first_vendor else 20,
        'reputation': first_vendor.weight_reputation if first_vendor else 20,
    }

    initial_data = {
        'weight_price': weights['price'],
        'weight_quality': weights['quality'],
        'weight_facility': weights['facility'],
        'weight_reputation': weights['reputation'],
    }
    if category_filter:
        initial_data['category'] = category_filter

    context = {
        'vendors': vendors_list,
        'vendor_groups': vendor_groups,
        'form': VendorCandidateForm(initial=initial_data),
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
            from core.tutorial import emit_tutorial_event
            return emit_tutorial_event(request, redirect('vendors:compare'), 'vendor_saved')
        except (ValueError, TypeError):
            pass
    return redirect('vendors:compare')


@login_required
@owner_required
def add_vendor(request):
    """HTMX endpoint: Add vendor candidate with inline drawer validation feedback."""
    if request.method == 'POST':
        form = VendorCandidateForm(request.POST)
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.wedding = request.wedding
            vendor.save()
            messages.success(request, f'Kandidat vendor "{vendor.name}" berhasil ditambahkan.')
            from core.tutorial import emit_tutorial_event
            return emit_tutorial_event(request, redirect('vendors:compare'), 'vendor_saved')
        if request.htmx:
            weights = {
                'price': int(request.POST.get('weight_price') or 30),
                'quality': int(request.POST.get('weight_quality') or 30),
                'facility': int(request.POST.get('weight_facility') or 20),
                'reputation': int(request.POST.get('weight_reputation') or 20),
            }
            response = render(request, 'vendors/partials/vendor_form.html', {
                'form': form,
                'is_edit': False,
                'weights': weights,
            })
            response['HX-Retarget'] = '#vendor-sheet-add'
            response['HX-Reswap'] = 'innerHTML'
            return response
        err_msgs = []
        for field, errs in form.errors.items():
            label = form.fields[field].label if field in form.fields else field
            err_msgs.append(f'{label}: {", ".join(errs)}')
        messages.error(request, 'Gagal menambah vendor. ' + ' | '.join(err_msgs))
    return redirect('vendors:compare')


@login_required
@owner_required
def update_vendor(request, pk):
    """HTMX endpoint: Update vendor candidate inside the slide-over sheet."""
    vendor = get_object_or_404(VendorCandidate, pk=pk, wedding=request.wedding)
    if request.GET.get('cancel') == '1':
        return render(request, 'vendors/partials/vendor_card.html', {'vendor': vendor})
    weights = {
        'price': vendor.weight_price,
        'quality': vendor.weight_quality,
        'facility': vendor.weight_facility,
        'reputation': vendor.weight_reputation,
    }
    if request.method == 'POST':
        form = VendorCandidateForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Perubahan vendor "{vendor.name}" berhasil disimpan.')
            return redirect('vendors:compare')
        response = render(request, 'vendors/partials/vendor_form.html', {
            'form': form,
            'vendor': vendor,
            'is_edit': True,
            'weights': weights,
        })
        response['HX-Retarget'] = '#vendor-sheet-edit'
        response['HX-Reswap'] = 'innerHTML'
        return response
    else:
        form = VendorCandidateForm(instance=vendor)
    return render(request, 'vendors/partials/vendor_form.html', {
        'form': form,
        'vendor': vendor,
        'is_edit': True,
        'weights': weights,
    })


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
    """HTMX endpoint: Select or cycle vendor status."""
    vendor = get_object_or_404(VendorCandidate, pk=pk, wedding=request.wedding)
    new_status = request.POST.get('status') or request.GET.get('status')
    valid_statuses = dict(VendorCandidate.STATUS_CHOICES)
    if new_status and new_status in valid_statuses:
        vendor.status = new_status
    else:
        cycle = ['shortlist', 'booked', 'rejected']
        idx = cycle.index(vendor.status) if vendor.status in cycle else 0
        vendor.status = cycle[(idx + 1) % len(cycle)]
    vendor.save(update_fields=['status'])
    if request.htmx:
        return render(request, 'vendors/partials/vendor_card.html', {'vendor': vendor})
    return redirect('vendors:compare')
