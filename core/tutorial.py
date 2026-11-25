"""
Interactive Guided Tutorial ("Tur Praktik Rangkai") service helpers:
- Per-membership state persistence
- Cross-request HTMX event emission (supports both 200 partials and 302 redirects)
- Safe, tenant-scoped sample data creation & surgical cleanup
"""
import json
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone


def _merge_hx_trigger(response, event_name, payload):
    """Attach or merge an event into the HX-Trigger response header."""
    existing = response.get('HX-Trigger')
    data = {}
    if existing:
        try:
            parsed = json.loads(existing)
            if isinstance(parsed, dict):
                data = parsed
            else:
                data[str(existing)] = True
        except (ValueError, TypeError):
            data[str(existing)] = True
    data[event_name] = payload
    response['HX-Trigger'] = json.dumps(data)
    return response


def emit_tutorial_event(request, response, action_key):
    """
    Notify the interactive tutorial engine that the user completed an action
    (e.g., 'savings_saved', 'budget_saved', 'vendor_saved', 'guest_saved', 'task_saved').
    Handles both direct 200 HTMX responses and 302 redirect responses seamlessly.
    """
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return response
    if not getattr(request, 'wedding', None):
        return response

    if response.status_code in (301, 302):
        request.session['tutorial_pending_event'] = action_key
    elif response.status_code == 200:
        _merge_hx_trigger(response, 'tutorialEvent', {'action': action_key})
    return response


def get_tutorial_membership(request):
    """Return the active WeddingMembership for the current user & wedding without redundant queries."""
    wedding = getattr(request, 'wedding', None)
    if not wedding or not getattr(request, 'user', None) or not request.user.is_authenticated:
        return None
    active = getattr(request, 'active_membership', None)
    if active and active.wedding_id == wedding.id:
        return active
    from core.models import WeddingMembership
    membership = WeddingMembership.objects.filter(user=request.user, wedding=wedding).first()
    request.active_membership = membership
    return membership


def _count_sample_records(state):
    samples = (state or {}).get('sample_records') or {}
    total = 0
    for key in ('savings_deposit_ids', 'budget_item_ids', 'vendor_ids', 'guest_ids', 'sample_task_ids', 'task_toggled'):
        total += len(samples.get(key) or [])
    if samples.get('savings_goal_prev'):
        total += 1
    return total


def get_tutorial_context(request):
    """Build lightweight tutorial state dict for template context & JSON API."""
    wedding = getattr(request, 'wedding', None)
    role = getattr(request, 'wedding_role', None)
    if not wedding or not getattr(request, 'user', None) or not request.user.is_authenticated:
        return None

    membership = get_tutorial_membership(request)
    if membership:
        status = membership.tutorial_status or 'not_started'
        step = membership.tutorial_step or 0
        state = membership.tutorial_state or {}
    else:
        # Platform admin inspecting a client workspace without direct membership
        sess = request.session.get(f'admin_tutorial_{wedding.pk}') or {}
        status = sess.get('status', 'dismissed')
        step = sess.get('step', 0)
        state = sess.get('state', {})

    completed_missions = state.get('completed_missions') or []
    sample_count = _count_sample_records(state)

    can_access_savings = role in ('owner', 'co_owner', 'admin')
    can_access_vendors = role in ('owner', 'co_owner', 'wo_manager', 'admin')
    can_access_finance = (
        role in ('owner', 'co_owner', 'admin')
        or (role == 'wo_manager' and bool(wedding.allow_wo_budget_access))
    )

    return {
        'status': status,
        'step': step,
        'phase': state.get('phase') or 'action',
        'completed_missions': completed_missions,
        'has_sample_data': sample_count > 0,
        'sample_count': sample_count,
        'pending_event': getattr(request, 'tutorial_pending_event', None),
        'wedding_id': wedding.pk,
        'role': role or 'owner',
        'can_access_savings': can_access_savings,
        'can_access_finance': can_access_finance,
        'can_access_vendors': can_access_vendors,
    }


def save_tutorial_membership_state(request, status=None, step=None, state=None):
    """Persist tutorial state to WeddingMembership (or session fallback for admin inspect)."""
    wedding = getattr(request, 'wedding', None)
    if not wedding:
        return None
    membership = get_tutorial_membership(request)
    if membership:
        update_fields = []
        if status is not None:
            membership.tutorial_status = status
            update_fields.append('tutorial_status')
        if step is not None:
            membership.tutorial_step = max(0, int(step))
            update_fields.append('tutorial_step')
        if state is not None:
            membership.tutorial_state = state
            update_fields.append('tutorial_state')
        if update_fields:
            membership.save(update_fields=update_fields)
        return membership
    else:
        key = f'admin_tutorial_{wedding.pk}'
        sess = request.session.get(key) or {'status': 'dismissed', 'step': 0, 'state': {}}
        if status is not None:
            sess['status'] = status
        if step is not None:
            sess['step'] = max(0, int(step))
        if state is not None:
            sess['state'] = state
        request.session[key] = sess
        request.session.modified = True
        return None


def create_sample_data_for_mission(request, mission_key):
    """
    Create realistic, clearly labeled sample data for a specific tutorial mission.
    Records created IDs in tutorial_state['sample_records'] for surgical cleanup.
    """
    wedding = request.wedding
    role = getattr(request, 'wedding_role', None)
    today = timezone.localdate()

    membership = get_tutorial_membership(request)
    if membership:
        state = dict(membership.tutorial_state or {})
    else:
        sess = request.session.get(f'admin_tutorial_{wedding.pk}') or {}
        state = dict(sess.get('state') or {})

    samples = dict(state.get('sample_records') or {})

    if mission_key == 'savings':
        if role not in ('owner', 'co_owner', 'admin'):
            return False, 'Peran Anda tidak memiliki akses ke Tabungan Bersama.'
        from finances.models import SavingsGoal, SavingsDeposit
        goal, _ = SavingsGoal.objects.get_or_create(wedding=wedding)
        if 'savings_goal_prev' not in samples:
            samples['savings_goal_prev'] = {
                'target_amount': int(goal.target_amount or 0),
                'monthly_deposit': int(goal.monthly_deposit or 0),
                'wedding_total_budget': int(wedding.total_budget or 0),
            }
        if not goal.target_amount or goal.target_amount == 0:
            goal.target_amount = Decimal('150000000')
        if not goal.monthly_deposit or goal.monthly_deposit == 0:
            goal.monthly_deposit = Decimal('10000000')
        goal.save()
        if not wedding.total_budget or wedding.total_budget == 0:
            wedding.total_budget = goal.target_amount
            wedding.save(update_fields=['total_budget'])

        dep = SavingsDeposit.objects.create(
            goal=goal,
            amount=Decimal('15000000'),
            date=today,
            depositor='Bersama',
            notes='[Contoh Tur] Setoran awal tabungan nikah',
        )
        ids = list(samples.get('savings_deposit_ids') or [])
        ids.append(dep.pk)
        samples['savings_deposit_ids'] = ids
        msg = 'Data contoh target tabungan (Rp 150 jt) & setoran awal (Rp 15 jt) berhasil ditambahkan.'

    elif mission_key == 'budget':
        can_access_finance = (
            role in ('owner', 'co_owner', 'admin')
            or (role == 'wo_manager' and bool(wedding.allow_wo_budget_access))
        )
        if not can_access_finance:
            return False, 'Peran Anda tidak memiliki akses ke Anggaran & Kas.'
        from finances.models import BudgetCategory, BudgetItem
        cat = BudgetCategory.objects.filter(wedding=wedding).order_by('sort_order', 'id').first()
        if not cat:
            cat = BudgetCategory.objects.create(
                wedding=wedding,
                name='Venue & Gedung',
                allocation_percentage=Decimal('30.00'),
                sort_order=1,
            )
        item = BudgetItem.objects.create(
            wedding=wedding,
            category=cat,
            name='[Contoh Tur] DP Venue Pernikahan',
            vendor_name='Grand Ballroom Contoh',
            allocated_amount=Decimal('30000000'),
            actual_cost=Decimal('25000000'),
            paid_amount=Decimal('10000000'),
            payer='joint',
            payment_status='dp_paid',
            due_date=today + timedelta(days=5),
            notes='Data contoh dari Tur Praktik Rangkai',
        )
        ids = list(samples.get('budget_item_ids') or [])
        ids.append(item.pk)
        samples['budget_item_ids'] = ids
        msg = 'Item contoh "DP Venue Pernikahan" (DP Rp 10 jt, jatuh tempo 5 hari lagi) berhasil ditambahkan.'

    elif mission_key == 'vendors':
        if role not in ('owner', 'co_owner', 'wo_manager', 'admin'):
            return False, 'Peran Anda tidak memiliki akses ke Direktori Vendor.'
        from vendors.models import VendorCandidate
        existing = VendorCandidate.objects.filter(wedding=wedding).first()
        vendor = VendorCandidate.objects.create(
            wedding=wedding,
            name='[Contoh Tur] Studio Foto Harmoni',
            category='documentation',
            contact_pic='Raka (Contoh)',
            phone='081234567890',
            price_estimate=Decimal('18000000'),
            status='shortlist',
            score_price=4,
            score_quality=5,
            score_facility=4,
            score_reputation=5,
            weight_price=existing.weight_price if existing else 35,
            weight_quality=existing.weight_quality if existing else 30,
            weight_facility=existing.weight_facility if existing else 20,
            weight_reputation=existing.weight_reputation if existing else 15,
            notes='Data contoh dari Tur Praktik Rangkai',
        )
        ids = list(samples.get('vendor_ids') or [])
        ids.append(vendor.pk)
        samples['vendor_ids'] = ids
        msg = 'Kandidat vendor contoh "Studio Foto Harmoni" berhasil ditambahkan.'

    elif mission_key == 'guests':
        from guests.models import Guest
        guest = Guest.objects.create(
            wedding=wedding,
            name='[Contoh Tur] Keluarga Pak Budi',
            phone='081298765432',
            relation_side='groom_family',
            category='vip',
            pax_allocation=4,
            rsvp_status='attending',
            notes='Data contoh dari Tur Praktik Rangkai',
        )
        ids = list(samples.get('guest_ids') or [])
        ids.append(guest.pk)
        samples['guest_ids'] = ids
        msg = 'Tamu contoh "Keluarga Pak Budi" (4 pax, VIP, Hadir) berhasil ditambahkan.'

    elif mission_key == 'tasks':
        from operations.models import TaskMilestone
        task = TaskMilestone.objects.filter(wedding=wedding).exclude(status='done').order_by('sort_order', 'id').first()
        if task:
            toggled = list(samples.get('task_toggled') or [])
            if not any(t.get('id') == task.pk for t in toggled):
                toggled.append({'id': task.pk, 'prev_status': task.status})
            task.status = 'done'
            task.save(update_fields=['status'])
            samples['task_toggled'] = toggled
            msg = f'Tugas "{task.title}" berhasil ditandai selesai sebagai contoh.'
        else:
            task = TaskMilestone.objects.create(
                wedding=wedding,
                title='[Contoh Tur] Finalisasi konsep acara',
                phase='d360',
                assignee='both',
                status='done',
                is_custom=True,
            )
            ids = list(samples.get('sample_task_ids') or [])
            ids.append(task.pk)
            samples['sample_task_ids'] = ids
            msg = 'Tugas contoh berhasil ditambahkan & ditandai selesai.'
    else:
        return False, 'Misi tutorial tidak dikenali.'

    state['sample_records'] = samples
    save_tutorial_membership_state(request, state=state)
    return True, msg


def cleanup_sample_data(request):
    """
    Surgically delete/revert all sample records created during the tutorial
    for this user's active wedding workspace. Never touches real user data.
    Also sweeps any leftover '[Contoh Tur]' records in this workspace as a safety net.
    """
    wedding = request.wedding
    membership = get_tutorial_membership(request)
    if membership:
        state = dict(membership.tutorial_state or {})
    else:
        sess = request.session.get(f'admin_tutorial_{wedding.pk}') or {}
        state = dict(sess.get('state') or {})

    samples = state.get('sample_records') or {}
    deleted = 0

    from finances.models import BudgetItem, SavingsDeposit, SavingsGoal
    from guests.models import Guest
    from vendors.models import VendorCandidate
    from operations.models import TaskMilestone

    # 1. Savings deposits (tracked IDs + '[Contoh Tur]' safety net)
    dep_qs = SavingsDeposit.objects.filter(goal__wedding=wedding)
    dep_ids = samples.get('savings_deposit_ids') or []
    if dep_ids:
        cnt, _ = dep_qs.filter(pk__in=dep_ids).delete()
        deleted += cnt
    cnt, _ = dep_qs.filter(notes__startswith='[Contoh Tur]').delete()
    deleted += cnt

    # 2. Revert SavingsGoal & Wedding total_budget if previously zero
    if samples.get('savings_goal_prev'):
        prev = samples['savings_goal_prev']
        goal = SavingsGoal.objects.filter(wedding=wedding).first()
        if goal:
            changed = False
            if prev.get('target_amount', 0) == 0 and int(goal.target_amount or 0) == 150000000:
                goal.target_amount = Decimal('0')
                changed = True
            if prev.get('monthly_deposit', 0) == 0 and int(goal.monthly_deposit or 0) == 10000000:
                goal.monthly_deposit = Decimal('0')
                changed = True
            if changed:
                goal.save()
        if prev.get('wedding_total_budget', 0) == 0 and int(wedding.total_budget or 0) == 150000000:
            wedding.total_budget = Decimal('0')
            wedding.save(update_fields=['total_budget'])
        deleted += 1

    # 3. Budget items (tracked IDs + '[Contoh Tur]' safety net)
    item_ids = samples.get('budget_item_ids') or []
    if item_ids:
        cnt, _ = BudgetItem.objects.filter(pk__in=item_ids, wedding=wedding).delete()
        deleted += cnt
    cnt, _ = BudgetItem.objects.filter(wedding=wedding, name__startswith='[Contoh Tur]').delete()
    deleted += cnt

    # 4. Vendors (tracked IDs + '[Contoh Tur]' safety net)
    vendor_ids = samples.get('vendor_ids') or []
    if vendor_ids:
        cnt, _ = VendorCandidate.objects.filter(pk__in=vendor_ids, wedding=wedding).delete()
        deleted += cnt
    cnt, _ = VendorCandidate.objects.filter(wedding=wedding, name__startswith='[Contoh Tur]').delete()
    deleted += cnt

    # 5. Guests (tracked IDs + '[Contoh Tur]' safety net)
    guest_ids = samples.get('guest_ids') or []
    if guest_ids:
        cnt, _ = Guest.objects.filter(pk__in=guest_ids, wedding=wedding).delete()
        deleted += cnt
    cnt, _ = Guest.objects.filter(wedding=wedding, name__startswith='[Contoh Tur]').delete()
    deleted += cnt

    # 6. Tasks (revert toggled tasks + delete '[Contoh Tur]' sample tasks)
    for entry in (samples.get('task_toggled') or []):
        t = TaskMilestone.objects.filter(pk=entry.get('id'), wedding=wedding).first()
        if t:
            t.status = entry.get('prev_status', 'todo')
            t.save(update_fields=['status'])
            deleted += 1

    task_ids = samples.get('sample_task_ids') or []
    if task_ids:
        cnt, _ = TaskMilestone.objects.filter(pk__in=task_ids, wedding=wedding).delete()
        deleted += cnt
    cnt, _ = TaskMilestone.objects.filter(wedding=wedding, title__startswith='[Contoh Tur]').delete()
    deleted += cnt

    state['sample_records'] = {}
    save_tutorial_membership_state(request, state=state)
    return deleted
