"""
Finance forms: BudgetItem, ContributionShare.
"""
from django import forms
from finances.models import BudgetItem, BudgetCategory, ContributionShare


class BudgetCategoryConfigForm(forms.ModelForm):
    allocation_percentage = forms.DecimalField(
        min_value=0, max_value=100, max_digits=5, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'wp-input', 'style': 'padding-right: 30px;', 'step': 'any'}),
        error_messages={'max_value': 'Maksimal 100%'}
    )
    allocated_budget = forms.DecimalField(
        min_value=0, max_digits=15, decimal_places=0, required=False,
        widget=forms.NumberInput(attrs={'class': 'wp-input', 'step': 'any'})
    )

    class Meta:
        model = BudgetCategory
        fields = ['allocation_percentage', 'allocated_budget']

    def clean_allocation_percentage(self):
        return self.cleaned_data.get('allocation_percentage') or 0

    def clean_allocated_budget(self):
        return self.cleaned_data.get('allocated_budget') or 0


class BudgetItemForm(forms.ModelForm):
    """Form for creating/editing budget items."""
    class Meta:
        model = BudgetItem
        fields = [
            'category', 'name', 'vendor_name', 'allocated_amount',
            'actual_cost', 'paid_amount', 'payer', 'payment_status',
            'due_date', 'notes',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'wp-input'}),
            'name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama item pengeluaran'}),
            'vendor_name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama vendor (opsional)'}),
            'allocated_amount': forms.NumberInput(attrs={'class': 'wp-input', 'placeholder': '0'}),
            'actual_cost': forms.NumberInput(attrs={'class': 'wp-input', 'placeholder': '0'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'wp-input', 'placeholder': '0'}),
            'payer': forms.Select(attrs={'class': 'wp-input'}),
            'payment_status': forms.Select(attrs={'class': 'wp-input'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'wp-input'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'class': 'wp-input', 'rows': 2}),
        }

    def __init__(self, *args, wedding=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['allocated_amount', 'actual_cost', 'paid_amount', 'payer', 'payment_status']:
            if field_name in self.fields:
                self.fields[field_name].required = False
        if wedding:
            self.fields['category'].queryset = BudgetCategory.objects.filter(wedding=wedding)
            self.fields['category'].label_from_instance = lambda obj: obj.name

    def clean_allocated_amount(self):
        return self.cleaned_data.get('allocated_amount') or 0

    def clean_actual_cost(self):
        return self.cleaned_data.get('actual_cost') or 0

    def clean_paid_amount(self):
        return self.cleaned_data.get('paid_amount') or 0

    def clean_payer(self):
        return self.cleaned_data.get('payer') or 'joint'

    def clean_payment_status(self):
        return self.cleaned_data.get('payment_status') or 'unpaid'


class BudgetCategoryForm(forms.ModelForm):
    """Form for editing budget category allocation (supports both nominal Rp and percentage %)."""
    class Meta:
        model = BudgetCategory
        fields = ['name', 'icon', 'allocation_percentage', 'allocated_budget']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'wp-input'}),
            'icon': forms.TextInput(attrs={'class': 'wp-input', 'style': 'width: 60px;'}),
            'allocation_percentage': forms.NumberInput(attrs={
                'class': 'wp-input tabular-nums',
                'step': 'any',
                'min': '0',
                'max': '100',
            }),
            'allocated_budget': forms.NumberInput(attrs={
                'class': 'wp-input tabular-nums',
                'step': 'any',
                'min': '0',
                'placeholder': 'Nominal (Rp)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['icon'].required = False
        self.fields['allocation_percentage'].required = False
        self.fields['allocated_budget'].required = False

    def clean_icon(self):
        val = self.cleaned_data.get('icon')
        if not val and self.instance and self.instance.pk and self.instance.icon:
            return self.instance.icon
        return val or '<i data-lucide="folder"></i>'

    def clean_allocation_percentage(self):
        return self.cleaned_data.get('allocation_percentage') or 0

    def clean_allocated_budget(self):
        return self.cleaned_data.get('allocated_budget') or 0



from finances.models import SavingsGoal, SavingsDeposit

class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ['target_amount', 'monthly_deposit']
        widgets = {
            'target_amount': forms.NumberInput(attrs={'class': 'wp-input', 'placeholder': 'Misal: 100000000'}),
            'monthly_deposit': forms.NumberInput(attrs={'class': 'wp-input', 'placeholder': 'Misal: 5000000'}),
        }

class SavingsDepositForm(forms.ModelForm):
    class Meta:
        model = SavingsDeposit
        fields = ['amount', 'date', 'depositor', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'wp-input', 'placeholder': 'Misal: 2500000'}),
            'date': forms.DateInput(attrs={'class': 'wp-input', 'type': 'date'}, format='%Y-%m-%d'),
            'depositor': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Pria / Wanita / Bersama'}),
            'notes': forms.Textarea(attrs={'class': 'wp-input', 'rows': 2, 'placeholder': 'Catatan tambahan (opsional)'}),
        }
