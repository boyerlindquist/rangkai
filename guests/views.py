import io
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from core.decorators import workspace_required, owner_required
from guests.models import Guest, CateringConfig
from guests.forms import GuestForm, CateringConfigForm


def _normalize_side(val):
    if not val:
        return 'groom_family'
    val_str = str(val).strip().lower()
    if any(k in val_str for k in ['keluarga pria', 'kel. pria', 'groom_family', 'groom family', 'cpp', 'keluarga cpp', 'kel. cpp', 'keluarga pengantin pria']):
        return 'groom_family'
    if any(k in val_str for k in ['keluarga wanita', 'kel. wanita', 'bride_family', 'bride family', 'cpw', 'keluarga cpw', 'kel. cpw', 'keluarga pengantin wanita']):
        return 'bride_family'
    if any(k in val_str for k in ['teman wanita', 'bride_friend', 'teman cpw', 'sahabat wanita']):
        return 'bride_friend'
    if any(k in val_str for k in ['teman pria', 'groom_friend', 'teman cpp', 'sahabat pria', 'teman']):
        return 'groom_friend'
    return 'groom_family'


def _normalize_category(val):
    if not val:
        return 'regular'
    val_str = str(val).strip().lower()
    if 'vvip' in val_str:
        return 'vvip'
    if 'vip' in val_str:
        return 'vip'
    return 'regular'


def _normalize_rsvp(val):
    if not val:
        return 'pending'
    val_str = str(val).strip().lower()
    if any(k in val_str for k in ['hadir', 'attending', 'yes', 'datang', 'ok']):
        return 'attending'
    if any(k in val_str for k in ['berhalangan', 'declined', 'tidak hadir', 'tidak', 'no', 'batal']):
        return 'declined'
    return 'pending'


def _normalize_pax(val):
    try:
        pax = int(float(str(val).strip()))
        return max(1, min(pax, 20))
    except (ValueError, TypeError):
        return 2


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
    search_query = request.GET.get('q', '').strip()

    if side_filter:
        guests = guests.filter(relation_side=side_filter)
    if category_filter:
        guests = guests.filter(category=category_filter)
    if rsvp_filter:
        guests = guests.filter(rsvp_status=rsvp_filter)
    if search_query:
        guests = guests.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

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
        'search_query': search_query,
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
            return redirect('guests:list')
    return redirect('guests:list')


@login_required
@owner_required
def bulk_add_guests(request):
    """HTMX endpoint: Save multi-row entries from Spreadsheet Mode."""
    if request.method == 'POST':
        names = request.POST.getlist('name[]')
        phones = request.POST.getlist('phone[]')
        sides = request.POST.getlist('relation_side[]')
        categories = request.POST.getlist('category[]')
        paxes = request.POST.getlist('pax_allocation[]')
        rsvps = request.POST.getlist('rsvp_status[]')
        notes_list = request.POST.getlist('notes[]')

        guests_to_create = []
        for i in range(len(names)):
            name = names[i].strip() if i < len(names) else ""
            if not name:
                continue
            phone = phones[i].strip() if i < len(phones) else ""
            side = sides[i] if i < len(sides) else 'groom_family'
            category = categories[i] if i < len(categories) else 'regular'
            pax = _normalize_pax(paxes[i]) if i < len(paxes) else 2
            rsvp = rsvps[i] if i < len(rsvps) else 'pending'
            note = notes_list[i].strip() if i < len(notes_list) else ""

            guests_to_create.append(Guest(
                wedding=request.wedding,
                name=name,
                phone=phone,
                relation_side=side,
                category=category,
                pax_allocation=pax,
                rsvp_status=rsvp,
                notes=note
            ))

        if guests_to_create:
            Guest.objects.bulk_create(guests_to_create)
            messages.success(request, f"Berhasil menambahkan {len(guests_to_create)} tamu dari Mode Spreadsheet!")
        else:
            messages.warning(request, "Tidak ada nama tamu yang diisi.")

    return redirect('guests:list')


@login_required
@workspace_required
def download_guest_template(request):
    """Download ready-to-fill Excel template for guest list."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Daftar Tamu"

    headers = [
        "Nama Tamu (Wajib)",
        "No. HP / WhatsApp",
        "Asal Relasi (Keluarga Pria / Keluarga Wanita / Teman Pria / Teman Wanita)",
        "Kategori (Reguler / VIP / VVIP)",
        "Jumlah Pax",
        "Status RSVP (Pending / Hadir / Berhalangan)",
        "Catatan"
    ]
    ws.append(headers)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0F2920", end_color="0F2920", fill_type="solid")
    
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Example rows
    examples = [
        ["Bpk. H. Ahmad Dahlan & Keluarga", "081234567890", "Keluarga Pria", "VIP", 4, "Hadir", "Om dari CPP"],
        ["dr. Rina Suryani, Sp.A", "081198765432", "Teman Wanita", "Reguler", 2, "Pending", "Teman Kuliah CPW"],
        ["Dimas Anggara & Partner", "085612345678", "Teman Pria", "Reguler", 2, "Pending", "Teman Kantor"],
        ["Ibu Siti Aminah", "081399887766", "Keluarga Wanita", "VVIP", 2, "Hadir", "Tante dari CPW"],
    ]
    for row in examples:
        ws.append(row)

    column_widths = [35, 20, 30, 20, 15, 22, 30]
    for i, col_letter in enumerate(["A", "B", "C", "D", "E", "F", "G"]):
        ws.column_dimensions[col_letter].width = column_widths[i]

    ws.row_dimensions[1].height = 28

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = 'attachment; filename="Template_Daftar_Tamu_Rangkai.xlsx"'
    return response


@login_required
@owner_required
def import_guests(request):
    """Import guests from uploaded Excel (.xlsx) or CSV file."""
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        filename = file.name.lower()
        guests_to_create = []

        try:
            if filename.endswith('.xlsx'):
                wb = openpyxl.load_workbook(file, data_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                if len(rows) > 1:
                    for row in rows[1:]:
                        if not row or not any(row):
                            continue
                        name = str(row[0]).strip() if row[0] is not None else ""
                        if not name or name.lower().startswith('nama tamu'):
                            continue
                        phone = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
                        if phone.endswith('.0'):
                            phone = phone[:-2]
                        side = _normalize_side(row[2] if len(row) > 2 else '')
                        category = _normalize_category(row[3] if len(row) > 3 else '')
                        pax = _normalize_pax(row[4] if len(row) > 4 else 2)
                        rsvp = _normalize_rsvp(row[5] if len(row) > 5 else 'pending')
                        notes = str(row[6]).strip() if len(row) > 6 and row[6] is not None else ""

                        guests_to_create.append(Guest(
                            wedding=request.wedding,
                            name=name,
                            phone=phone,
                            relation_side=side,
                            category=category,
                            pax_allocation=pax,
                            rsvp_status=rsvp,
                            notes=notes
                        ))

            elif filename.endswith('.csv'):
                decoded_file = file.read().decode('utf-8-sig', errors='ignore')
                reader = csv.reader(io.StringIO(decoded_file))
                rows = list(reader)
                if len(rows) > 1:
                    for row in rows[1:]:
                        if not row or not any(row):
                            continue
                        name = row[0].strip()
                        if not name or name.lower().startswith('nama tamu'):
                            continue
                        phone = row[1].strip() if len(row) > 1 else ""
                        side = _normalize_side(row[2] if len(row) > 2 else '')
                        category = _normalize_category(row[3] if len(row) > 3 else '')
                        pax = _normalize_pax(row[4] if len(row) > 4 else 2)
                        rsvp = _normalize_rsvp(row[5] if len(row) > 5 else 'pending')
                        notes = row[6].strip() if len(row) > 6 else ""

                        guests_to_create.append(Guest(
                            wedding=request.wedding,
                            name=name,
                            phone=phone,
                            relation_side=side,
                            category=category,
                            pax_allocation=pax,
                            rsvp_status=rsvp,
                            notes=notes
                        ))
            else:
                messages.error(request, "Format file tidak didukung. Harap unggah file .xlsx atau .csv.")
                return redirect('guests:list')

            if guests_to_create:
                Guest.objects.bulk_create(guests_to_create)
                messages.success(request, f"Berhasil mengimpor {len(guests_to_create)} tamu ke database!")
            else:
                messages.warning(request, "Tidak ada data tamu valid yang ditemukan dalam file.")

        except Exception as e:
            messages.error(request, f"Gagal memproses file: {str(e)}")

    return redirect('guests:list')


@login_required
@owner_required
def update_guest(request, pk):
    """HTMX endpoint: Update guest."""
    guest = get_object_or_404(Guest, pk=pk, wedding=request.wedding)
    if request.GET.get('cancel') == '1':
        return render(request, 'guests/partials/guest_row.html', {'guest': guest})
    if request.method == 'POST':
        form = GuestForm(request.POST, instance=guest)
        if form.is_valid():
            form.save()
            return redirect('guests:list')
        response = render(request, 'guests/partials/guest_form.html', {'form': form, 'guest': guest})
        response['HX-Retarget'] = f'#edit-guest-{guest.pk}'
        response['HX-Reselect'] = f'#edit-guest-{guest.pk}'
        response['HX-Reswap'] = 'outerHTML'
        return response
    else:
        form = GuestForm(instance=guest)
    return render(request, 'guests/partials/guest_form.html', {'form': form, 'guest': guest})


@login_required
@owner_required
def delete_guest(request, pk):
    """HTMX endpoint: Delete guest."""
    guest = get_object_or_404(Guest, pk=pk, wedding=request.wedding)
    guest.delete()
    return redirect('guests:list')


@login_required
@owner_required
def toggle_rsvp(request, pk):
    """HTMX endpoint: Quick toggle or select RSVP status."""
    guest = get_object_or_404(Guest, pk=pk, wedding=request.wedding)
    new_status = request.POST.get('rsvp_status') or request.GET.get('rsvp_status')
    if new_status and new_status in dict(Guest.RSVP_CHOICES):
        guest.rsvp_status = new_status
    else:
        cycle = ['pending', 'attending', 'declined']
        idx = cycle.index(guest.rsvp_status) if guest.rsvp_status in cycle else 0
        guest.rsvp_status = cycle[(idx + 1) % len(cycle)]
    guest.save(update_fields=['rsvp_status'])
    return redirect('guests:list')


@login_required
@owner_required
def toggle_checkin(request, pk):
    """HTMX endpoint: Quick toggle D-Day Check-In status."""
    guest = get_object_or_404(Guest, pk=pk, wedding=request.wedding)
    guest.checked_in = not guest.checked_in
    if guest.checked_in and guest.rsvp_status == 'pending':
        guest.rsvp_status = 'attending'
        guest.save(update_fields=['checked_in', 'rsvp_status'])
    else:
        guest.save(update_fields=['checked_in'])
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
    return redirect('guests:list')
