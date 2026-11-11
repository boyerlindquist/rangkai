"""
Finance views: Budget Dashboard, HTMX endpoints for CRUD.
"""
import math
import datetime
import json
from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum

from core.decorators import workspace_required, owner_required
from finances.models import BudgetCategory, BudgetItem, ContributionShare, SavingsGoal, SavingsDeposit
from finances.forms import BudgetItemForm, BudgetCategoryForm, BudgetCategoryConfigForm, SavingsGoalForm, SavingsDepositForm
from django.forms import modelformset_factory


def _compute_financial_state(wedding):
    """
    Central financial engine connecting:
    1. SavingsGoal (Dana Terkumpul & Rate Tabungan Bulanan)
    2. BudgetCategory (Rencana Pagu Nominal & Persentase)
    3. BudgetItem (Realisasi Kesepakatan Vendor & Dana Sudah Terpakai/Dibayar)
    """
    goal, _ = SavingsGoal.objects.get_or_create(wedding=wedding)

    # Auto-initialize total_budget from savings target if total_budget is still 0
    if not wedding.total_budget and goal.target_amount and goal.target_amount > 0:
        wedding.total_budget = goal.target_amount
        wedding.save(update_fields=['total_budget'])

    categories = list(BudgetCategory.objects.filter(wedding=wedding).prefetch_related('items'))
    items = list(BudgetItem.objects.filter(wedding=wedding).select_related('category'))

    total_saved = int(goal.total_saved or 0)
    monthly_saving_rate = int(goal.monthly_deposit or 0)
    savings_target = int(goal.target_amount or 0)

    total_cat_planned = int(sum(int(c.allocated_amount or 0) for c in categories))
    total_allocated = int(wedding.total_budget or total_cat_planned or 0)
    total_actual = int(sum(int(i.actual_cost or 0) for i in items))
    total_paid = int(sum(int(i.paid_amount or 0) for i in items))
    total_remaining = max(0, total_actual - total_paid)

    # Cash pool math (using Dana Terkumpul from Tabungan)
    available_cash = total_saved - total_paid
    available_cash_positive = max(0, available_cash)
    is_cash_deficit = available_cash < 0
    cash_deficit_amount = abs(available_cash) if is_cash_deficit else 0

    # Overall budget requirement & shortfall against Dana Terkumpul
    effective_total_need = max(total_allocated, total_actual, total_cat_planned)
    shortfall_from_saved = max(0, effective_total_need - total_saved)
    shortfall_vs_plan = max(0, total_allocated - total_saved)
    shortfall_vs_actual = max(0, total_actual - total_saved)
    surplus_from_saved = max(0, total_saved - effective_total_need)

    saved_vs_need_pct = min(100, round((total_saved / effective_total_need) * 100, 1)) if effective_total_need > 0 else (100 if total_saved > 0 else 0)
    paid_of_saved_pct = min(100, round((total_paid / total_saved) * 100, 1)) if total_saved > 0 else 0
    free_of_saved_pct = max(0, round(100 - paid_of_saved_pct, 1)) if total_saved > 0 else 0

    # Time-to-complete estimation based on monthly_saving_rate from Tabungan
    months_needed = 0
    estimated_finish_date = None
    if shortfall_from_saved > 0 and monthly_saving_rate > 0:
        months_needed = math.ceil(shortfall_from_saved / monthly_saving_rate)
        estimated_finish_date = datetime.date.today() + datetime.timedelta(days=months_needed * 30)

    days_remaining = wedding.days_remaining
    months_until_wedding = round(days_remaining / 30, 1) if (days_remaining and days_remaining > 0) else None
    required_monthly_for_dday = None
    is_saving_on_track = True
    if shortfall_from_saved > 0 and days_remaining and days_remaining > 0:
        eff_months = max(1.0, days_remaining / 30.0)
        required_monthly_for_dday = int(math.ceil(shortfall_from_saved / eff_months))
        if monthly_saving_rate > 0 and (months_needed * 30) > days_remaining:
            is_saving_on_track = False

    # Waterfall coverage check across categories using available_cash_positive
    running_free_cash = available_cash_positive
    ready_categories_count = 0
    partial_categories_count = 0
    shortfall_categories_count = 0

    for cat in categories:
        cat_planned = int(cat.allocated_amount or 0)
        cat_actual = int(cat.total_actual or 0)
        cat_paid = int(cat.total_paid or 0)
        cat_need = max(cat_planned, cat_actual)
        cat_unpaid_need = max(0, cat_need - cat_paid)

        covered_by_free_cash = min(running_free_cash, cat_unpaid_need)
        running_free_cash -= covered_by_free_cash

        cat_total_covered = cat_paid + covered_by_free_cash
        cat_shortfall = max(0, cat_need - cat_total_covered)
        cat_coverage_pct = min(100, round((cat_total_covered / cat_need) * 100)) if cat_need > 0 else 100
        cat_months_needed = math.ceil(cat_shortfall / monthly_saving_rate) if (cat_shortfall > 0 and monthly_saving_rate > 0) else 0

        if cat_need == 0:
            coverage_status = 'empty'
        elif cat_paid >= cat_need:
            coverage_status = 'settled'
            ready_categories_count += 1
        elif cat_shortfall == 0:
            coverage_status = 'ready'
            ready_categories_count += 1
        elif cat_total_covered > 0:
            coverage_status = 'partial'
            partial_categories_count += 1
        else:
            coverage_status = 'shortfall'
            shortfall_categories_count += 1

        cat.cat_planned = cat_planned
        cat.cat_actual = cat_actual
        cat.cat_paid = cat_paid
        cat.cat_need = cat_need
        cat.cat_unpaid_need = cat_unpaid_need
        cat.covered_by_free_cash = covered_by_free_cash
        cat.cat_total_covered = cat_total_covered
        cat.cat_shortfall = cat_shortfall
        cat.cat_coverage_pct = cat_coverage_pct
        cat.cat_months_needed = cat_months_needed
        cat.coverage_status = coverage_status

    paid_items = sorted([i for i in items if (i.paid_amount or 0) > 0], key=lambda x: x.paid_amount, reverse=True)
    unpaid_items = sorted([i for i in items if (x_rem := (x.actual_cost if (x := i) else 0) - (i.paid_amount or 0)) > 0], key=lambda x: (x.due_date or datetime.date.max))

    is_over_allocated = (total_cat_planned > total_allocated) and (total_allocated > 0)
    over_allocated_amount = (total_cat_planned - total_allocated) if is_over_allocated else 0
    over_allocated_pct = round((total_cat_planned / total_allocated) * 100, 1) if (is_over_allocated and total_allocated > 0) else 0

    is_under_allocated = (total_cat_planned < total_allocated) and (total_cat_planned > 0)
    under_allocated_amount = (total_allocated - total_cat_planned) if is_under_allocated else 0

    return {
        'goal': goal,
        'categories': categories,
        'items': items,
        'total_saved': total_saved,
        'monthly_saving_rate': monthly_saving_rate,
        'savings_target': savings_target,
        'total_cat_planned': total_cat_planned,
        'unallocated_plan': total_allocated - total_cat_planned,
        'total_allocated': total_allocated,
        'is_over_allocated': is_over_allocated,
        'over_allocated_amount': over_allocated_amount,
        'over_allocated_pct': over_allocated_pct,
        'is_under_allocated': is_under_allocated,
        'under_allocated_amount': under_allocated_amount,
        'total_actual': total_actual,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'variance': total_allocated - total_actual,
        'available_cash': available_cash,
        'available_cash_positive': available_cash_positive,
        'is_cash_deficit': is_cash_deficit,
        'cash_deficit_amount': cash_deficit_amount,
        'effective_total_need': effective_total_need,
        'shortfall_from_saved': shortfall_from_saved,
        'shortfall_vs_plan': shortfall_vs_plan,
        'shortfall_vs_actual': shortfall_vs_actual,
        'surplus_from_saved': surplus_from_saved,
        'saved_vs_need_pct': saved_vs_need_pct,
        'paid_of_saved_pct': paid_of_saved_pct,
        'free_of_saved_pct': free_of_saved_pct,
        'months_needed': months_needed,
        'estimated_finish_date': estimated_finish_date,
        'months_until_wedding': months_until_wedding,
        'required_monthly_for_dday': required_monthly_for_dday,
        'is_saving_on_track': is_saving_on_track,
        'ready_categories_count': ready_categories_count,
        'partial_categories_count': partial_categories_count,
        'shortfall_categories_count': shortfall_categories_count,
        'paid_items': paid_items,
        'unpaid_items': unpaid_items,
    }


@login_required
@workspace_required
def budget_dashboard(request):
    """Finance & Cash Flow hub integrated with Savings Pool."""
    wedding = request.wedding
    state = _compute_financial_state(wedding)
    categories = state['categories']
    items = state['items']

    # Cash-out by month (for chart)
    cash_out_by_month = {}
    for item in BudgetItem.objects.filter(wedding=wedding, due_date__isnull=False).order_by('due_date'):
        month_key = item.due_date.strftime('%Y-%m')
        month_label = item.due_date.strftime('%b %Y')
        if month_key not in cash_out_by_month:
            cash_out_by_month[month_key] = {'label': month_label, 'amount': 0}
        cash_out_by_month[month_key]['amount'] += int(item.actual_cost - item.paid_amount)

    # Split-bill shares
    shares = ContributionShare.objects.filter(wedding=wedding)

    # Payment status breakdown by payer
    payer_breakdown = {}
    for item in items:
        payer = item.get_payer_display()
        if payer not in payer_breakdown:
            payer_breakdown[payer] = {'actual': 0, 'paid': 0}
        payer_breakdown[payer]['actual'] += int(item.actual_cost)
        payer_breakdown[payer]['paid'] += int(item.paid_amount)

    for payer in payer_breakdown:
        payer_breakdown[payer]['remaining'] = payer_breakdown[payer]['actual'] - payer_breakdown[payer]['paid']

    # 3-Layer Sankey: Sumber Dana (Payer) -> Kategori (Category) -> Item Pengeluaran
    payer_cat_map = defaultdict(int)
    cat_item_links = []
    seen_nodes = set()

    payer_display_names = set(dict(BudgetItem.PAYER_CHOICES).values())
    payer_display_names.add('Belum Ada Sumber Dana')
    cat_names = set(c.name for c in categories)
    seen_nodes.update(payer_display_names)
    seen_nodes.update(cat_names)

    sankey_raw_data = []
    category_unallocated = []

    for cat in categories:
        cat_alloc = int(cat.allocated_amount or 0)
        items = list(cat.items.all())
        valid_items = [
            i for i in items
            if (i.actual_cost and i.actual_cost > 0) or (i.allocated_amount and i.allocated_amount > 0)
        ]

        total_items_cost = sum(
            int(i.actual_cost if i.actual_cost and i.actual_cost > 0 else i.allocated_amount)
            for i in valid_items
        )

        # Layer 2 -> Layer 3: Category -> Items
        for item in valid_items:
            amount = int(item.actual_cost if item.actual_cost and item.actual_cost > 0 else item.allocated_amount)
            payer = item.get_payer_display()

            payer_cat_map[(payer, cat.name)] += amount

            # Disambiguate item name if it collides with another node
            item_label = item.name.strip() or f"Item #{item.id}"
            while item_label in seen_nodes:
                item_label += '\u200b'
            seen_nodes.add(item_label)

            cat_item_links.append({
                'from': cat.name,
                'to': item_label,
                'weight': amount,
                'payer': payer,
                'layer': 2,
            })

        unallocated_in_cat = max(0, cat_alloc - total_items_cost)
        if unallocated_in_cat > 0:
            category_unallocated.append((cat.name, unallocated_in_cat))

    # Allocate unallocated ceiling portions:
    # First from Tabungan Bersama up to its target budget capacity,
    # and any excess (over-allocation) from 'Belum Ada Sumber Dana'
    total_joint_budget = int(wedding.total_budget or state.get('savings_target', 0) or 0)
    tabungan_spent_on_items = sum(amount for (payer, cat_name), amount in payer_cat_map.items() if payer == 'Tabungan Bersama')
    remaining_tabungan = max(0, total_joint_budget - tabungan_spent_on_items)

    for cat_name, unalloc_amt in category_unallocated:
        if total_joint_budget > 0:
            funded = min(unalloc_amt, remaining_tabungan)
            unfunded = unalloc_amt - funded
            remaining_tabungan -= funded
        else:
            funded = unalloc_amt
            unfunded = 0

        if funded > 0:
            payer_cat_map[('Tabungan Bersama', cat_name)] += funded
        if unfunded > 0:
            payer_cat_map[('Belum Ada Sumber Dana', cat_name)] += unfunded

    # Layer 1 -> Layer 2 records
    for (payer, cat_name), amount in payer_cat_map.items():
        if amount > 0:
            sankey_raw_data.append({
                'from': payer,
                'to': cat_name,
                'weight': amount,
                'payer': payer,
                'layer': 1,
            })

    sankey_raw_data.extend(cat_item_links)
    has_sankey_data = len(sankey_raw_data) > 0
    sankey_data_json = json.dumps(sankey_raw_data)

    category_forms = {cat.pk: BudgetItemForm(wedding=wedding, initial={'category': cat.pk}) for cat in categories}

    context = {
        **state,
        'cash_out_data': list(cash_out_by_month.values()),
        'shares': shares,
        'payer_breakdown': payer_breakdown,
        'sankey_data_json': sankey_data_json,
        'has_sankey_data': has_sankey_data,
        'form': BudgetItemForm(wedding=wedding),
        'category_forms': category_forms,
    }
    return render(request, 'finances/budget_dashboard.html', context)


@login_required
@owner_required
def add_budget_item(request):
    """HTMX endpoint: Add a new budget item."""
    wedding = request.wedding
    if request.method == 'POST':
        form = BudgetItemForm(request.POST, wedding=wedding)
        if form.is_valid():
            item = form.save(commit=False)
            item.wedding = wedding
            item.save()
            return redirect('finances:dashboard')
        else:
            return render(request, 'finances/partials/budget_item_form.html', {
                'form': form,
            })
    return redirect('finances:dashboard')


@login_required
@owner_required
def add_item_to_category(request, category_pk):
    """HTMX endpoint: Add a budget item pre-scoped to a specific category."""
    wedding = request.wedding
    category = get_object_or_404(BudgetCategory, pk=category_pk, wedding=wedding)
    if request.method == 'POST':
        form = BudgetItemForm(request.POST, wedding=wedding)
        if form.is_valid():
            item = form.save(commit=False)
            item.wedding = wedding
            item.save()
            return redirect('finances:dashboard')
        # On validation error, re-render the inline form
        return render(request, 'finances/partials/inline_item_form.html', {
            'form': form,
            'category': category,
        })
    return redirect('finances:dashboard')


@login_required
@owner_required
def update_budget_item(request, pk):
    """HTMX endpoint: Update a budget item."""
    item = get_object_or_404(BudgetItem, pk=pk, wedding=request.wedding)
    if request.GET.get('cancel') == '1':
        return render(request, 'finances/partials/budget_item_row.html', {'item': item})
    if request.method == 'POST':
        form = BudgetItemForm(request.POST, instance=item, wedding=request.wedding)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.payment_status == 'settled' and updated.paid_amount == 0 and updated.actual_cost > 0:
                updated.paid_amount = updated.actual_cost
            elif updated.paid_amount >= updated.actual_cost > 0:
                updated.payment_status = 'settled'
            updated.save()
            return redirect('finances:dashboard')
        response = render(request, 'finances/partials/budget_item_form.html', {'form': form, 'item': item})
        response['HX-Retarget'] = f'#edit-budget-item-{item.pk}'
        response['HX-Reselect'] = f'#edit-budget-item-{item.pk}'
        response['HX-Reswap'] = 'outerHTML'
        return response
    else:
        form = BudgetItemForm(instance=item, wedding=request.wedding)
    return render(request, 'finances/partials/budget_item_form.html', {'form': form, 'item': item})


@login_required
@owner_required
def delete_budget_item(request, pk):
    """HTMX endpoint: Delete a budget item."""
    item = get_object_or_404(BudgetItem, pk=pk, wedding=request.wedding)
    item.delete()
    return redirect('finances:dashboard')


@login_required
@owner_required
def toggle_payment_status(request, pk):
    """HTMX endpoint: Quick update or toggle payment status / payer & sync paid_amount."""
    item = get_object_or_404(BudgetItem, pk=pk, wedding=request.wedding)
    new_status = request.POST.get('payment_status') or request.GET.get('payment_status')
    new_payer = request.POST.get('payer') or request.GET.get('payer')
    update_fields = []

    if new_status and new_status in dict(BudgetItem.PAYMENT_STATUS_CHOICES):
        item.payment_status = new_status
        update_fields.append('payment_status')
        if new_status == 'settled' and item.actual_cost > 0:
            item.paid_amount = item.actual_cost
            update_fields.append('paid_amount')
        elif new_status == 'unpaid':
            item.paid_amount = 0
            update_fields.append('paid_amount')

    if new_payer and new_payer in dict(BudgetItem.PAYER_CHOICES):
        item.payer = new_payer
        update_fields.append('payer')

    if not new_status and not new_payer:
        if request.GET.get('settle') == '1' or request.POST.get('settle') == '1':
            item.payment_status = 'settled'
            if item.actual_cost > 0:
                item.paid_amount = item.actual_cost
            update_fields.extend(['payment_status', 'paid_amount'])
        else:
            status_cycle = ['unpaid', 'dp_paid', 'partial', 'settled']
            current_idx = status_cycle.index(item.payment_status) if item.payment_status in status_cycle else 0
            next_status = status_cycle[(current_idx + 1) % len(status_cycle)]
            item.payment_status = next_status
            if next_status == 'settled' and item.actual_cost > 0:
                item.paid_amount = item.actual_cost
            elif next_status == 'unpaid':
                item.paid_amount = 0
            update_fields.extend(['payment_status', 'paid_amount'])

    if update_fields:
        item.save(update_fields=list(set(update_fields)))

    if request.GET.get('from') == 'dashboard':
        return redirect('core:dashboard')
    return redirect('finances:dashboard')


def _sync_category_nominal_and_pct(cat, wedding):
    """Keep allocated_budget (Rp) and allocation_percentage (%) synchronized with wedding.total_budget."""
    total_budget = int(wedding.total_budget or 0)
    nominal = int(cat.allocated_budget or 0)
    pct = float(cat.allocation_percentage or 0)

    if nominal > 0 and total_budget > 0:
        cat.allocation_percentage = min(100, round((nominal / total_budget) * 100, 2))
    elif nominal == 0 and pct > 0 and total_budget > 0:
        cat.allocated_budget = int(round((total_budget * pct) / 100))
    elif nominal > 0 and total_budget == 0:
        # If total_budget was 0, initialize total_budget after saving
        pass


@login_required
@owner_required
def add_budget_category(request):
    """HTMX endpoint: Create a new budget category (by Nominal Rp or Percentage %)."""
    if request.method == 'POST':
        form = BudgetCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.wedding = request.wedding
            _sync_category_nominal_and_pct(cat, request.wedding)
            cat.save()
            if not request.wedding.total_budget and cat.allocated_budget > 0:
                request.wedding.total_budget = sum(c.allocated_amount for c in BudgetCategory.objects.filter(wedding=request.wedding))
                request.wedding.save(update_fields=['total_budget'])
    return redirect('finances:dashboard')


@login_required
@owner_required
def update_budget_category(request, pk):
    """HTMX endpoint: Update budget category allocation (by Nominal Rp or Percentage %)."""
    category = get_object_or_404(BudgetCategory, pk=pk, wedding=request.wedding)
    if request.GET.get('cancel') == '1':
        state = _compute_financial_state(request.wedding)
        annotated_cat = next((c for c in state['categories'] if c.pk == category.pk), category)
        return render(request, 'finances/partials/budget_category_row.html', {'cat': annotated_cat})
    if request.method == 'POST':
        form = BudgetCategoryForm(request.POST, instance=category)
        if form.is_valid():
            cat = form.save(commit=False)
            _sync_category_nominal_and_pct(cat, request.wedding)
            cat.save()
            if not request.wedding.total_budget and cat.allocated_budget > 0:
                request.wedding.total_budget = sum(c.allocated_amount for c in BudgetCategory.objects.filter(wedding=request.wedding))
                request.wedding.save(update_fields=['total_budget'])
            return redirect('finances:dashboard')
        response = render(request, 'finances/partials/budget_category_form.html', {'form': form, 'cat': category})
        response['HX-Retarget'] = f'#category-header-{category.pk}'
        response['HX-Reselect'] = f'#category-header-{category.pk}'
        response['HX-Reswap'] = 'outerHTML'
        return response
    else:
        form = BudgetCategoryForm(instance=category)
    return render(request, 'finances/partials/budget_category_form.html', {'form': form, 'cat': category})


@login_required
@owner_required
def delete_budget_category(request, pk):
    """HTMX endpoint: Delete a budget category."""
    category = get_object_or_404(BudgetCategory, pk=pk, wedding=request.wedding)
    category.delete()
    return redirect('finances:dashboard')


@login_required
@owner_required
def update_total_budget(request):
    """HTMX/POST endpoint: Quickly update wedding.total_budget & recalculate category nominals/percentages."""
    if request.method == 'POST':
        raw_val = request.POST.get('total_budget', '').strip().replace('.', '').replace(',', '')
        try:
            val = max(0, int(raw_val or 0))
            request.wedding.total_budget = val
            request.wedding.save(update_fields=['total_budget'])
            
            # Keep SavingsGoal target_amount synchronized
            goal, _ = SavingsGoal.objects.get_or_create(wedding=request.wedding)
            if goal.target_amount != val:
                goal.target_amount = val
                goal.save(update_fields=['target_amount'])

            categories = list(BudgetCategory.objects.filter(wedding=request.wedding))
            if val > 0:
                for cat in categories:
                    nom = int(cat.allocated_budget or 0)
                    pct = float(cat.allocation_percentage or 0)
                    if nom > 0:
                        # Recalculate percentage to reflect new total budget
                        cat.allocation_percentage = min(100, round((nom / val) * 100, 2))
                        cat.save(update_fields=['allocation_percentage'])
                    elif nom == 0 and pct > 0:
                        cat.allocated_budget = int(round((val * pct) / 100))
                        cat.save(update_fields=['allocated_budget'])
        except (ValueError, TypeError):
            pass
    return redirect('finances:dashboard')


@login_required
@owner_required
def config_allocations(request):
    """HTMX endpoint: Configure all category allocations (Nominal Rp & Percentage %) and total_budget at once."""
    CategoryFormSet = modelformset_factory(
        BudgetCategory, 
        form=BudgetCategoryConfigForm,
        extra=0,
        can_delete=False
    )
    queryset = BudgetCategory.objects.filter(wedding=request.wedding).order_by('sort_order', 'name')
    goal, _ = SavingsGoal.objects.get_or_create(wedding=request.wedding)
    
    if request.method == 'POST':
        raw_budget = request.POST.get('total_budget', '').strip().replace('.', '').replace(',', '')
        if raw_budget != '':
            try:
                tb_val = max(0, int(float(raw_budget)))
                request.wedding.total_budget = tb_val
                request.wedding.save(update_fields=['total_budget'])
                if goal.target_amount != tb_val:
                    goal.target_amount = tb_val
                    goal.save(update_fields=['target_amount'])
            except (ValueError, TypeError):
                pass
        formset = CategoryFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            instances = formset.save(commit=False)
            total_b = int(request.wedding.total_budget or 0)
            for inst in instances:
                nom = int(inst.allocated_budget or 0)
                pct = float(inst.allocation_percentage or 0)
                if nom > 0 and total_b > 0:
                    inst.allocation_percentage = min(100, round((nom / total_b) * 100, 2))
                elif nom == 0 and pct > 0 and total_b > 0:
                    inst.allocated_budget = int(round((total_b * pct) / 100))
                inst.save()
            if total_b == 0:
                sum_nom = sum(int(c.allocated_budget or 0) for c in BudgetCategory.objects.filter(wedding=request.wedding))
                if sum_nom > 0:
                    request.wedding.total_budget = sum_nom
                    request.wedding.save(update_fields=['total_budget'])
                    goal.target_amount = sum_nom
                    goal.save(update_fields=['target_amount'])
            return redirect('finances:dashboard')
    else:
        formset = CategoryFormSet(queryset=queryset)
        
    return render(request, 'finances/partials/config_allocations_form.html', {
        'formset': formset,
        'total_budget': int(request.wedding.total_budget or goal.target_amount or 0),
        'total_saved': int(goal.total_saved or 0),
        'savings_target': int(goal.target_amount or 0),
    })

@login_required
@workspace_required
def savings_tracker_view(request):
    """Joint Savings Tracker dashboard."""
    wedding = request.wedding
    goal, created = SavingsGoal.objects.get_or_create(wedding=wedding)
    
    # Calculate estimations
    estimated_months = 0
    estimated_completion_date = None
    
    if goal.remaining > 0 and goal.monthly_deposit > 0:
        estimated_months = int(goal.remaining / goal.monthly_deposit)
        if goal.remaining % goal.monthly_deposit > 0:
            estimated_months += 1
            
        today = datetime.date.today()
        # rough estimation adding 30 days per month
        estimated_completion_date = today + datetime.timedelta(days=estimated_months * 30)

    progress_percentage = 0
    if goal.target_amount > 0:
        progress_percentage = min(100, (goal.total_saved / goal.target_amount) * 100)

    # Prepare cumulative line chart data per depositor & total vs target
    deposits_asc = list(goal.deposits.all().order_by('date', 'created_at', 'id'))
    
    # Distinct depositors preserving order
    depositors = []
    for d in deposits_asc:
        dep_name = (d.depositor or 'Bersama').strip() or 'Bersama'
        if dep_name not in depositors:
            depositors.append(dep_name)

    # Group deposits by date and depositor
    date_deposits = defaultdict(lambda: defaultdict(int))
    for d in deposits_asc:
        dep_name = (d.depositor or 'Bersama').strip() or 'Bersama'
        date_key = d.date.strftime('%Y-%m-%d')
        date_deposits[date_key][dep_name] += int(d.amount)

    sorted_dates = sorted(date_deposits.keys())

    chart_labels = []
    total_series = []
    depositor_series = {dep: [] for dep in depositors}
    target_val = int(goal.target_amount or 0)
    target_series = []

    running_total = 0
    running_per_depositor = {dep: 0 for dep in depositors}

    if sorted_dates:
        # Initial starting point at 0
        chart_labels.append('Mulai')
        total_series.append(0)
        for dep in depositors:
            depositor_series[dep].append(0)
        target_series.append(target_val)

        for dt_str in sorted_dates:
            dt_obj = datetime.datetime.strptime(dt_str, '%Y-%m-%d').date()
            chart_labels.append(dt_obj.strftime('%d %b %Y'))

            for dep in depositors:
                amt = date_deposits[dt_str].get(dep, 0)
                running_per_depositor[dep] += amt
                depositor_series[dep].append(running_per_depositor[dep])
                running_total += amt

            total_series.append(running_total)
            target_series.append(target_val)

    chart_data = {
        'has_data': len(sorted_dates) > 0,
        'labels': chart_labels,
        'target_amount': target_val,
        'target_series': target_series,
        'total_series': total_series,
        'depositors': depositors,
        'depositor_series': depositor_series,
        'depositor_totals': {dep: running_per_depositor[dep] for dep in depositors},
    }

    context = {
        'goal': goal,
        'deposits': goal.deposits.all(),
        'goal_form': SavingsGoalForm(instance=goal),
        'deposit_form': SavingsDepositForm(),
        'progress_percentage': progress_percentage,
        'estimated_months': estimated_months,
        'estimated_completion_date': estimated_completion_date,
        'chart_data_json': json.dumps(chart_data),
        'chart_data': chart_data,
    }
    return render(request, 'finances/savings_tracker.html', context)


@login_required
@owner_required
def update_savings_goal(request):
    """HTMX endpoint to update savings target & monthly capability."""
    wedding = request.wedding
    goal = SavingsGoal.objects.get(wedding=wedding)
    if request.method == 'POST':
        form = SavingsGoalForm(request.POST, instance=goal)
        if form.is_valid():
            goal = form.save()
            # Keep wedding.total_budget synchronized if target_amount changed
            if goal.target_amount and int(goal.target_amount) > 0:
                if wedding.total_budget != int(goal.target_amount):
                    wedding.total_budget = int(goal.target_amount)
                    wedding.save(update_fields=['total_budget'])
            return redirect('finances:savings_tracker')
    return redirect('finances:savings_tracker')


@login_required
@owner_required
def add_savings_deposit(request):
    """HTMX endpoint to add a new deposit."""
    wedding = request.wedding
    goal = SavingsGoal.objects.get(wedding=wedding)
    if request.method == 'POST':
        form = SavingsDepositForm(request.POST)
        if form.is_valid():
            deposit = form.save(commit=False)
            deposit.goal = goal
            deposit.save()
            return redirect('finances:savings_tracker')
    return redirect('finances:savings_tracker')


@login_required
@owner_required
def update_savings_deposit(request, pk):
    """Endpoint to update an existing savings deposit."""
    deposit = get_object_or_404(SavingsDeposit, pk=pk, goal__wedding=request.wedding)
    if request.method == 'POST':
        form = SavingsDepositForm(request.POST, instance=deposit)
        if form.is_valid():
            form.save()
    return redirect('finances:savings_tracker')


@login_required
@owner_required
def delete_savings_deposit(request, pk):
    """HTMX/Standard endpoint to delete a deposit."""
    deposit = get_object_or_404(SavingsDeposit, pk=pk, goal__wedding=request.wedding)
    deposit.delete()
    return redirect('finances:savings_tracker')
