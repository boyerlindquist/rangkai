"""
Finance views: Budget Dashboard, HTMX endpoints for CRUD.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum

from core.decorators import workspace_required, owner_required
from finances.models import BudgetCategory, BudgetItem, ContributionShare
from finances.forms import BudgetItemForm, BudgetCategoryForm, BudgetCategoryConfigForm
from django.forms import modelformset_factory


@login_required
@workspace_required
def budget_dashboard(request):
    """Finance & Cash Flow hub."""
    wedding = request.wedding
    categories = BudgetCategory.objects.filter(wedding=wedding).prefetch_related('items')

    # Budget summary
    items = BudgetItem.objects.filter(wedding=wedding)
    total_allocated = wedding.total_budget
    total_actual = items.aggregate(s=Sum('actual_cost'))['s'] or 0
    total_paid = items.aggregate(s=Sum('paid_amount'))['s'] or 0

    # Cash-out by month (for chart)
    cash_out_by_month = {}
    for item in items.filter(due_date__isnull=False).order_by('due_date'):
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

    context = {
        'categories': categories,
        'total_allocated': total_allocated,
        'total_actual': total_actual,
        'total_paid': total_paid,
        'total_remaining': total_actual - total_paid,
        'variance': total_allocated - total_actual,
        'cash_out_data': list(cash_out_by_month.values()),
        'shares': shares,
        'payer_breakdown': payer_breakdown,
        'form': BudgetItemForm(wedding=wedding),
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
def update_budget_item(request, pk):
    """HTMX endpoint: Update a budget item."""
    item = get_object_or_404(BudgetItem, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        form = BudgetItemForm(request.POST, instance=item, wedding=request.wedding)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, 'finances/partials/budget_item_row.html', {'item': item})
            return redirect('finances:dashboard')
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
    """HTMX endpoint: Quick toggle payment status."""
    item = get_object_or_404(BudgetItem, pk=pk, wedding=request.wedding)
    status_cycle = ['unpaid', 'dp_paid', 'partial', 'settled']
    current_idx = status_cycle.index(item.payment_status)
    item.payment_status = status_cycle[(current_idx + 1) % len(status_cycle)]
    item.save(update_fields=['payment_status'])
    if request.htmx:
        return render(request, 'finances/partials/budget_item_row.html', {'item': item})
    return redirect('finances:dashboard')


@login_required
@owner_required
def update_budget_category(request, pk):
    """HTMX endpoint: Update budget category allocation."""
    category = get_object_or_404(BudgetCategory, pk=pk, wedding=request.wedding)
    if request.method == 'POST':
        form = BudgetCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, 'finances/partials/budget_category_row.html', {'cat': category})
            return redirect('finances:dashboard')
    else:
        form = BudgetCategoryForm(instance=category)
    return render(request, 'finances/partials/budget_category_form.html', {'form': form, 'cat': category})


@login_required
@owner_required
def config_allocations(request):
    """HTMX endpoint: Configure all category allocations at once."""
    CategoryFormSet = modelformset_factory(
        BudgetCategory, 
        form=BudgetCategoryConfigForm,
        extra=0,
        can_delete=False
    )
    queryset = BudgetCategory.objects.filter(wedding=request.wedding).order_by('sort_order', 'name')
    
    if request.method == 'POST':
        formset = CategoryFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            return redirect('finances:dashboard')
    else:
        formset = CategoryFormSet(queryset=queryset)
        
    return render(request, 'finances/partials/config_allocations_form.html', {'formset': formset})



from finances.models import SavingsGoal, SavingsDeposit
from finances.forms import SavingsGoalForm, SavingsDepositForm
import datetime

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

    context = {
        'goal': goal,
        'deposits': goal.deposits.all(),
        'goal_form': SavingsGoalForm(instance=goal),
        'deposit_form': SavingsDepositForm(),
        'progress_percentage': progress_percentage,
        'estimated_months': estimated_months,
        'estimated_completion_date': estimated_completion_date,
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
            form.save()
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
