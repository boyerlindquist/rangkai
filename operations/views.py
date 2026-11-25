"""
Operations views: Checklist, Rundown, Asset Custodian, Fabric Calculator.
"""
import json
import uuid
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from collections import defaultdict

from core.decorators import workspace_required, owner_required
from operations.models import (
    TimelinePhase,
    TaskMilestone,
    RundownEvent,
    AssetCustodian,
    FabricEntry,
    WeddingNote,
    DEFAULT_PHASE_RANGES,
    PHASE_COLOR_CHOICES,
    format_h_day,
)
from operations.forms import TaskMilestoneForm, RundownEventForm, AssetCustodianForm, FabricEntryForm


PHASE_COLOR_PALETTE = [c[0] for c in PHASE_COLOR_CHOICES]


# ============================================================
# CHECKLIST PRESETS & SMART GUIDE CATALOG
# ============================================================

TIMELINE_PRESETS = {
    'standard': {
        'name': 'Standar 1 Tahun (Default)',
        'desc': '5 fase berbasis H-minus (H-360 s/d H+1), cocok untuk persiapan 6-12 bulan.',
        'phases': [
            ('d360', 'Fase 1: Persiapan Awal & Venue', 360, 181, 'emerald'),
            ('d180', 'Fase 2: Vendor Utama & Berkas', 180, 91, 'blue'),
            ('d90', 'Fase 3: Undangan & Finalisasi', 90, 31, 'violet'),
            ('d30', 'Fase 4: Teknis & Pelunasan', 30, 7, 'amber'),
            ('dday', 'Fase 5: Minggu Hari-H & Pasca', 6, -1, 'rose'),
        ],
    },
    'express': {
        'name': 'Persiapan Express (< 6 Bulan)',
        'desc': '4 tahapan ringkas & padat (H-180 s/d H+1) untuk persiapan cepat 2-5 bulan.',
        'phases': [
            ('d360', 'Tahap 1: Fondasi, Budget & Venue', 180, 91, 'emerald'),
            ('d180', 'Tahap 2: Vendor Utama, Busana & KUA', 90, 31, 'blue'),
            ('d30', 'Tahap 3: Undangan, RSVP & Technical Meeting', 30, 7, 'amber'),
            ('dday', 'Tahap 4: Minggu Terakhir & Hari-H', 6, -1, 'rose'),
        ],
    },
    'event_based': {
        'name': 'Berbasis Rangkaian Acara',
        'desc': '5 tahapan berdasarkan prosesi acara (Lamaran -> Vendor -> KUA -> Pra-Acara -> Hari-H).',
        'phases': [
            ('d360', '1. Lamaran, Keluarga & Anggaran', 360, 181, 'emerald'),
            ('d180', '2. Venue, Katering & Vendor Utama', 180, 91, 'blue'),
            ('d90', '3. Berkas KUA, Cincin & Undangan', 90, 31, 'violet'),
            ('d30', '4. Pengajian, Siraman & Gladi Bersih', 30, 7, 'amber'),
            ('dday', '5. Akad Nikah, Resepsi & Pasca-Acara', 6, -1, 'rose'),
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


def _parse_phase_day(raw_value, field_label):
    """Parse an integer day-before-wedding value (supports -30 to 1095)."""
    text = str(raw_value if raw_value is not None else '').strip()
    if text == '':
        return None, f'{field_label} wajib diisi.'
    try:
        val = int(text)
    except ValueError:
        return None, f'{field_label} harus berupa angka bulat (contoh: 180 untuk H-180, 0 untuk Hari-H).'
    if val < -30 or val > 1095:
        return None, f'{field_label} harus berada di antara -30 (H+30) sampai 1095 (H-1095).'
    return val, None


def _validate_phase_ranges(phase_entries):
    """
    Validate a list of (label, start_day_before, end_day_before) tuples.
    Rules:
      1. start_day_before >= end_day_before for every phase.
      2. No two phases may overlap: [end1, start1] and [end2, start2] overlap iff max(end1, end2) <= min(start1, start2).
    Returns error string or None if valid.
    """
    for label, start_d, end_d in phase_entries:
        if start_d < end_d:
            return (
                f'Rentang fase "{label}" tidak valid: hari mulai ({format_h_day(start_d)}) '
                f'harus lebih awal atau sama dengan hari selesai ({format_h_day(end_d)}).'
            )

    n = len(phase_entries)
    for i in range(n):
        lbl_a, s_a, e_a = phase_entries[i]
        for j in range(i + 1, n):
            lbl_b, s_b, e_b = phase_entries[j]
            if max(e_a, e_b) <= min(s_a, s_b):
                return (
                    f'Rentang waktu fase "{lbl_a}" ({format_h_day(s_a)} s/d {format_h_day(e_a)}) '
                    f'bentrok (overlap) dengan "{lbl_b}" ({format_h_day(s_b)} s/d {format_h_day(e_b)}). '
                    f'Pastikan rentang antar fase tidak saling tumpang tindih.'
                )
    return None


def _resolve_active_phase(phase_objs, days_remaining, tasks_by_phase=None):
    """
    Determine the active phase key & index from TimelinePhase objects:
      1. Manual override (is_active_override=True)
      2. Exact H-minus range match against days_remaining
      3. Nearest phase if days_remaining is outside defined ranges
      4. Fallback to first incomplete phase or first phase
    """
    phase_order = [p.key for p in phase_objs]
    if not phase_order:
        return None, -1

    override_phase = next((p for p in phase_objs if p.is_active_override), None)
    if override_phase:
        return override_phase.key, phase_order.index(override_phase.key)

    if days_remaining is not None:
        for idx, p in enumerate(phase_objs):
            if p.contains_days_before(days_remaining):
                return p.key, idx
        # Outside explicit range: if before earliest phase, pick earliest; if past latest, pick latest
        sorted_by_start = sorted(enumerate(phase_objs), key=lambda x: x[1].start_day_before, reverse=True)
        if days_remaining > sorted_by_start[0][1].start_day_before:
            return sorted_by_start[0][1].key, sorted_by_start[0][0]
        sorted_by_end = sorted(enumerate(phase_objs), key=lambda x: x[1].end_day_before)
        if days_remaining < sorted_by_end[0][1].end_day_before:
            return sorted_by_end[0][1].key, sorted_by_end[0][0]

    if tasks_by_phase is not None:
        for idx, p_key in enumerate(phase_order):
            p_list = tasks_by_phase.get(p_key, [])
            p_total = len(p_list)
            p_done = sum(1 for t in p_list if t.status == 'done')
            if p_total == 0 or p_done < p_total:
                return p_key, idx

    return phase_order[0], 0


def _ensure_wedding_phases(wedding, all_tasks_list=None):
    """Ensure Wedding has TimelinePhase rows; seed from default 5 phases with non-overlapping ranges if empty."""
    existing = list(TimelinePhase.objects.filter(wedding=wedding).order_by('sort_order', 'id'))
    if existing:
        existing_keys = {p.key for p in existing}
        if all_tasks_list is not None:
            orphan_keys = {t.phase for t in all_tasks_list if t.phase and t.phase not in existing_keys}
        else:
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
                s_d, e_d, col = DEFAULT_PHASE_RANGES.get(o_key, (360, 181, PHASE_COLOR_PALETTE[max_order % len(PHASE_COLOR_PALETTE)]))
                p = TimelinePhase.objects.create(
                    wedding=wedding,
                    key=o_key,
                    label=default_map.get(o_key, o_key),
                    start_day_before=s_d,
                    end_day_before=e_d,
                    color=col,
                    sort_order=max_order,
                )
                existing.append(p)
        return existing

    # Seed the 5 standard phases with non-overlapping ranges
    seeded = []
    for idx, (p_key, p_label, s_d, e_d, col) in enumerate(TIMELINE_PRESETS['standard']['phases']):
        seeded.append(
            TimelinePhase.objects.create(
                wedding=wedding,
                key=p_key,
                label=p_label,
                start_day_before=s_d,
                end_day_before=e_d,
                color=col,
                sort_order=idx,
            )
        )
    return seeded


# ============================================================
# CHECKLIST VIEWS (Route: /checklist/)
# ============================================================

def _build_checklist_context(wedding, assignee_filter='', include_guide=True, include_form=True):
    """Compute grouped tasks, dynamic phases, progress, and smart task guide in minimal queries."""
    # Single query for all tasks of this wedding (reused for grouping, counts, overdue, and guide matching)
    all_tasks_list = list(TaskMilestone.objects.filter(wedding=wedding))
    phase_objs = _ensure_wedding_phases(wedding, all_tasks_list=all_tasks_list)
    phases = [(p.key, p.label) for p in phase_objs]
    phase_order = [p.key for p in phase_objs]

    filtered_tasks = [t for t in all_tasks_list if t.assignee == assignee_filter] if assignee_filter else all_tasks_list
    tasks_by_phase = defaultdict(list)
    for t in filtered_tasks:
        tasks_by_phase[t.phase].append(t)

    days_remaining = wedding.days_remaining
    current_phase_key, current_phase_idx = _resolve_active_phase(phase_objs, days_remaining, tasks_by_phase)

    grouped_tasks = {}
    total_overdue_tasks = 0
    all_overdue_tasks = []
    today = timezone.localdate()

    for phase_idx, p_obj in enumerate(phase_objs):
        phase_key = p_obj.key
        phase_label = p_obj.label
        phase_tasks = tasks_by_phase.get(phase_key, [])
        total = len(phase_tasks)
        done = sum(1 for t in phase_tasks if t.status == 'done')
        progress = round((done / total) * 100) if total > 0 else 0

        is_current = (phase_key == current_phase_key)
        is_past = (current_phase_idx != -1 and phase_idx < current_phase_idx)
        is_upcoming = (current_phase_idx != -1 and phase_idx > current_phase_idx)

        overdue_tasks_in_phase = []
        annotated_tasks = []
        for t in phase_tasks:
            t_deadline_overdue = bool(t.due_date and t.due_date < today and t.status != 'done')
            t_is_overdue = ((is_past or t_deadline_overdue) and t.status != 'done')
            setattr(t, 'is_deadline_overdue', t_deadline_overdue)
            setattr(t, 'is_overdue', t_is_overdue)
            annotated_tasks.append(t)
            if t_is_overdue:
                overdue_tasks_in_phase.append(t)

        if overdue_tasks_in_phase:
            total_overdue_tasks += len(overdue_tasks_in_phase)
            all_overdue_tasks.extend(overdue_tasks_in_phase)

        grouped_tasks[phase_key] = {
            'key': phase_key,
            'label': phase_label,
            'start_day_before': p_obj.start_day_before,
            'end_day_before': p_obj.end_day_before,
            'range_display': p_obj.range_display,
            'color': p_obj.color,
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

    total = len(all_tasks_list)
    done = sum(1 for t in all_tasks_list if t.status == 'done')
    overall_progress = round((done / max(total, 1)) * 100)

    # Annotate Smart Guide Catalog only when needed (skip on fast checkbox OOB updates)
    guide_catalog = []
    if include_guide:
        existing_titles_lower = {t.title.lower().strip() for t in all_tasks_list}
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
        'task_form': TaskMilestoneForm(wedding=wedding, phases=phase_objs) if include_form else None,
        'days_remaining': days_remaining,
        'current_phase_key': current_phase_key,
        'current_phase_label': dict(phases).get(current_phase_key) if current_phase_key else None,
        'total_overdue_tasks': total_overdue_tasks,
        'all_overdue_tasks': all_overdue_tasks,
        'guide_catalog': guide_catalog,
        'timeline_presets': TIMELINE_PRESETS,
        'phase_color_choices': PHASE_COLOR_CHOICES,
    }


def _annotate_single_task(task, ctx):
    """Attach is_overdue and is_deadline_overdue flags to a single TaskMilestone instance."""
    phase_data = ctx['grouped_tasks'].get(task.phase)
    is_past = phase_data['is_past'] if phase_data else False
    today = timezone.localdate()
    is_deadline_overdue = bool(task.due_date and task.due_date < today and task.status != 'done')
    setattr(task, 'is_deadline_overdue', is_deadline_overdue)
    setattr(task, 'is_overdue', (is_past or is_deadline_overdue) and task.status != 'done')
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
    from core.tutorial import emit_tutorial_event
    if request.GET.get('from') == 'dashboard':
        return emit_tutorial_event(request, redirect('core:dashboard'), 'task_saved')
    if request.htmx:
        ctx = _build_checklist_context(request.wedding, include_guide=False, include_form=False)
        if request.GET.get('oob_only') == '1':
            return emit_tutorial_event(
                request,
                render(request, 'operations/partials/checklist_oob_stats.html', ctx),
                'task_saved',
            )
        ctx['task'] = _annotate_single_task(task, ctx)
        return emit_tutorial_event(
            request,
            render(request, 'operations/partials/task_item_with_oob.html', ctx),
            'task_saved',
        )
    return emit_tutorial_event(request, redirect('operations-checklist:checklist'), 'task_saved')


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
            from core.tutorial import emit_tutorial_event
            if request.htmx:
                ctx = _build_checklist_context(request.wedding)
                ctx['task'] = None
                ctx['oob_phase_list_key'] = task.phase
                ctx['oob_guide_update'] = True
                return emit_tutorial_event(
                    request,
                    render(request, 'operations/partials/task_item_with_oob.html', ctx),
                    'task_saved',
                )
            return emit_tutorial_event(request, redirect('operations-checklist:checklist'), 'task_saved')
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
    """Add a new customizable TimelinePhase with required non-overlapping H-minus range."""
    if request.method == 'POST':
        wedding = request.wedding
        phase_objs = _ensure_wedding_phases(wedding)
        label = (request.POST.get('label') or '').strip()
        if not label:
            messages.error(request, 'Nama fase wajib diisi.')
            return redirect('operations-checklist:checklist')

        start_d, err1 = _parse_phase_day(request.POST.get('start_day_before'), 'Mulai (H-)')
        end_d, err2 = _parse_phase_day(request.POST.get('end_day_before'), 'Selesai (H-)')
        if err1 or err2:
            messages.error(request, err1 or err2)
            return redirect('operations-checklist:checklist')

        entries = [(p.label, p.start_day_before, p.end_day_before) for p in phase_objs]
        entries.append((label, start_d, end_d))
        overlap_err = _validate_phase_ranges(entries)
        if overlap_err:
            messages.error(request, overlap_err)
            return redirect('operations-checklist:checklist')

        color = (request.POST.get('color') or '').strip()
        if color not in PHASE_COLOR_PALETTE:
            color = PHASE_COLOR_PALETTE[len(phase_objs) % len(PHASE_COLOR_PALETTE)]

        new_key = f"phase_{uuid.uuid4().hex[:6]}"
        TimelinePhase.objects.create(
            wedding=wedding,
            key=new_key,
            label=label,
            start_day_before=start_d,
            end_day_before=end_d,
            color=color,
            sort_order=len(phase_objs),
        )
        messages.success(request, f'Fase "{label}" ({format_h_day(start_d)} s/d {format_h_day(end_d)}) berhasil ditambahkan.')
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
    """Bulk update phase names, H-minus day ranges (non-overlapping), colors, order, active phase, and newly added phases."""
    if request.method == 'POST':
        wedding = request.wedding
        phase_objs = list(_ensure_wedding_phases(wedding))
        active_key = request.POST.get('active_phase_key', '')

        staged_updates = []
        range_entries = []

        for idx, p in enumerate(phase_objs):
            new_label = (request.POST.get(f'label_{p.key}') or '').strip() or p.label
            new_order_raw = request.POST.get(f'order_{p.key}', str(idx))
            try:
                new_order = int(new_order_raw)
            except ValueError:
                new_order = idx

            start_raw = request.POST.get(f'start_{p.key}', p.start_day_before)
            end_raw = request.POST.get(f'end_{p.key}', p.end_day_before)
            start_d, err1 = _parse_phase_day(start_raw, f'Mulai fase "{new_label}"')
            end_d, err2 = _parse_phase_day(end_raw, f'Selesai fase "{new_label}"')
            if err1 or err2:
                messages.error(request, err1 or err2)
                return redirect('operations-checklist:checklist')

            color = (request.POST.get(f'color_{p.key}') or p.color).strip()
            if color not in PHASE_COLOR_PALETTE:
                color = p.color

            staged_updates.append((p, new_label, new_order, start_d, end_d, color))
            range_entries.append((new_label, start_d, end_d))

        new_phase_label = (request.POST.get('new_phase_label') or '').strip()
        new_phase_spec = None
        if new_phase_label:
            n_start, err1 = _parse_phase_day(request.POST.get('new_phase_start'), f'Mulai fase baru "{new_phase_label}"')
            n_end, err2 = _parse_phase_day(request.POST.get('new_phase_end'), f'Selesai fase baru "{new_phase_label}"')
            if err1 or err2:
                messages.error(request, err1 or err2)
                return redirect('operations-checklist:checklist')
            n_color = (request.POST.get('new_phase_color') or '').strip()
            if n_color not in PHASE_COLOR_PALETTE:
                n_color = PHASE_COLOR_PALETTE[len(phase_objs) % len(PHASE_COLOR_PALETTE)]
            new_phase_spec = (new_phase_label, n_start, n_end, n_color)
            range_entries.append((new_phase_label, n_start, n_end))

        overlap_err = _validate_phase_ranges(range_entries)
        if overlap_err:
            messages.error(request, overlap_err)
            return redirect('operations-checklist:checklist')

        with transaction.atomic():
            for p, new_label, new_order, start_d, end_d, color in staged_updates:
                p.label = new_label
                p.sort_order = new_order
                p.start_day_before = start_d
                p.end_day_before = end_d
                p.color = color
                p.is_active_override = (p.key == active_key)
                p.save()

            ordered = list(TimelinePhase.objects.filter(wedding=wedding).order_by('sort_order', 'id'))
            for i, p in enumerate(ordered):
                if p.sort_order != i:
                    p.sort_order = i
                    p.save(update_fields=['sort_order'])

            if new_phase_spec:
                lbl, s_d, e_d, col = new_phase_spec
                TimelinePhase.objects.create(
                    wedding=wedding,
                    key=f"phase_{uuid.uuid4().hex[:6]}",
                    label=lbl,
                    start_day_before=s_d,
                    end_day_before=e_d,
                    color=col,
                    sort_order=len(ordered),
                )

        messages.success(request, 'Susunan tahapan & rentang waktu timeline berhasil diperbarui.')
    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def reset_or_apply_preset(request):
    """Reset tasks/phases to 0 (with mandatory non-overlapping H-minus ranges) or apply a timeline preset."""
    if request.method == 'POST':
        wedding = request.wedding
        mode = request.POST.get('mode', '')

        if mode == 'clear_tasks':
            deleted_count, _ = TaskMilestone.objects.filter(wedding=wedding).delete()
            messages.success(request, f'{deleted_count} tugas dibersihkan. Silakan gunakan Panduan Tugas Penting atau tambah tugas sendiri dari 0!')

        elif mode == 'start_from_zero':
            raw_labels = request.POST.getlist('custom_phase_labels')
            raw_starts = request.POST.getlist('custom_phase_starts')
            raw_ends = request.POST.getlist('custom_phase_ends')

            parsed_phases = []
            for idx, lbl_raw in enumerate(raw_labels):
                lbl = (lbl_raw or '').strip()
                if not lbl:
                    continue
                s_raw = raw_starts[idx] if idx < len(raw_starts) else ''
                e_raw = raw_ends[idx] if idx < len(raw_ends) else ''
                s_d, err1 = _parse_phase_day(s_raw, f'Mulai fase "{lbl}"')
                e_d, err2 = _parse_phase_day(e_raw, f'Selesai fase "{lbl}"')
                if err1 or err2:
                    messages.error(request, err1 or err2)
                    return redirect('operations-checklist:checklist')
                parsed_phases.append((lbl, s_d, e_d))

            if not parsed_phases:
                messages.error(request, 'Minimal harus ada 1 fase beserta rentang waktunya (H- mulai s/d H- selesai).')
                return redirect('operations-checklist:checklist')

            overlap_err = _validate_phase_ranges(parsed_phases)
            if overlap_err:
                messages.error(request, overlap_err)
                return redirect('operations-checklist:checklist')

            # Sort chronologically from earliest (largest H-minus) to latest
            parsed_phases.sort(key=lambda item: item[1], reverse=True)

            with transaction.atomic():
                TaskMilestone.objects.filter(wedding=wedding).delete()
                TimelinePhase.objects.filter(wedding=wedding).delete()
                for idx, (lbl, s_d, e_d) in enumerate(parsed_phases):
                    TimelinePhase.objects.create(
                        wedding=wedding,
                        key=f"custom_{idx + 1}_{uuid.uuid4().hex[:4]}",
                        label=lbl,
                        start_day_before=s_d,
                        end_day_before=e_d,
                        color=PHASE_COLOR_PALETTE[idx % len(PHASE_COLOR_PALETTE)],
                        sort_order=idx,
                        is_active_override=False,
                    )
            messages.success(request, 'Timeline & Tugas berhasil di-reset dari 0 dengan rentang fase baru!')

        elif mode == 'preset':
            preset_key = request.POST.get('preset_key', 'standard')
            task_handling = request.POST.get('task_handling', 'remap')
            preset = TIMELINE_PRESETS.get(preset_key, TIMELINE_PRESETS['standard'])
            new_phases = preset['phases']
            new_keys = [k for k, _, _, _, _ in new_phases]

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
                for old_idx, old_k in enumerate(old_keys):
                    if old_k not in new_keys:
                        mapped_idx = min(round((old_idx / max(len(old_keys) - 1, 1)) * (len(new_keys) - 1)), len(new_keys) - 1)
                        TaskMilestone.objects.filter(wedding=wedding, phase=old_k).update(phase=new_keys[mapped_idx])

            TimelinePhase.objects.filter(wedding=wedding).delete()
            for idx, (p_key, p_label, s_d, e_d, col) in enumerate(new_phases):
                TimelinePhase.objects.create(
                    wedding=wedding,
                    key=p_key,
                    label=p_label,
                    start_day_before=s_d,
                    end_day_before=e_d,
                    color=col,
                    sort_order=idx,
                )
            messages.success(request, f'Preset "{preset["name"]}" berhasil diterapkan!')

    return redirect('operations-checklist:checklist')


# Official Indonesian National Holidays (2025 - 2027) for red-date calendar markers
INDONESIA_HOLIDAYS = {
    # 2025
    '2025-01-01': 'Tahun Baru Masehi',
    '2025-01-27': 'Isra Mikraj Nabi Muhammad SAW',
    '2025-01-29': 'Tahun Baru Imlek 2576',
    '2025-03-29': 'Hari Suci Nyepi 1947',
    '2025-03-31': 'Hari Raya Idul Fitri 1446 H',
    '2025-04-01': 'Hari Raya Idul Fitri 1446 H',
    '2025-04-18': 'Wafat Yesus Kristus',
    '2025-04-20': 'Kebangkitan Yesus Kristus (Paskah)',
    '2025-05-01': 'Hari Buruh Internasional',
    '2025-05-12': 'Hari Raya Waisak 2569 BE',
    '2025-05-29': 'Kenaikan Yesus Kristus',
    '2025-06-01': 'Hari Lahir Pancasila',
    '2025-06-06': 'Hari Raya Idul Adha 1446 H',
    '2025-06-27': 'Tahun Baru Islam 1447 H',
    '2025-08-17': 'Hari Kemerdekaan RI',
    '2025-09-05': 'Maulid Nabi Muhammad SAW',
    '2025-12-25': 'Hari Raya Natal',
    # 2026
    '2026-01-01': 'Tahun Baru Masehi',
    '2026-01-16': 'Isra Mikraj Nabi Muhammad SAW',
    '2026-02-17': 'Tahun Baru Imlek 2577',
    '2026-03-19': 'Hari Suci Nyepi 1948',
    '2026-03-20': 'Hari Raya Idul Fitri 1447 H',
    '2026-03-21': 'Hari Raya Idul Fitri 1447 H',
    '2026-04-03': 'Wafat Yesus Kristus',
    '2026-04-05': 'Kebangkitan Yesus Kristus (Paskah)',
    '2026-05-01': 'Hari Buruh Internasional',
    '2026-05-14': 'Kenaikan Yesus Kristus',
    '2026-05-27': 'Hari Raya Idul Adha 1447 H',
    '2026-05-31': 'Hari Raya Waisak 2570 BE',
    '2026-06-01': 'Hari Lahir Pancasila',
    '2026-06-16': 'Tahun Baru Islam 1448 H',
    '2026-08-17': 'Hari Kemerdekaan RI',
    '2026-08-25': 'Maulid Nabi Muhammad SAW',
    '2026-12-25': 'Hari Raya Natal',
    # 2027
    '2027-01-01': 'Tahun Baru Masehi',
    '2027-01-05': 'Isra Mikraj Nabi Muhammad SAW',
    '2027-02-06': 'Tahun Baru Imlek 2578',
    '2027-03-09': 'Hari Suci Nyepi 1949',
    '2027-03-10': 'Hari Raya Idul Fitri 1448 H',
    '2027-03-11': 'Hari Raya Idul Fitri 1448 H',
    '2027-03-26': 'Wafat Yesus Kristus',
    '2027-03-28': 'Kebangkitan Yesus Kristus (Paskah)',
    '2027-05-01': 'Hari Buruh Internasional',
    '2027-05-06': 'Kenaikan Yesus Kristus',
    '2027-05-16': 'Hari Raya Idul Adha 1448 H',
    '2027-05-20': 'Hari Raya Waisak 2571 BE',
    '2027-06-01': 'Hari Lahir Pancasila',
    '2027-06-06': 'Tahun Baru Islam 1449 H',
    '2027-08-17': 'Hari Kemerdekaan RI',
    '2027-08-15': 'Maulid Nabi Muhammad SAW',
    '2027-12-25': 'Hari Raya Natal',
}


@login_required
@workspace_required
def calendar_view(request):
    """
    Visual Wedding Phase Calendar (/calendar/).
    Highlights each TimelinePhase range with color markers, marks Sundays & Indonesian
    National Holidays in red, displays task deadlines (TaskMilestone.due_date),
    and surfaces payment due dates for authorized roles (preserving WO/Crew financial privacy).
    """
    wedding = request.wedding
    today = timezone.localdate()
    wedding_date = wedding.wedding_date

    all_tasks = list(TaskMilestone.objects.filter(wedding=wedding))
    phase_objs = _ensure_wedding_phases(wedding, all_tasks_list=all_tasks)
    phase_label_map = {p.key: p.label for p in phase_objs}

    tasks_by_phase = defaultdict(list)
    for t in all_tasks:
        tasks_by_phase[t.phase].append(t)

    days_before_today = (wedding_date - today).days if wedding_date else None
    current_phase_key, current_phase_idx = _resolve_active_phase(phase_objs, days_before_today, tasks_by_phase)

    phase_cards = []
    phases_payload = []
    active_phase_card = None

    for idx, p in enumerate(phase_objs):
        p_tasks = tasks_by_phase.get(p.key, [])
        total = len(p_tasks)
        done = sum(1 for t in p_tasks if t.status == 'done')
        pct = round((done / total) * 100) if total > 0 else 0
        start_dt, end_dt = p.get_calendar_dates(wedding_date)
        is_current = (p.key == current_phase_key)

        card = {
            'key': p.key,
            'label': p.label,
            'color': p.color,
            'start_day_before': p.start_day_before,
            'end_day_before': p.end_day_before,
            'range_display': p.range_display,
            'start_date': start_dt,
            'end_date': end_dt,
            'start_iso': start_dt.isoformat() if start_dt else '',
            'end_iso': end_dt.isoformat() if end_dt else '',
            'total_tasks': total,
            'done_tasks': done,
            'progress': pct,
            'is_current': is_current,
            'is_override': p.is_active_override,
        }
        phase_cards.append(card)
        if is_current:
            active_phase_card = card

        phases_payload.append({
            'key': p.key,
            'label': p.label,
            'color': p.color,
            'start_day_before': p.start_day_before,
            'end_day_before': p.end_day_before,
            'range_display': p.range_display,
            'start_iso': start_dt.isoformat() if start_dt else '',
            'end_iso': end_dt.isoformat() if end_dt else '',
            'total_tasks': total,
            'done_tasks': done,
            'progress': pct,
            'is_current': is_current,
        })

    events_payload = []

    # 1. Task Deadlines (visible to all workspace roles: Pengantin, WO, Crew)
    for t in all_tasks:
        if t.due_date:
            events_payload.append({
                'date': t.due_date.isoformat(),
                'title': t.title,
                'phase_key': t.phase,
                'phase_label': phase_label_map.get(t.phase, t.phase),
                'status': t.status,
                'status_display': t.get_status_display(),
                'is_critical': t.is_critical,
                'is_overdue': bool(t.due_date < today and t.status != 'done'),
                'assignee': t.get_assignee_display(),
                'type': 'task',
            })

    # 2. Financial Payment Due Dates (ONLY if role can access finance!)
    role = getattr(request, 'wedding_role', None)
    can_access_finance = (
        role in ('owner', 'co_owner', 'admin')
        or (role == 'wo_manager' and wedding.allow_wo_budget_access)
    )
    if can_access_finance:
        from finances.models import BudgetItem
        due_items = (
            BudgetItem.objects.filter(category__wedding=wedding, due_date__isnull=False)
            .select_related('category')
            .order_by('due_date')
        )
        for item in due_items:
            events_payload.append({
                'date': item.due_date.isoformat(),
                'title': item.name,
                'category': item.category.name,
                'status': item.payment_status,
                'status_display': item.get_payment_status_display(),
                'amount': int(item.actual_cost or 0),
                'type': 'payment',
            })

    return render(request, 'operations/calendar.html', {
        'today': today,
        'today_iso': today.isoformat(),
        'wedding_date': wedding_date,
        'wedding_date_iso': wedding_date.isoformat() if wedding_date else '',
        'today_h_label': format_h_day(days_before_today) if days_before_today is not None else None,
        'days_before_today': days_before_today,
        'phase_cards': phase_cards,
        'active_phase': active_phase_card,
        'can_access_finance': can_access_finance,
        'phases_json': json.dumps(phases_payload),
        'events_json': json.dumps(events_payload),
        'holidays_json': json.dumps(INDONESIA_HOLIDAYS),
    })


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

    # Rundown events (evaluate once)
    rundown = list(RundownEvent.objects.filter(wedding=wedding))

    # Rundown sanity checks
    sanity_warnings = _check_rundown_sanity(rundown)

    # Assets (single query split in Python)
    assets = list(AssetCustodian.objects.filter(wedding=wedding))
    critical_assets = [a for a in assets if a.asset_category == 'critical']
    equipment_assets = [a for a in assets if a.asset_category == 'equipment']

    # Fabric entries (evaluate once)
    fabric_entries = list(FabricEntry.objects.filter(wedding=wedding))
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


# ============================================================
# FREE NOTES & MEETING MINUTES (/notes/)
# ============================================================

def _notes_role_flags(request):
    """Return (is_couple_or_admin, can_edit_notes) for current workspace request."""
    role = getattr(request, 'wedding_role', None)
    is_admin = bool(getattr(request, 'is_platform_admin', False))
    is_couple_or_admin = is_admin or role in ('owner', 'co_owner', 'admin')
    can_edit_notes = is_couple_or_admin or role == 'wo_manager'
    return is_couple_or_admin, can_edit_notes


def _visible_notes_qs(request):
    """
    Strictly isolate notes per wedding and enforce default privacy:
    - Owner / Co-Owner / Admin see all notes in the workspace.
    - WO Manager & Crew see all notes ONLY when wedding.allow_wo_notes_access is True,
      otherwise they only see notes with is_shared_with_team=True.
    """
    wedding = request.wedding
    is_couple_or_admin, _ = _notes_role_flags(request)
    qs = WeddingNote.objects.filter(wedding=wedding).select_related('created_by', 'updated_by')
    if not is_couple_or_admin and not wedding.allow_wo_notes_access:
        qs = qs.filter(is_shared_with_team=True)
    return qs


def _serialize_note(note):
    local_dt = timezone.localtime(note.updated_at) if note.updated_at else timezone.localtime()
    return {
        'id': note.pk,
        'title': note.title,
        'content': note.content,
        'category': note.category,
        'category_label': note.get_category_display(),
        'is_pinned': note.is_pinned,
        'is_shared_with_team': note.is_shared_with_team,
        'created_by': note.created_by.username if note.created_by else '-',
        'updated_by': note.updated_by.username if note.updated_by else (note.created_by.username if note.created_by else '-'),
        'updated_at_iso': local_dt.isoformat(),
        'updated_display': local_dt.strftime('%d %b %Y, %H:%M'),
        'updated_short': local_dt.strftime('%d %b'),
        'updated_time': local_dt.strftime('%H:%M'),
    }


@login_required
@workspace_required
def notes_view(request):
    """Split-pane Free Notes & Meeting Minutes workspace (/notes/)."""
    wedding = request.wedding
    is_couple_or_admin, can_edit_notes = _notes_role_flags(request)
    notes = [_serialize_note(n) for n in _visible_notes_qs(request)]

    config_payload = {
        'notes': notes,
        'categories': [{'key': k, 'label': v} for k, v in WeddingNote.CATEGORY_CHOICES],
        'isCoupleOrAdmin': is_couple_or_admin,
        'canEdit': can_edit_notes,
        'allowWoNotesAccess': bool(wedding.allow_wo_notes_access),
        'urls': {
            'create': '/notes/create/',
            'toggleAll': '/notes/toggle-all-visibility/',
        },
    }

    return render(request, 'operations/notes.html', {
        'notes_config_json': json.dumps(config_payload),
        'is_couple_or_admin': is_couple_or_admin,
        'can_edit_notes': can_edit_notes,
        'allow_wo_notes_access': bool(wedding.allow_wo_notes_access),
        'notes_count': len(notes),
    })


@login_required
@workspace_required
@require_POST
def note_create_api(request):
    """Create a new note. Default is private for Owner/Co-Owner, shared for WO Manager."""
    is_couple_or_admin, can_edit_notes = _notes_role_flags(request)
    if not can_edit_notes:
        return JsonResponse({'error': 'Crew operasional hanya memiliki akses baca pada catatan.'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        payload = {}

    valid_categories = dict(WeddingNote.CATEGORY_CHOICES)
    category = payload.get('category') if payload.get('category') in valid_categories else 'general'
    title = (payload.get('title') or '').strip()[:200]
    content = payload.get('content') or ''

    # Default private for Owner/Co-Owner; WO Manager notes are automatically shared with team
    is_shared = bool(payload.get('is_shared_with_team', False)) if is_couple_or_admin else True

    note = WeddingNote.objects.create(
        wedding=request.wedding,
        title=title,
        content=content,
        category=category,
        is_pinned=bool(payload.get('is_pinned', False)),
        is_shared_with_team=is_shared,
        created_by=request.user,
        updated_by=request.user,
    )
    return JsonResponse({'ok': True, 'note': _serialize_note(note)}, status=201)


@login_required
@workspace_required
@require_POST
def note_save_api(request, pk):
    """Auto-save note title, content, category, pin, and (couple/admin only) team visibility."""
    is_couple_or_admin, can_edit_notes = _notes_role_flags(request)
    if not can_edit_notes:
        return JsonResponse({'error': 'Akses ditolak.'}, status=403)

    note = get_object_or_404(_visible_notes_qs(request), pk=pk)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Payload tidak valid.'}, status=400)

    valid_categories = dict(WeddingNote.CATEGORY_CHOICES)
    if 'title' in payload:
        note.title = (payload.get('title') or '').strip()[:200]
    if 'content' in payload:
        note.content = payload.get('content') or ''
    if 'category' in payload and payload.get('category') in valid_categories:
        note.category = payload.get('category')
    if 'is_pinned' in payload:
        note.is_pinned = bool(payload.get('is_pinned'))
    if 'is_shared_with_team' in payload and is_couple_or_admin:
        note.is_shared_with_team = bool(payload.get('is_shared_with_team'))

    note.updated_by = request.user
    note.save()
    return JsonResponse({'ok': True, 'note': _serialize_note(note)})


@login_required
@workspace_required
@require_POST
def note_delete_api(request, pk):
    """Delete a note inside current wedding workspace."""
    _, can_edit_notes = _notes_role_flags(request)
    if not can_edit_notes:
        return JsonResponse({'error': 'Akses ditolak.'}, status=403)

    note = get_object_or_404(_visible_notes_qs(request), pk=pk)
    note.delete()
    return JsonResponse({'ok': True, 'deleted_id': pk})


@login_required
@workspace_required
@require_POST
def notes_toggle_all_visibility_api(request):
    """Owner/Co-Owner/Admin global toggle: show all workspace notes to WO & Crew."""
    is_couple_or_admin, _ = _notes_role_flags(request)
    if not is_couple_or_admin:
        return JsonResponse({'error': 'Hanya Pengantin (Owner/Co-Owner) yang dapat mengubah izin privasi catatan.'}, status=403)

    wedding = request.wedding
    wedding.allow_wo_notes_access = not wedding.allow_wo_notes_access
    wedding.save(update_fields=['allow_wo_notes_access'])
    return JsonResponse({
        'ok': True,
        'allow_wo_notes_access': wedding.allow_wo_notes_access,
    })
