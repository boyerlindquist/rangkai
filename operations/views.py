"""
Operations views: Checklist, Rundown, Asset Custodian, Fabric Calculator.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from collections import defaultdict

from core.decorators import workspace_required, owner_required
from operations.models import TaskMilestone, RundownEvent, AssetCustodian, FabricEntry
from operations.forms import TaskMilestoneForm, RundownEventForm, AssetCustodianForm, FabricEntryForm


# ============================================================
# CHECKLIST VIEWS (Route: /checklist/)
# ============================================================

@login_required
@workspace_required
def checklist_view(request):
    """Phased Checklist hub with accordion and filters."""
    wedding = request.wedding
    tasks = TaskMilestone.objects.filter(wedding=wedding)

    # Filter by assignee
    assignee_filter = request.GET.get('assignee', '')
    if assignee_filter:
        tasks = tasks.filter(assignee=assignee_filter)

    # Group by phase for accordion
    phases = TaskMilestone.PHASE_CHOICES
    grouped_tasks = {}
    for phase_key, phase_label in phases:
        phase_tasks = tasks.filter(phase=phase_key)
        total = phase_tasks.count()
        done = phase_tasks.filter(status='done').count()
        progress = round((done / total) * 100) if total > 0 else 0
        grouped_tasks[phase_key] = {
            'label': phase_label,
            'tasks': phase_tasks,
            'total': total,
            'done': done,
            'progress': progress,
        }

    # Overall stats
    all_tasks = TaskMilestone.objects.filter(wedding=wedding)
    total = all_tasks.count()
    done = all_tasks.filter(status='done').count()
    overall_progress = round((done / max(total, 1)) * 100)

    context = {
        'grouped_tasks': grouped_tasks,
        'phases': phases,
        'overall_progress': overall_progress,
        'total_tasks': total,
        'done_tasks': done,
        'assignee_filter': assignee_filter,
        'task_form': TaskMilestoneForm(),
    }
    return render(request, 'operations/checklist.html', context)


@login_required
@owner_required
def toggle_task_status(request, pk):
    """HTMX endpoint: Cycle task status (todo -> in_progress -> done)."""
    task = get_object_or_404(TaskMilestone, pk=pk, wedding=request.wedding)
    cycle = ['todo', 'in_progress', 'done']
    idx = cycle.index(task.status)
    task.status = cycle[(idx + 1) % len(cycle)]
    task.save(update_fields=['status'])
    if request.htmx:
        phase_tasks = TaskMilestone.objects.filter(wedding=request.wedding, phase=task.phase)
        total = phase_tasks.count()
        done = phase_tasks.filter(status='done').count()
        progress = int((done / total) * 100) if total > 0 else 0
        
        all_tasks = TaskMilestone.objects.filter(wedding=request.wedding)
        overall_total = all_tasks.count()
        overall_done = all_tasks.filter(status='done').count()
        overall_progress = int((overall_done / overall_total) * 100) if overall_total > 0 else 0
        
        context = {
            'task': task,
            'progress': progress,
            'phase_key': task.phase,
            'phase_label': task.get_phase_display(),
            'done_count': done,
            'total_count': total,
            'overall_progress': overall_progress,
            'overall_done': overall_done,
            'overall_total': overall_total,
        }
        return render(request, 'operations/partials/task_item.html', context)
    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def add_task(request):
    """HTMX endpoint: Add custom task."""
    if request.method == 'POST':
        form = TaskMilestoneForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.wedding = request.wedding
            task.is_custom = True
            task.save()
            if request.htmx:
                return redirect('operations-checklist:checklist')
            return redirect('operations-checklist:checklist')
    return redirect('operations-checklist:checklist')


@login_required
@owner_required
def delete_task(request, pk):
    """HTMX endpoint: Delete a custom task."""
    task = get_object_or_404(TaskMilestone, pk=pk, wedding=request.wedding, is_custom=True)
    task.delete()
    if request.htmx:
        return HttpResponse('')
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
            if request.htmx:
                return redirect('operations-hub:operations_hub')
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def delete_rundown_event(request, pk):
    event = get_object_or_404(RundownEvent, pk=pk, wedding=request.wedding)
    event.delete()
    if request.htmx:
        return HttpResponse('')
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
            if request.htmx:
                return redirect('operations-hub:operations_hub')
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def toggle_asset_status(request, pk):
    asset = get_object_or_404(AssetCustodian, pk=pk, wedding=request.wedding)
    cycle = ['pending', 'loaded', 'received', 'handed', 'packed']
    idx = cycle.index(asset.status)
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
            if request.htmx:
                return redirect('operations-hub:operations_hub')
    return redirect('operations-hub:operations_hub')


@login_required
@owner_required
def delete_fabric_entry(request, pk):
    entry = get_object_or_404(FabricEntry, pk=pk, wedding=request.wedding)
    entry.delete()
    if request.htmx:
        return HttpResponse('')
    return redirect('operations-hub:operations_hub')

@login_required
@owner_required
def update_task(request, pk):
    """HTMX endpoint: Update custom or template task."""
    task = get_object_or_404(TaskMilestone, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        form = TaskMilestoneForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, 'operations/partials/task_item.html', {'task': task})
            return redirect('operations-checklist:checklist')
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
    
    doc_form = DocumentRequirementForm()
    ses_form = SeserahanItemForm()
    
    context = {
        'documents': documents,
        'seserahan': seserahan,
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
def delete_document(request, pk):
    doc = get_object_or_404(DocumentRequirement, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        doc.delete()
    return redirect('operations-checklist:detail_checklists')

@login_required
@owner_required
def delete_seserahan(request, pk):
    ses = get_object_or_404(SeserahanItem, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        ses.delete()
    return redirect('operations-checklist:detail_checklists')


@login_required
@owner_required
def update_document(request, pk):
    doc = get_object_or_404(DocumentRequirement, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        form = DocumentRequirementForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            return render(request, 'operations/partials/doc_row.html', {'doc': doc})
    else:
        form = DocumentRequirementForm(instance=doc)
    return render(request, 'operations/partials/doc_form_inline.html', {'doc_form': form, 'doc': doc})

@login_required
@owner_required
def update_seserahan(request, pk):
    ses = get_object_or_404(SeserahanItem, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        form = SeserahanItemForm(request.POST, instance=ses)
        if form.is_valid():
            form.save()
            return render(request, 'operations/partials/ses_row.html', {'ses': ses})
    else:
        form = SeserahanItemForm(instance=ses)
    return render(request, 'operations/partials/ses_form_inline.html', {'ses_form': form, 'ses': ses})
