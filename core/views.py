"""
Core views: Dashboard, Auth (Register/Login/Logout), Join Workspace, Settings.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from core.models import Wedding, WeddingMembership
from core.forms import RegisterForm, LoginForm, JoinWorkspaceForm, WeddingSettingsForm
from core.decorators import workspace_required


DEFAULT_BUDGET_CATEGORIES = [
    {'name': 'Catering & F&B', 'icon': '<i data-lucide="utensils"></i>', 'allocation': {'foodie': 45, 'aesthetic': 30, 'balanced': 38}},
    {'name': 'Venue & Gedung', 'icon': '<i data-lucide="building"></i>', 'allocation': {'foodie': 10, 'aesthetic': 20, 'balanced': 12}},
    {'name': 'Dekorasi', 'icon': '<i data-lucide="sparkles"></i>', 'allocation': {'foodie': 10, 'aesthetic': 15, 'balanced': 10}},
    {'name': 'Attire & MUA', 'icon': '<i data-lucide="scissors"></i>', 'allocation': {'foodie': 10, 'aesthetic': 15, 'balanced': 12}},
    {'name': 'Dokumentasi', 'icon': '<i data-lucide="camera"></i>', 'allocation': {'foodie': 10, 'aesthetic': 10, 'balanced': 10}},
    {'name': 'Entertainment & MC', 'icon': '<i data-lucide="mic"></i>', 'allocation': {'foodie': 3, 'aesthetic': 3, 'balanced': 5}},
    {'name': 'Admin & Legalitas', 'icon': '<i data-lucide="file-text"></i>', 'allocation': {'foodie': 5, 'aesthetic': 3, 'balanced': 5}},
    {'name': 'Seserahan & Cincin', 'icon': '<i data-lucide="gem"></i>', 'allocation': {'foodie': 2, 'aesthetic': 2, 'balanced': 3}},
    {'name': 'Buffer / Darurat', 'icon': '<i data-lucide="shield"></i>', 'allocation': {'foodie': 5, 'aesthetic': 2, 'balanced': 5}},
]

DEFAULT_TASKS = [
    # Persiapan Awal
    {'phase': 'd360', 'category': 'other', 'title': 'Pertemuan keluarga (Perkenalan & Silaturahmi)', 'assignee': 'both', 'is_critical': True},
    {'phase': 'd360', 'category': 'rundown', 'title': 'Menentukan tanggal pernikahan', 'assignee': 'both', 'is_critical': True},
    {'phase': 'd360', 'category': 'other', 'title': 'Menentukan tema & konsep pernikahan', 'assignee': 'both'},
    {'phase': 'd360', 'category': 'rundown', 'title': 'Menentukan tanggal lamaran (jika ada)', 'assignee': 'both'},
    {'phase': 'd360', 'category': 'finance', 'title': 'Menentukan target total budget & skema split-bill', 'assignee': 'both', 'linked_tool': 'Top-Down Allocator', 'is_critical': True},
    {'phase': 'd360', 'category': 'guest', 'title': 'Menentukan estimasi jumlah tamu', 'assignee': 'both'},
    
    # Tempat, Dekorasi, Vendor Utama
    {'phase': 'd360', 'category': 'venue', 'title': 'Survey & booking venue (Akad & Resepsi)', 'assignee': 'both', 'linked_tool': 'Vendor Scoring', 'is_critical': True},
    {'phase': 'd360', 'category': 'vendor', 'title': 'Riset & shortlist vendor Catering', 'assignee': 'both', 'linked_tool': 'Vendor Scoring'},
    {'phase': 'd360', 'category': 'vendor', 'title': 'Riset & shortlist vendor Dekorasi', 'assignee': 'both', 'linked_tool': 'Vendor Scoring'},
    {'phase': 'd360', 'category': 'vendor', 'title': 'Riset & shortlist vendor MUA & Busana', 'assignee': 'bride', 'linked_tool': 'Vendor Scoring'},
    {'phase': 'd360', 'category': 'vendor', 'title': 'Riset & shortlist vendor Dokumentasi (Foto/Video)', 'assignee': 'both', 'linked_tool': 'Vendor Scoring'},
    
    # Administrasi Persiapan Pernikahan
    {'phase': 'd180', 'category': 'legal', 'title': 'Siapkan Surat Pengantar dari RT/RW', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Siapkan Fotocopy KTP & KK (CPP dan CPW)', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Siapkan Fotocopy Akta kelahiran & Ijazah (CPP dan CPW)', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Siapkan Pas Foto 3x2 latar biru 5 lembar (CPP dan CPW)', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Pengurusan berkas N1-N4 di Kelurahan & Numpang Nikah', 'assignee': 'both', 'is_critical': True},
    {'phase': 'd180', 'category': 'legal', 'title': 'Siapkan Fotocopy KTP Wali Nikah & 2 Orang Saksi', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Suntik TT / Keterangan Vaksin TT (CPW)', 'assignee': 'bride'},
    {'phase': 'd180', 'category': 'legal', 'title': 'Daftar nikah ke KUA', 'assignee': 'both', 'is_critical': True},
    {'phase': 'd180', 'category': 'legal', 'title': 'Mengikuti bimbingan pra-nikah', 'assignee': 'both'},

    # Mahar, Seserahan & Cincin
    {'phase': 'd180', 'category': 'other', 'title': 'Beli cincin couple / kawin', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'other', 'title': 'Pesan mahar & kotak cincin nikah', 'assignee': 'groom'},
    {'phase': 'd180', 'category': 'other', 'title': 'Beli & hias barang seserahan', 'assignee': 'both'},
    
    # Vendor Lanjutan
    {'phase': 'd180', 'category': 'vendor', 'title': 'Lock DP Katering, MUA, Dekor, dan Dokumentasi', 'assignee': 'both', 'linked_tool': 'Cash Flow Forecaster', 'is_critical': True},
    {'phase': 'd180', 'category': 'vendor', 'title': 'Pesan Baju pengantin akad & resepsi (CPP & CPW)', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'vendor', 'title': 'Fitting baju pengantin & seragam keluarga', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'vendor', 'title': 'Sesi prewedding foto/video', 'assignee': 'both'},
    
    # Undangan, Souvenir, & Tamu
    {'phase': 'd180', 'category': 'logistic', 'title': 'Pesan & cetak buku tamu', 'assignee': 'both'},
    {'phase': 'd180', 'category': 'logistic', 'title': 'Pesan Souvenir pernikahan', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'guest', 'title': 'Finalisasi database tamu & alokasi kuota keluarga', 'assignee': 'both', 'linked_tool': 'Quota Tug-of-War', 'is_critical': True},
    {'phase': 'd90', 'category': 'logistic', 'title': 'Desain & cetak undangan digital/fisik', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'logistic', 'title': 'Kirim undangan fisik & digital', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'logistic', 'title': 'Beli kain seragam keluarga & bridesmaid', 'assignee': 'bride', 'linked_tool': 'Yardage Calculator'},
    
    # Acara & Hiburan
    {'phase': 'd90', 'category': 'vendor', 'title': 'Booking MC, Hiburan (Band/Penyanyi) & Photobooth', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'rundown', 'title': 'Pesan jasa qori / tilawah (jika ada)', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'rundown', 'title': 'Tentukan petugas sambutan dari perwakilan keluarga/tokoh', 'assignee': 'both'},
    {'phase': 'd90', 'category': 'rundown', 'title': 'Persiapan & booking alat Acara Adat (jika ada)', 'assignee': 'family'},

    # Technical Meeting & Persiapan Mendekati Hari H
    {'phase': 'd90', 'category': 'vendor', 'title': 'Technical Meeting tahap 1 dengan semua vendor', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'fb', 'title': 'Finalisasi menu test food & fixasi rasio buffet/stall', 'assignee': 'both', 'linked_tool': 'Catering Simulator', 'is_critical': True},
    {'phase': 'd30', 'category': 'finance', 'title': 'Pelunasan seluruh vendor (H-7 to H-3)', 'assignee': 'both', 'linked_tool': 'Cash-Out Calendar', 'is_critical': True},
    {'phase': 'd30', 'category': 'guest', 'title': 'Final RSVP & konfirmasi kehadiran tamu', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'logistic', 'title': 'Packing logistik souvenir & seserahan', 'assignee': 'family'},
    
    # Panitia & Petugas Hari H
    {'phase': 'd30', 'category': 'rundown', 'title': 'Menyusun susunan panitia keluarga', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'rundown', 'title': 'Menunjuk pengiring pengantin wanita / bridesmaid', 'assignee': 'bride'},
    {'phase': 'd30', 'category': 'rundown', 'title': 'Menunjuk penjaga buku tamu & souvenir', 'assignee': 'family'},
    {'phase': 'd30', 'category': 'finance', 'title': 'Menunjuk penjaga & pemegang kunci kotak amplop', 'assignee': 'family', 'is_critical': True},
    {'phase': 'd30', 'category': 'fb', 'title': 'Menunjuk PIC penjaga makanan/prasmanan keluarga', 'assignee': 'family'},
    {'phase': 'd30', 'category': 'other', 'title': 'Koordinasi Tim Kebersihan & Keamanan (Parkir, dll)', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'logistic', 'title': 'Booking / atur Transportasi Calon Pengantin & Keluarga', 'assignee': 'both'},
    
    # Finalisasi
    {'phase': 'd30', 'category': 'rundown', 'title': 'Briefing / rapat panitia keluarga', 'assignee': 'both', 'is_critical': True},
    {'phase': 'd30', 'category': 'rundown', 'title': 'Final Technical Meeting (TM) & validasi rundown WO', 'assignee': 'both', 'linked_tool': 'Rundown Sanity', 'is_critical': True},
    {'phase': 'd30', 'category': 'logistic', 'title': 'Gladi bersih / rehearsal di venue', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'other', 'title': 'Booking & perawatan kuku (Nail art)', 'assignee': 'bride'},
    {'phase': 'd30', 'category': 'legal', 'title': 'Ajukan izin cuti menikah di tempat kerja', 'assignee': 'both'},
    {'phase': 'd30', 'category': 'other', 'title': 'Jaga kesehatan & konsumsi vitamin', 'assignee': 'both'},

    # Hari H & Pasca Acara
    {'phase': 'dday', 'category': 'asset', 'title': 'Logistik: pastikan semua barang dibawa ke venue', 'assignee': 'family', 'linked_tool': 'Asset Custodian', 'is_critical': True},
    {'phase': 'dday', 'category': 'asset', 'title': 'Serah terima barang berharga ke PIC', 'assignee': 'both', 'linked_tool': 'Asset Custodian', 'is_critical': True},
    {'phase': 'dday', 'category': 'post', 'title': 'Pengembalian kotak seserahan sewa & busana adat', 'assignee': 'family'},
    {'phase': 'dday', 'category': 'post', 'title': 'Rekap amplop / angpao & hitung total', 'assignee': 'both'},
]


def _create_default_data(wedding):
    """Populate default budget categories and task milestones for a new workspace."""
    from finances.models import BudgetCategory
    from operations.models import TaskMilestone
    from guests.models import CateringConfig

    style = wedding.budget_style or 'balanced'

    # Create budget categories
    for i, cat in enumerate(DEFAULT_BUDGET_CATEGORIES):
        BudgetCategory.objects.create(
            wedding=wedding,
            name=cat['name'],
            icon=cat['icon'],
            allocation_percentage=cat['allocation'].get(style, 0),
            sort_order=i,
        )

    # Create default task milestones
    for i, task in enumerate(DEFAULT_TASKS):
        TaskMilestone.objects.create(
            wedding=wedding,
            phase=task['phase'],
            category=task.get('category', 'other'),
            title=task['title'],
            assignee=task.get('assignee', 'both'),
            linked_tool=task.get('linked_tool', ''),
            is_critical=task.get('is_critical', False),
            sort_order=i,
        )

    # Create default catering config
    CateringConfig.objects.create(wedding=wedding)


def register_view(request):
    """User registration with auto workspace creation."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Create wedding workspace
            wedding = Wedding.objects.create(
                groom_name=form.cleaned_data['groom_name'],
                bride_name=form.cleaned_data['bride_name'],
                wedding_date=form.cleaned_data.get('wedding_date'),
            )

            # Create membership
            WeddingMembership.objects.create(
                user=user,
                wedding=wedding,
                role='owner',
            )

            # Populate default data
            _create_default_data(wedding)

            login(request, user)
            messages.success(request, f'Selamat datang, {user.username}! Workspace berhasil dibuat.')
            messages.info(request, f'Kode undangan pasangan: {wedding.invite_code}')
            return redirect('core:dashboard')
    else:
        form = RegisterForm()

    return render(request, 'core/register.html', {'form': form})


def login_view(request):
    """User login."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    next_url = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, f'Selamat datang kembali, {request.user.username}!')
            from django.utils.http import url_has_allowed_host_and_scheme
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('core:dashboard')
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    """User logout."""
    logout(request)
    messages.info(request, 'Berhasil logout.')
    return redirect('core:login')


@login_required
def join_workspace_view(request):
    """Join an existing workspace via invite code."""
    # If user already has a workspace, redirect to dashboard
    if WeddingMembership.objects.filter(user=request.user).exists():
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = JoinWorkspaceForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['invite_code'].upper()
            try:
                wedding = Wedding.objects.get(invite_code=code)
            except Wedding.DoesNotExist:
                form.add_error('invite_code', 'Kode undangan tidak ditemukan.')
            else:
                WeddingMembership.objects.create(
                    user=request.user,
                    wedding=wedding,
                    role='co_owner',
                )
                messages.success(request, f'Berhasil bergabung ke workspace {wedding}!')
                return redirect('core:dashboard')
    else:
        form = JoinWorkspaceForm()

    return render(request, 'core/join_workspace.html', {'form': form})


@login_required
@workspace_required
def dashboard_view(request):
    """Overview Hub with 4 KPI cards and active phase snapshot."""
    wedding = request.wedding

    # KPI 1: Days remaining
    days_remaining = wedding.days_remaining

    # KPI 2: Budget summary
    from finances.models import BudgetItem, BudgetCategory
    from vendors.models import VendorCandidate
    import json

    budget_agg = BudgetItem.objects.filter(wedding=wedding).aggregate(
        total_actual=Sum('actual_cost'),
        total_paid=Sum('paid_amount'),
    )
    total_actual = budget_agg['total_actual'] or 0
    total_paid = budget_agg['total_paid'] or 0
    budget_remaining = wedding.total_budget - total_actual

    # Sankey Data — 3 layers: Total Budget → Category → Item
    categories_with_items = BudgetCategory.objects.filter(wedding=wedding).prefetch_related('items')

    sankey_data = []
    seen_item_names = {}  # track name usage to avoid Google Sankey node collision

    for cat in categories_with_items:
        items_with_cost = [item for item in cat.items.all() if item.actual_cost and item.actual_cost > 0]
        cat_total = sum(float(item.actual_cost) for item in items_with_cost)

        if cat_total > 0:
            # Layer 1: Total Budget → Category
            sankey_data.append(['Total Budget', cat.name, cat_total])
            # Layer 2: Category → each Item
            for item in items_with_cost:
                # Ensure unique node name — append thin spaces for duplicates
                base_name = item.name
                count = seen_item_names.get(base_name, 0)
                item_node = base_name + ('\u200b' * count)  # zero-width space suffix
                seen_item_names[base_name] = count + 1
                sankey_data.append([cat.name, item_node, float(item.actual_cost)])

    if budget_remaining > 0:
        sankey_data.append(['Total Budget', 'Sisa Budget', float(budget_remaining)])

    sankey_data_json = json.dumps(sankey_data)

    # Booked Vendors
    booked_vendors = VendorCandidate.objects.filter(wedding=wedding, status='booked')

    # KPI 3: RSVP stats
    from guests.models import Guest
    guest_stats = Guest.objects.filter(wedding=wedding).aggregate(
        total_guests=Count('id'),
        attending=Count('id', filter=Q(rsvp_status='attending')),
        total_pax=Sum('pax_allocation'),
        attending_pax=Sum('pax_allocation', filter=Q(rsvp_status='attending')),
    )

    # KPI 4: Task progress
    from operations.models import TaskMilestone
    task_stats = TaskMilestone.objects.filter(wedding=wedding).aggregate(
        total=Count('id'),
        done=Count('id', filter=Q(status='done')),
        in_progress=Count('id', filter=Q(status='in_progress')),
    )
    task_total = task_stats['total'] or 1
    task_progress = round((task_stats['done'] / task_total) * 100)

    # Urgent items: payments overdue or due within the next 7 days
    from datetime import timedelta
    overdue_items = BudgetItem.objects.filter(
        wedding=wedding,
        due_date__lte=timezone.now().date() + timedelta(days=7),
    ).exclude(payment_status='settled').order_by('due_date')

    # Active phase tasks
    active_tasks = TaskMilestone.objects.filter(
        wedding=wedding,
        status__in=['todo', 'in_progress'],
    )[:10]

    context = {
        'days_remaining': days_remaining,
        'budget_remaining': budget_remaining,
        'total_actual': total_actual,
        'total_paid': total_paid,
        'sankey_data_json': sankey_data_json,
        'booked_vendors': booked_vendors,
        'guest_stats': guest_stats,
        'task_stats': task_stats,
        'task_progress': task_progress,
        'overdue_items': overdue_items,
        'active_tasks': active_tasks,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@workspace_required
def settings_view(request):
    """Edit wedding workspace settings."""
    wedding = request.wedding

    if request.method == 'POST':
        form = WeddingSettingsForm(request.POST, instance=wedding)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pengaturan berhasil disimpan.')
            if request.htmx:
                return render(request, 'core/partials/settings_form.html', {'form': form})
            return redirect('core:settings')
    else:
        form = WeddingSettingsForm(instance=wedding)

    return render(request, 'core/settings.html', {'form': form})

@login_required
@workspace_required
def guide_view(request):
    return render(request, 'core/guide.html')
