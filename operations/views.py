"""
Operations views: Checklist, Rundown, Asset Custodian, Fabric Calculator.
"""
import json
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from collections import defaultdict

from core.decorators import workspace_required, owner_required
from operations.models import TimelinePhase, TaskMilestone, RundownEvent, AssetCustodian, FabricEntry
from operations.forms import TaskMilestoneForm, RundownEventForm, AssetCustodianForm, FabricEntryForm


# ============================================================
# CHECKLIST PRESETS & SMART GUIDE CATALOG
# ============================================================

TIMELINE_PRESETS = {
    'standard': {
        'name': 'Standar 1 Tahun (Default)',
        'desc': '5 fase berbasis H-minus (D-360 s/d D-Day), cocok untuk persiapan 6–12 bulan.',
        'phases': [
            ('d360', 'Fase 1: D-360 s/d D-180'),
            ('d180', 'Fase 2: D-180 s/d D-90'),
            ('d90', 'Fase 3: D-90 s/d D-30'),
            ('d30', 'Fase 4: D-30 s/d D-7'),
            ('dday', 'Fase 5: D-Day & H+1'),
        ],
    },
    'express': {
        'name': 'Persiapan Express (< 6 Bulan)',
        'desc': '4 tahapan ringkas & padat untuk persiapan cepat 2–5 bulan.',
        'phases': [
            ('d360', 'Tahap 1: Fondasi, Budget & Venue'),
            ('d180', 'Tahap 2: Vendor Utama, Busana & KUA'),
            ('d30', 'Tahap 3: Undangan, RSVP & Technical Meeting'),
            ('dday', 'Tahap 4: Minggu Terakhir & Hari-H'),
        ],
    },
    'event_based': {
        'name': 'Berbasis Rangkaian Acara',
        'desc': '5 tahapan berdasarkan prosesi acara (Lamaran ➔ Vendor ➔ KUA ➔ Pra-Acara ➔ Hari-H).',
        'phases': [
            ('d360', '1. Lamaran, Keluarga & Anggaran'),
            ('d180', '2. Venue, Katering & Vendor Utama'),
            ('d90', '3. Berkas KUA, Cincin & Undangan'),
            ('d30', '4. Pengajian, Siraman & Gladi Bersih'),
            ('dday', '5. Akad Nikah, Resepsi & Pasca-Acara'),
        ],
    },
}

TASK_GUIDE_CATALOG = [
    {
        'key': 'foundation',
        'title': 'Keluarga, Lamaran & Anggaran Awal',
        'icon': 'heart-handshake',
        'desc': 'Kesepakatan awal antar keluarga, tanggal acara, dan pagu anggaran.',
        'items': [
            {'title': 'Pertemuan keluarga (Perkenalan & Silaturahmi)', 'category': 'other', 'assignee': 'both', 'is_critical': True},
            {'title': 'Menentukan tanggal pernikahan', 'category': 'rundown', 'assignee': 'both', 'is_critical': True},
            {'title': 'Menentukan tema & konsep pernikahan', 'category': 'other', 'assignee': 'both', 'is_critical': False},
            {'title': 'Menentukan tanggal lamaran (jika ada)', 'category': 'rundown', 'assignee': 'both', 'is_critical': False},
            {'title': 'Menentukan target total budget & skema split-bill', 'category': 'finance', 'assignee': 'both', 'is_critical': True, 'linked_tool': 'Top-Down Allocator'},
            {'title': 'Menentukan estimasi jumlah tamu', 'category': 'guest', 'assignee': 'both', 'is_critical': False},
        ],
    },
    {
        'key': 'venue_vendor',
        'title': 'Venue, Katering & Vendor Utama',
        'icon': 'building-2',
        'desc': 'Survey tempat, seleksi vendor utama, kunci DP, dan fitting busana.',
        'items': [
            {'title': 'Survey & booking venue (Akad & Resepsi)', 'category': 'venue', 'assignee': 'both', 'is_critical': True, 'linked_tool': 'Vendor Scoring'},
            {'title': 'Riset & shortlist vendor Catering', 'category': 'vendor', 'assignee': 'both', 'is_critical': False, 'linked_tool': 'Vendor Scoring'},
            {'title': 'Riset & shortlist vendor Dekorasi', 'category': 'vendor', 'assignee': 'both', 'is_critical': False, 'linked_tool': 'Vendor Scoring'},
            {'title': 'Riset & shortlist vendor MUA & Busana', 'category': 'vendor', 'assignee': 'bride', 'is_critical': False, 'linked_tool': 'Vendor Scoring'},
            {'title': 'Riset & shortlist vendor Dokumentasi (Foto/Video)', 'category': 'vendor', 'assignee': 'both', 'is_critical': False, 'linked_tool': 'Vendor Scoring'},
            {'title': 'Lock DP Katering, MUA, Dekor, dan Dokumentasi', 'category': 'vendor', 'assignee': 'both', 'is_critical': True, 'linked_tool': 'Cash Flow Forecaster'},
            {'title': 'Pesan Baju pengantin akad & resepsi (CPP & CPW)', 'category': 'vendor', 'assignee': 'both', 'is_critical': False},
            {'title': 'Fitting baju pengantin & seragam keluarga', 'category': 'vendor', 'assignee': 'both', 'is_critical': False},
            {'title': 'Sesi prewedding foto/video', 'category': 'vendor', 'assignee': 'both', 'is_critical': False},
            {'title': 'Booking MC, Hiburan (Band/Penyanyi) & Photobooth', 'category': 'vendor', 'assignee': 'both', 'is_critical': False},
        ],
    },
    {
        'key': 'legal_kua',
        'title': 'Legalitas & Berkas KUA / Sipil',
        'icon': 'file-check-2',
        'desc': 'Dokumen administrasi pernikahan agar pendaftaran KUA/Catatan Sipil lancar.',
        'items': [
            {'title': 'Siapkan Surat Pengantar dari RT/RW', 'category': 'legal', 'assignee': 'both', 'is_critical': False},
            {'title': 'Siapkan Fotocopy KTP & KK (CPP dan CPW)', 'category': 'legal', 'assignee': 'both', 'is_critical': False},
            {'title': 'Siapkan Fotocopy Akta kelahiran & Ijazah (CPP dan CPW)', 'category': 'legal', 'assignee': 'both', 'is_critical': False},
            {'title': 'Siapkan Pas Foto 3x2 latar biru 5 lembar (CPP dan CPW)', 'category': 'legal', 'assignee': 'both', 'is_critical': False},
            {'title': 'Pengurusan berkas N1-N4 di Kelurahan & Numpang Nikah', 'category': 'legal', 'assignee': 'both', 'is_critical': True},
            {'title': 'Siapkan Fotocopy KTP Wali Nikah & 2 Orang Saksi', 'category': 'legal', 'assignee': 'both', 'is_critical': False},
            {'title': 'Suntik TT / Keterangan Vaksin TT (CPW)', 'category': 'legal', 'assignee': 'bride', 'is_critical': False},
            {'title': 'Daftar nikah ke KUA', 'category': 'legal', 'assignee': 'both', 'is_critical': True},
            {'title': 'Mengikuti bimbingan pra-nikah', 'category': 'legal', 'assignee': 'both', 'is_critical': False},
            {'title': 'Ajukan izin cuti menikah di tempat kerja', 'category': 'legal', 'assignee': 'both', 'is_critical': False},
        ],
    },
    {
        'key': 'mahar_seserahan',
        'title': 'Mahar, Cincin & Seserahan',
        'icon': 'gem',
        'desc': 'Persiapan cincin kawin, mahar pernikahan, dan hantaran/seserahan.',
        'items': [
            {'title': 'Beli cincin couple / kawin', 'category': 'other', 'assignee': 'both', 'is_critical': True},
            {'title': 'Pesan mahar & kotak cincin nikah', 'category': 'other', 'assignee': 'groom', 'is_critical': True},
            {'title': 'Beli & hias barang seserahan', 'category': 'other', 'assignee': 'both', 'is_critical': False},
            {'title': 'Packing logistik souvenir & seserahan', 'category': 'logistic', 'assignee': 'family', 'is_critical': False},
        ],
    },
    {
        'key': 'guest_invitation',
        'title': 'Tamu, Undangan, Seragam & Souvenir',
        'icon': 'users',
        'desc': 'Daftar tamu, kuota undangan, kain seragam keluarga, dan suvenir.',
        'items': [
            {'title': 'Finalisasi database tamu & alokasi kuota keluarga', 'category': 'guest', 'assignee': 'both', 'is_critical': True, 'linked_tool': 'Quota Tug-of-War'},
            {'title': 'Desain & cetak undangan digital/fisik', 'category': 'logistic', 'assignee': 'both', 'is_critical': False},
            {'title': 'Kirim undangan fisik & digital', 'category': 'logistic', 'assignee': 'both', 'is_critical': False},
            {'title': 'Final RSVP & konfirmasi kehadiran tamu', 'category': 'guest', 'assignee': 'both', 'is_critical': False},
            {'title': 'Beli kain seragam keluarga & bridesmaid', 'category': 'logistic', 'assignee': 'bride', 'is_critical': False, 'linked_tool': 'Yardage Calculator'},
            {'title': 'Pesan & cetak buku tamu', 'category': 'logistic', 'assignee': 'both', 'is_critical': False},
            {'title': 'Pesan Souvenir pernikahan', 'category': 'logistic', 'assignee': 'both', 'is_critical': False},
        ],
    },
    {
        'key': 'technical_h30',
        'title': 'Teknis, Panitia & Mendekati Hari-H',
        'icon': 'clipboard-check',
        'desc': 'Technical meeting vendor, pelunasan, pembagian PIC panitia keluarga, dan gladi bersih.',
        'items': [
            {'title': 'Technical Meeting tahap 1 dengan semua vendor', 'category': 'vendor', 'assignee': 'both', 'is_critical': False},
            {'title': 'Finalisasi menu test food & fixasi rasio buffet/stall', 'category': 'fb', 'assignee': 'both', 'is_critical': True, 'linked_tool': 'Catering Simulator'},
            {'title': 'Pelunasan seluruh vendor (H-7 to H-3)', 'category': 'finance', 'assignee': 'both', 'is_critical': True, 'linked_tool': 'Cash-Out Calendar'},
            {'title': 'Menyusun susunan panitia keluarga', 'category': 'rundown', 'assignee': 'both', 'is_critical': False},
            {'title': 'Menunjuk penjaga & pemegang kunci kotak amplop', 'category': 'finance', 'assignee': 'family', 'is_critical': True},
            {'title': 'Menunjuk PIC penjaga makanan/prasmanan keluarga', 'category': 'fb', 'assignee': 'family', 'is_critical': False},
            {'title': 'Briefing / rapat panitia keluarga', 'category': 'rundown', 'assignee': 'both', 'is_critical': True},
            {'title': 'Final Technical Meeting (TM) & validasi rundown WO', 'category': 'rundown', 'assignee': 'both', 'is_critical': True, 'linked_tool': 'Rundown Sanity'},
            {'title': 'Gladi bersih / rehearsal di venue', 'category': 'logistic', 'assignee': 'both', 'is_critical': False},
        ],
    },
    {
        'key': 'dday_post',
        'title': 'Logistik Hari-H & Pasca-Acara',
        'icon': 'sparkles',
        'desc': 'Pengawalan barang penting saat Hari-H dan penyelesaian pasca-acara.',
        'items': [
            {'title': 'Logistik: pastikan semua barang dibawa ke venue', 'category': 'asset', 'assignee': 'family', 'is_critical': True, 'linked_tool': 'Asset Custodian'},
            {'title': 'Serah terima barang berharga ke PIC', 'category': 'asset', 'assignee': 'both', 'is_critical': True, 'linked_tool': 'Asset Custodian'},
            {'title': 'Pengembalian kotak seserahan sewa & busana adat', 'category': 'post', 'assignee': 'family', 'is_critical': False},
            {'title': 'Rekap amplop / angpao & hitung total', 'category': 'post', 'assignee': 'both', 'is_critical': False},
        ],
    },
]


def _ensure_wedding_phases(wedding):
    """Ensure Wedding has TimelinePhase rows; seed from default 5 phases if empty."""
    existing = list(TimelinePhase.objects.filter(wedding=wedding).order_by('sort_order', 'id'))
    if existing:
        # Also make sure any orphan task phase keys exist as TimelinePhase
        existing_keys = {p.key for p in existing}
        orphan_keys = (
            TaskMilestone.objects.filter(wedding=wedding)
            .exclude(phase__in=existing_keys)
            .values_list('phase', flat=True)
            .distinct()
        )
        default_map = dict(TaskMilestone.PHASE_CHOICES)
        max_order = max((p.sort_order for p in existing), default=0)
        for o_key in orphan_keys:
            if o_key:
                max_order += 1
                p = TimelinePhase.objects.create(
                    wedding=wedding,
                    key=o_key,
                    label=default_map.get(o_key, o_key),
                    sort_order=max_order,
                )
                existing.append(p)
        return existing

    # Seed the 5 standard phases
    seeded = []
    for idx, (p_key, p_label) in enumerate(TaskMilestone.PHASE_CHOICES):
        seeded.append(
            TimelinePhase.objects.create(
                wedding=wedding,
                key=p_key,
                label=p_label,
                sort_order=idx,
            )
        )
    return seeded


# ============================================================
# CHECKLIST VIEWS (Route: /checklist/)
# ============================================================

def _build_checklist_context(wedding, assignee_filter=''):
    """Compute grouped tasks, dynamic phases, progress, and smart task guide for Checklist."""
    phase_objs = _ensure_wedding_phases(wedding)
    phases = [(p.key, p.label) for p in phase_objs]
    phase_order = [p.key for p in phase_objs]

    tasks = TaskMilestone.objects.filter(wedding=wedding)
    if assignee_filter:
        tasks = tasks.filter(assignee=assignee_filter)

    days_remaining = wedding.days_remaining

    # Determine active phase:
    # 1. Check if user manually set an active override phase
    override_phase = next((p for p in phase_objs if p.is_active_override), None)
    current_phase_key = None
    current_phase_idx = -1

    if override_phase:
        current_phase_key = override_phase.key
        current_phase_idx = phase_order.index(current_phase_key)
    elif days_remaining is not None and phase_order:
        # If standard keys exist, map by days_remaining; otherwise map proportionally or first incomplete phase
        if days_remaining > 180 and 'd360' in phase_order:
            current_phase_key = 'd360'
        elif days_remaining >= 90 and 'd180' in phase_order:
            current_phase_key = 'd180'
        elif days_remaining >= 30 and 'd90' in phase_order:
            current_phase_key = 'd90'
        elif days_remaining >= 7 and 'd30' in phase_order:
            current_phase_key = 'd30'
        elif 'dday' in phase_order and days_remaining < 7:
            current_phase_key = 'dday'
        else:
            # Custom phases: pick the first phase that isn't 100% done, or the first phase
            current_phase_key = phase_order[0]
            for p_key in phase_order:
                p_total = tasks.filter(phase=p_key).count()
                p_done = tasks.filter(phase=p_key, status='done').count()
                if p_total == 0 or p_done < p_total:
                    current_phase_key = p_key
                    break
        current_phase_idx = phase_order.index(current_phase_key)
    elif phase_order:
        current_phase_key = phase_order[0]
        current_phase_idx = 0

    grouped_tasks = {}
    total_overdue_tasks = 0
    all_overdue_tasks = []

    for phase_idx, p_obj in enumerate(phase_objs):
        phase_key = p_obj.key
        phase_label = p_obj.label
        phase_tasks = tasks.filter(phase=phase_key)
        total = phase_tasks.count()
        done = phase_tasks.filter(status='done').count()
        progress = round((done / total) * 100) if total > 0 else 0

        is_current = (phase_key == current_phase_key)
        is_past = (current_phase_idx != -1 and phase_idx < current_phase_idx)
        is_upcoming = (current_phase_idx != -1 and phase_idx > current_phase_idx)

        overdue_tasks_in_phase = []
        if is_past:
            overdue_tasks_in_phase = [t for t in phase_tasks if t.status != 'done']
            total_overdue_tasks += len(overdue_tasks_in_phase)
            all_overdue_tasks.extend(overdue_tasks_in_phase)

        annotated_tasks = []
        for t in phase_tasks:
            t_is_overdue = (is_past and t.status != 'done')
            setattr(t, 'is_overdue', t_is_overdue)
            annotated_tasks.append(t)

        grouped_tasks[phase_key] = {
            'key': phase_key,
            'label': phase_label,
            'is_active_override': p_obj.is_active_override,
            'tasks': annotated_tasks,
            'total': total,
            'done': done,
            'progress': progress,
            'is_current': is_current,
            'is_past': is_past,
            'is_upcoming': is_upcoming,
            'overdue_count': len(overdue_tasks_in_phase),
            'phase_idx': phase_idx,
            'step_num': phase_idx + 1,
        }

    all_tasks = TaskMilestone.objects.filter(wedding=wedding)
    total = all_tasks.count()
    done = all_tasks.filter(status='done').count()
    overall_progress = round((done / max(total, 1)) * 100)

    # Annotate Smart Guide Catalog with whether each task title is already in user's checklist
    existing_titles_lower = {t.lower().strip() for t in all_tasks.values_list('title', flat=True)}
    guide_catalog = []
    for topic in TASK_GUIDE_CATALOG:
        annotated_items = []
        added_count = 0
        for idx, item in enumerate(topic['items']):
            is_added = item['title'].lower().strip() in existing_titles_lower
            if is_added:
                added_count += 1
            annotated_items.append({
                **item,
                'idx': idx,
                'already_added': is_added,
            })
        guide_catalog.append({
            **topic,
            'items': annotated_items,
            'added_count': added_count,
            'total_count': len(annotated_items),
        })

    return {
        'grouped_tasks': grouped_tasks,
        'phases': phases,
        'phase_keys_json': json.dumps(phase_order),
        'phase_objs': phase_objs,
        'phase_count': len(phase_objs),
        'overall_progress': overall_progress,
        'total_tasks': total,
        'done_tasks': done,
        'assignee_filter': assignee_filter,
        'task_form': TaskMilestoneForm(wedding=wedding),
        'days_remaining': days_remaining,
        'current_phase_key': current_phase_key,
        'current_phase_label': dict(phases).get(current_phase_key) if current_phase_key else None,
        'total_overdue_tasks': total_overdue_tasks,
        'all_overdue_tasks': all_overdue_tasks,
        'guide_catalog': guide_catalog,
        'timeline_presets': TIMELINE_PRESETS,
    }


def _annotate_single_task(task, ctx):
    """Attach is_overdue flag to a single TaskMilestone instance."""
    phase_data = ctx['grouped_tasks'].get(task.phase)
    is_past = phase_data['is_past'] if phase_data else False
    setattr(task, 'is_overdue', is_past and task.status != 'done')
    return task


@login_required
@workspace_required
def checklist_view(request):
    """Phased Checklist hub with smart active phase detection and overdue catch-up tracking."""
    assignee_filter = request.GET.get('assignee', '')
    context = _build_checklist_context(request.wedding, assignee_filter=assignee_filter)
    return render(request, 'operations/checklist.html', context)


@login_required
@owner_required
def toggle_task_status(request, pk):
    """HTMX endpoint: 1-click toggle (todo <-> done) or select/cycle status."""
    task = get_object_or_404(TaskMilestone, pk=pk, wedding=request.wedding)
    new_status = request.POST.get('status') or request.GET.get('status')
    if new_status and new_status in dict(TaskMilestone.STATUS_CHOICES):
        task.status = new_status
    elif request.GET.get('mode') == 'cycle':
        cycle = ['todo', 'in_progress', 'done']
        idx = cycle.index(task.status) if task.status in cycle else 0
        task.status = cycle[(idx + 1) % len(cycle)]
    else:
        task.status = 'done' if task.status != 'done' else 'todo'
    task.save(update_fields=['status'])
    if request.GET.get('from') == 'dashboard':
        return redirect('core:dashboard')
    if request.htmx:
        ctx = _build_checklist_context(request.wedding)
        ctx['task'] = _annotate_single_task(task, ctx)
        return render(request, 'operations/partials/task_item_with_oob.html', ctx)
    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def add_task(request):
    """HTMX endpoint: Add custom task."""
    if request.method == 'POST':
        form = TaskMilestoneForm(request.POST, wedding=request.wedding)
        if form.is_valid():
            task = form.save(commit=False)
            task.wedding = request.wedding
            task.is_custom = True
            task.save()
            if request.htmx:
                ctx = _build_checklist_context(request.wedding)
                ctx['task'] = None
                ctx['oob_phase_list_key'] = task.phase
                ctx['oob_guide_update'] = True
                return render(request, 'operations/partials/task_item_with_oob.html', ctx)
    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def add_guide_task(request):
    """Add a single recommended task or an entire topic from the Smart Task Guide into the selected phase."""
    if request.method == 'POST':
        wedding = request.wedding
        phase_objs = _ensure_wedding_phases(wedding)
        valid_phase_keys = {p.key for p in phase_objs}
        target_phase = request.POST.get('phase', '')
        if target_phase not in valid_phase_keys:
            target_phase = phase_objs[0].key if phase_objs else 'd360'

        topic_key = request.POST.get('topic_key', '')
        item_idx = request.POST.get('item_idx', '')

        topic = next((t for t in TASK_GUIDE_CATALOG if t['key'] == topic_key), None)
        if topic:
            existing_titles = {
                t.lower().strip()
                for t in TaskMilestone.objects.filter(wedding=wedding).values_list('title', flat=True)
            }
            max_order = TaskMilestone.objects.filter(wedding=wedding, phase=target_phase).count()
            if item_idx == 'all':
                for item in topic['items']:
                    if item['title'].lower().strip() not in existing_titles:
                        max_order += 1
                        TaskMilestone.objects.create(
                            wedding=wedding,
                            phase=target_phase,
                            title=item['title'],
                            category=item.get('category', 'other'),
                            assignee=item.get('assignee', 'both'),
                            is_critical=item.get('is_critical', False),
                            linked_tool=item.get('linked_tool', ''),
                            is_custom=False,
                            sort_order=max_order,
                        )
            else:
                try:
                    item = topic['items'][int(item_idx)]
                    if item['title'].lower().strip() not in existing_titles:
                        TaskMilestone.objects.create(
                            wedding=wedding,
                            phase=target_phase,
                            title=item['title'],
                            category=item.get('category', 'other'),
                            assignee=item.get('assignee', 'both'),
                            is_critical=item.get('is_critical', False),
                            linked_tool=item.get('linked_tool', ''),
                            is_custom=False,
                            sort_order=max_order + 1,
                        )
                except (ValueError, IndexError):
                    pass

            if request.htmx:
                ctx = _build_checklist_context(wedding)
                ctx['task'] = None
                ctx['oob_phase_list_key'] = target_phase
                ctx['oob_guide_update'] = True
                return render(request, 'operations/partials/task_item_with_oob.html', ctx)
    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def add_phase(request):
    """Add a new customizable TimelinePhase."""
    if request.method == 'POST':
        wedding = request.wedding
        phase_objs = _ensure_wedding_phases(wedding)
        label = (request.POST.get('label') or '').strip()
        if label:
            new_key = f"phase_{uuid.uuid4().hex[:6]}"
            next_order = len(phase_objs)
            TimelinePhase.objects.create(
                wedding=wedding,
                key=new_key,
                label=label,
                sort_order=next_order,
            )
            messages.success(request, f'Fase "{label}" berhasil ditambahkan.')
            response = redirect('operations-checklist:checklist')
            return response
    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def update_phase(request, phase_key):
    """Inline rename, reorder (up/down), or set active override for a TimelinePhase."""
    if request.method == 'POST':
        wedding = request.wedding
        phase_objs = list(_ensure_wedding_phases(wedding))
        target = next((p for p in phase_objs if p.key == phase_key), None)
        if not target:
            return redirect('operations-checklist:checklist')

        action = request.POST.get('action', 'rename')
        if action == 'rename':
            new_label = (request.POST.get('label') or '').strip()
            if new_label:
                target.label = new_label
                target.save(update_fields=['label'])
                messages.success(request, f'Nama fase diperbarui menjadi "{new_label}".')
        elif action == 'set_active':
            TimelinePhase.objects.filter(wedding=wedding).update(is_active_override=False)
            target.is_active_override = True
            target.save(update_fields=['is_active_override'])
            messages.success(request, f'"{target.label}" ditetapkan sebagai Fase Aktif saat ini.')
        elif action in ('move_up', 'move_down'):
            idx = phase_objs.index(target)
            swap_idx = idx - 1 if action == 'move_up' else idx + 1
            if 0 <= swap_idx < len(phase_objs):
                phase_objs[idx], phase_objs[swap_idx] = phase_objs[swap_idx], phase_objs[idx]
                for i, p in enumerate(phase_objs):
                    if p.sort_order != i:
                        p.sort_order = i
                        p.save(update_fields=['sort_order'])
    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def delete_phase(request, phase_key):
    """Safe delete a TimelinePhase: move its tasks to another phase OR delete them explicitly."""
    if request.method == 'POST':
        wedding = request.wedding
        phase_objs = list(_ensure_wedding_phases(wedding))
        if len(phase_objs) <= 1:
            messages.warning(request, 'Minimal harus ada 1 fase di timeline. Gunakan fitur Rombak Timeline jika ingin mereset dari 0.')
            return redirect('operations-checklist:checklist')

        target = next((p for p in phase_objs if p.key == phase_key), None)
        if not target:
            return redirect('operations-checklist:checklist')

        remaining_phases = [p for p in phase_objs if p.key != phase_key]
        task_action = request.POST.get('task_action', 'move')
        target_phase_key = request.POST.get('target_phase_key', '')

        phase_tasks = TaskMilestone.objects.filter(wedding=wedding, phase=phase_key)
        task_count = phase_tasks.count()

        if task_count > 0:
            if task_action == 'delete':
                phase_tasks.delete()
                messages.info(request, f'Fase "{target.label}" beserta {task_count} tugas di dalamnya telah dihapus.')
            else:
                valid_dest = next((p for p in remaining_phases if p.key == target_phase_key), remaining_phases[0])
                phase_tasks.update(phase=valid_dest.key)
                messages.success(request, f'{task_count} tugas dipindahkan ke "{valid_dest.label}", dan fase "{target.label}" dihapus.')
        else:
            messages.info(request, f'Fase "{target.label}" telah dihapus.')

        target.delete()
        for i, p in enumerate(remaining_phases):
            if p.sort_order != i:
                p.sort_order = i
                p.save(update_fields=['sort_order'])
    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def bulk_manage_phases(request):
    """Bulk update phase names, order, active phase, and newly added phases."""
    if request.method == 'POST':
        wedding = request.wedding
        phase_objs = list(_ensure_wedding_phases(wedding))
        active_key = request.POST.get('active_phase_key', '')

        for idx, p in enumerate(phase_objs):
            new_label = (request.POST.get(f'label_{p.key}') or '').strip()
            new_order_raw = request.POST.get(f'order_{p.key}', str(idx))
            try:
                new_order = int(new_order_raw)
            except ValueError:
                new_order = idx
            if new_label:
                p.label = new_label
            p.sort_order = new_order
            p.is_active_override = (p.key == active_key)
            p.save()

        # Re-normalize sort_order sequentially
        ordered = list(TimelinePhase.objects.filter(wedding=wedding).order_by('sort_order', 'id'))
        for i, p in enumerate(ordered):
            if p.sort_order != i:
                p.sort_order = i
                p.save(update_fields=['sort_order'])

        new_phase_label = (request.POST.get('new_phase_label') or '').strip()
        if new_phase_label:
            TimelinePhase.objects.create(
                wedding=wedding,
                key=f"phase_{uuid.uuid4().hex[:6]}",
                label=new_phase_label,
                sort_order=len(ordered),
            )
        messages.success(request, 'Susunan tahapan timeline berhasil diperbarui.')
    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def reset_or_apply_preset(request):
    """Reset tasks/phases to 0 or apply a timeline preset (Standard, Express, Event-Based)."""
    if request.method == 'POST':
        wedding = request.wedding
        mode = request.POST.get('mode', '')

        if mode == 'clear_tasks':
            # Keep existing phases, clear all tasks so user can build tasks from 0 with the Guide
            deleted_count, _ = TaskMilestone.objects.filter(wedding=wedding).delete()
            messages.success(request, f'{deleted_count} tugas dibersihkan. Silakan gunakan Panduan Tugas Penting atau tambah tugas sendiri dari 0!')

        elif mode == 'start_from_zero':
            # Wipe all tasks and phases, start with custom starter phase(s) entered by user
            TaskMilestone.objects.filter(wedding=wedding).delete()
            TimelinePhase.objects.filter(wedding=wedding).delete()
            raw_phases = request.POST.getlist('custom_phase_labels')
            clean_labels = [lbl.strip() for lbl in raw_phases if lbl and lbl.strip()]
            if not clean_labels:
                clean_labels = ['Tahap 1: Persiapan Awal']
            for idx, lbl in enumerate(clean_labels):
                TimelinePhase.objects.create(
                    wedding=wedding,
                    key=f"custom_{idx + 1}_{uuid.uuid4().hex[:4]}",
                    label=lbl,
                    sort_order=idx,
                    is_active_override=(idx == 0),
                )
            messages.success(request, 'Timeline & Tugas berhasil di-reset dari 0! Gunakan Panduan & Ide Tugas untuk mulai menyusun.')

        elif mode == 'preset':
            preset_key = request.POST.get('preset_key', 'standard')
            task_handling = request.POST.get('task_handling', 'remap')  # 'remap' | 'template' | 'empty'
            preset = TIMELINE_PRESETS.get(preset_key, TIMELINE_PRESETS['standard'])
            new_phases = preset['phases']
            new_keys = [k for k, _ in new_phases]

            old_phases = list(_ensure_wedding_phases(wedding))
            old_keys = [p.key for p in old_phases]

            if task_handling == 'empty':
                TaskMilestone.objects.filter(wedding=wedding).delete()
            elif task_handling == 'template':
                from core.views import DEFAULT_TASKS
                TaskMilestone.objects.filter(wedding=wedding).delete()
                for i, t_data in enumerate(DEFAULT_TASKS):
                    t_phase = t_data['phase']
                    if t_phase not in new_keys:
                        t_phase = new_keys[min(i % len(new_keys), len(new_keys) - 1)]
                    TaskMilestone.objects.create(
                        wedding=wedding,
                        phase=t_phase,
                        category=t_data.get('category', 'other'),
                        title=t_data['title'],
                        assignee=t_data.get('assignee', 'both'),
                        linked_tool=t_data.get('linked_tool', ''),
                        is_critical=t_data.get('is_critical', False),
                        sort_order=i,
                    )
            else:
                # Remap existing tasks proportionally so zero tasks are lost
                for old_idx, old_k in enumerate(old_keys):
                    if old_k not in new_keys:
                        mapped_idx = min(round((old_idx / max(len(old_keys) - 1, 1)) * (len(new_keys) - 1)), len(new_keys) - 1)
                        TaskMilestone.objects.filter(wedding=wedding, phase=old_k).update(phase=new_keys[mapped_idx])

            TimelinePhase.objects.filter(wedding=wedding).delete()
            for idx, (p_key, p_label) in enumerate(new_phases):
                TimelinePhase.objects.create(
                    wedding=wedding,
                    key=p_key,
                    label=p_label,
                    sort_order=idx,
                )
            messages.success(request, f'Preset "{preset["name"]}" berhasil diterapkan!')

    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def delete_task(request, pk):
    """HTMX endpoint: Delete any task (custom or default)."""
    task = get_object_or_404(TaskMilestone, pk=pk, wedding=request.wedding)
    old_phase = task.phase
    task.delete()
    if request.htmx:
        ctx = _build_checklist_context(request.wedding)
        ctx['task'] = None
        if ctx['grouped_tasks'].get(old_phase, {}).get('total', 0) == 0:
            ctx['oob_phase_list_key'] = old_phase
        ctx['oob_guide_update'] = True
        return render(request, 'operations/partials/task_item_with_oob.html', ctx)
    return redirect('operations-checklist:checklist')


# ============================================================
# OPERATIONS HUB VIEWS (Route: /operations/)
# ============================================================

@login_required
@workspace_required
def operations_hub(request):
    """Operations hub: Rundown, Assets, Fabric Calculator."""
    wedding = request.wedding

    # Rundown events
    rundown = RundownEvent.objects.filter(wedding=wedding)

    # Rundown sanity checks
    sanity_warnings = _check_rundown_sanity(rundown)

    # Assets
    assets = AssetCustodian.objects.filter(wedding=wedding)
    critical_assets = assets.filter(asset_category='critical')
    equipment_assets = assets.filter(asset_category='equipment')

    # Fabric entries
    fabric_entries = FabricEntry.objects.filter(wedding=wedding)
    fabric_totals = _calculate_fabric_totals(fabric_entries)

    context = {
        'rundown': rundown,
        'sanity_warnings': sanity_warnings,
        'critical_assets': critical_assets,
        'equipment_assets': equipment_assets,
        'fabric_entries': fabric_entries,
        'fabric_totals': fabric_totals,
        'rundown_form': RundownEventForm(),
        'asset_form': AssetCustodianForm(),
        'fabric_form': FabricEntryForm(),
    }
    return render(request, 'operations/operations_hub.html', context)


def _check_rundown_sanity(rundown_events):
    """Run automated sanity checks on the rundown."""
    warnings = []
    events = list(rundown_events)

    for event in events:
        duration = event.duration_minutes
        activity_lower = event.activity.lower()

        # MUA Duration Check
        if 'mua' in activity_lower and 'pengantin' in activity_lower and duration < 120:
            warnings.append({
                'type': 'danger',
                'icon': '<i data-lucide="alert-triangle"></i>',
                'message': f'MUA Pengantin Wanita hanya {duration} menit (minimal 120 menit).',
                'event': event,
            })
        if 'mua' in activity_lower and 'ibu' in activity_lower and duration < 60:
            warnings.append({
                'type': 'warning',
                'icon': '<i data-lucide="clock"></i>',
                'message': f'MUA Ibu hanya {duration} menit (minimal 60 menit).',
                'event': event,
            })

        # Photo session congestion
        if ('foto' in activity_lower or 'photo' in activity_lower) and duration < 15:
            warnings.append({
                'type': 'warning',
                'icon': '<i data-lucide="camera"></i>',
                'message': f'Sesi foto "{event.activity}" hanya {duration} menit — risiko terburu-buru.',
                'event': event,
            })

    # Transition gap check (akad → resepsi)
    for i, event in enumerate(events[:-1]):
        next_event = events[i + 1]
        act_lower = event.activity.lower()
        next_lower = next_event.activity.lower()

        if any(k in act_lower for k in ['akad', 'pemberkatan', 'holy matrimony']):
            if any(k in next_lower for k in ['resepsi', 'reception']):
                from datetime import datetime, timedelta
                end = datetime.combine(datetime.today(), event.end_time)
                start = datetime.combine(datetime.today(), next_event.start_time)
                gap = int((start - end).total_seconds() / 60)
                if gap < 60:
                    warnings.append({
                        'type': 'danger',
                        'icon': '<i data-lucide="alert-octagon"></i>',
                        'message': f'Jeda Akad → Resepsi hanya {gap} menit (minimal 60 menit untuk retouch).',
                    })

    return warnings


def _calculate_fabric_totals(entries):
    """Aggregate fabric yardage across all entries."""
    totals = defaultdict(float)
    for entry in entries:
        yardage = entry.yardage
        for fabric_type, meters in yardage.items():
            totals[fabric_type] += meters
    return dict(totals)


# HTMX endpoints for rundown
@login_required
@owner_required
def add_rundown_event(request):
    if request.method == 'POST':
        form = RundownEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.wedding = request.wedding
            event.save()
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def update_rundown_event(request, pk):
    event = get_object_or_404(RundownEvent, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        form = RundownEventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def delete_rundown_event(request, pk):
    event = get_object_or_404(RundownEvent, pk=pk, wedding=request.wedding)
    event.delete()
    return redirect('operations-hub:operations_hub')


# HTMX endpoints for assets
@login_required
@owner_required
def add_asset(request):
    if request.method == 'POST':
        form = AssetCustodianForm(request.POST)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.wedding = request.wedding
            asset.save()
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def update_asset(request, pk):
    asset = get_object_or_404(AssetCustodian, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        form = AssetCustodianForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def delete_asset(request, pk):
    asset = get_object_or_404(AssetCustodian, pk=pk, wedding=request.wedding)
    asset.delete()
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def toggle_asset_status(request, pk):
    asset = get_object_or_404(AssetCustodian, pk=pk, wedding=request.wedding)
    new_status = request.POST.get('status') or request.GET.get('status')
    if new_status and new_status in dict(AssetCustodian.STATUS_CHOICES):
        asset.status = new_status
    else:
        cycle = ['pending', 'loaded', 'received', 'handed', 'packed']
        idx = cycle.index(asset.status) if asset.status in cycle else 0
        asset.status = cycle[(idx + 1) % len(cycle)]
    asset.save(update_fields=['status'])
    if request.htmx:
        return render(request, 'operations/partials/asset_item.html', {'asset': asset})
    return redirect('operations-hub:operations_hub')


# HTMX endpoints for fabric
@login_required
@owner_required
def add_fabric_entry(request):
    if request.method == 'POST':
        form = FabricEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.wedding = request.wedding
            entry.save()
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def update_fabric_entry(request, pk):
    entry = get_object_or_404(FabricEntry, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        form = FabricEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def delete_fabric_entry(request, pk):
    entry = get_object_or_404(FabricEntry, pk=pk, wedding=request.wedding)
    entry.delete()
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def update_task(request, pk):
    """HTMX endpoint: Update custom or template task."""
    task = get_object_or_404(TaskMilestone, pk=pk, wedding=request.wedding)
    old_phase = task.phase
    if request.GET.get('cancel') == '1':
        ctx = _build_checklist_context(request.wedding)
        return render(request, 'operations/partials/task_item.html', {'task': _annotate_single_task(task, ctx)})
    if request.method == 'POST':
        form = TaskMilestoneForm(request.POST, instance=task)
        if form.is_valid():
            updated_task = form.save()
            if request.htmx:
                ctx = _build_checklist_context(request.wedding)
                if old_phase == updated_task.phase:
                    ctx['task'] = _annotate_single_task(updated_task, ctx)
                else:
                    ctx['task'] = None
                    ctx['oob_phase_list_key'] = old_phase
                    ctx['oob_second_phase_list_key'] = updated_task.phase
                return render(request, 'operations/partials/task_item_with_oob.html', ctx)
            return redirect('operations-checklist:checklist')
        response = render(request, 'operations/partials/task_form_inline.html', {'form': form, 'task': task})
        response['HX-Retarget'] = f'#edit-task-{task.pk}'
        response['HX-Reselect'] = f'#edit-task-{task.pk}'
        response['HX-Reswap'] = 'outerHTML'
        return response
    else:
        form = TaskMilestoneForm(instance=task)
    return render(request, 'operations/partials/task_form_inline.html', {'form': form, 'task': task})



from operations.models import DocumentRequirement, SeserahanItem
from operations.forms import DocumentRequirementForm, SeserahanItemForm

@login_required
@workspace_required
def detail_checklists_view(request):
    """Detailed checklists for Documents and Seserahan."""
    wedding = request.wedding
    
    documents = DocumentRequirement.objects.filter(wedding=wedding)
    seserahan = SeserahanItem.objects.filter(wedding=wedding)
    
    doc_done_count = documents.filter(status='done').count()
    ses_done_count = seserahan.filter(status='done').count()
    ses_total_est = sum(int(s.est_price or 0) for s in seserahan)
    ses_total_actual = sum(int(s.actual_price or 0) for s in seserahan)
    
    doc_form = DocumentRequirementForm()
    ses_form = SeserahanItemForm()
    
    context = {
        'documents': documents,
        'seserahan': seserahan,
        'doc_done_count': doc_done_count,
        'ses_done_count': ses_done_count,
        'ses_total_est': ses_total_est,
        'ses_total_actual': ses_total_actual,
        'ses_variance': ses_total_est - ses_total_actual,
        'doc_form': doc_form,
        'ses_form': ses_form,
    }
    return render(request, 'operations/detail_checklists.html', context)


@login_required
@owner_required
def add_document(request):
    wedding = request.wedding
    if request.method == 'POST':
        form = DocumentRequirementForm(request.POST)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.wedding = wedding
            doc.save()
            return redirect('operations-checklist:detail_checklists')
    return redirect('operations-checklist:detail_checklists')

@login_required
@owner_required
def add_seserahan(request):
    wedding = request.wedding
    if request.method == 'POST':
        form = SeserahanItemForm(request.POST)
        if form.is_valid():
            ses = form.save(commit=False)
            ses.wedding = wedding
            ses.save()
            return redirect('operations-checklist:detail_checklists')
    return redirect('operations-checklist:detail_checklists')

@login_required
@owner_required
def toggle_document_status(request, pk):
    doc = get_object_or_404(DocumentRequirement, pk=pk, wedding=request.wedding)
    new_status = request.POST.get('status') or request.GET.get('status')
    if new_status and new_status in dict(DocumentRequirement.STATUS_CHOICES):
        doc.status = new_status
    else:
        cycle = ['none', 'process', 'done']
        idx = cycle.index(doc.status) if doc.status in cycle else 0
        doc.status = cycle[(idx + 1) % len(cycle)]
    doc.save(update_fields=['status'])
    return redirect('operations-checklist:detail_checklists')

@login_required
@owner_required
def toggle_seserahan_status(request, pk):
    ses = get_object_or_404(SeserahanItem, pk=pk, wedding=request.wedding)
    new_status = request.POST.get('status') or request.GET.get('status')
    if new_status and new_status in dict(SeserahanItem.STATUS_CHOICES):
        ses.status = new_status
    else:
        cycle = ['none', 'process', 'done']
        idx = cycle.index(ses.status) if ses.status in cycle else 0
        ses.status = cycle[(idx + 1) % len(cycle)]
    ses.save(update_fields=['status'])
    return redirect('operations-checklist:detail_checklists')

@login_required
@owner_required
def delete_document(request, pk):
    doc = get_object_or_404(DocumentRequirement, pk=pk, wedding=request.wedding)
    doc.delete()
    return redirect('operations-checklist:detail_checklists')

@login_required
@owner_required
def delete_seserahan(request, pk):
    ses = get_object_or_404(SeserahanItem, pk=pk, wedding=request.wedding)
    ses.delete()
    return redirect('operations-checklist:detail_checklists')


@login_required
@owner_required
def update_document(request, pk):
    doc = get_object_or_404(DocumentRequirement, pk=pk, wedding=request.wedding)
    if request.GET.get('cancel') == '1':
        return render(request, 'operations/partials/doc_row.html', {'doc': doc})
    if request.method == 'POST':
        form = DocumentRequirementForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            return redirect('operations-checklist:detail_checklists')
        response = render(request, 'operations/partials/doc_form_inline.html', {'doc_form': form, 'doc': doc})
        response['HX-Retarget'] = f'#doc-{doc.pk}'
        response['HX-Reselect'] = f'#doc-{doc.pk}'
        response['HX-Reswap'] = 'outerHTML'
        return response
    else:
        form = DocumentRequirementForm(instance=doc)
    return render(request, 'operations/partials/doc_form_inline.html', {'doc_form': form, 'doc': doc})

@login_required
@owner_required
def update_seserahan(request, pk):
    ses = get_object_or_404(SeserahanItem, pk=pk, wedding=request.wedding)
    if request.GET.get('cancel') == '1':
        return render(request, 'operations/partials/ses_row.html', {'ses': ses})
    if request.method == 'POST':
        form = SeserahanItemForm(request.POST, instance=ses)
        if form.is_valid():
            form.save()
            return redirect('operations-checklist:detail_checklists')
        response = render(request, 'operations/partials/ses_form_inline.html', {'ses_form': form, 'ses': ses})
        response['HX-Retarget'] = f'#ses-{ses.pk}'
        response['HX-Reselect'] = f'#ses-{ses.pk}'
        response['HX-Reswap'] = 'outerHTML'
        return response
    else:
        form = SeserahanItemForm(instance=ses)
    return render(request, 'operations/partials/ses_form_inline.html', {'ses_form': form, 'ses': ses})
