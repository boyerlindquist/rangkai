"""
Finance forms: BudgetItem, ContributionShare.
"""
from django import forms
from finances.models import BudgetItem, BudgetCategory, ContributionShare


class BudgetCategoryConfigForm(forms.ModelForm):
    allocation_percentage = forms.IntegerField(
        min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'wp-input', 'style': 'padding-right: 30px;'}),
        error_messages={'max_value': 'Maksimal 100%'}
    )

    class Meta:
        model = BudgetCategory
        fields = ['allocation_percentage']


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
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'wp-input'}),
            'notes': forms.Textarea(attrs={'class': 'wp-input', 'rows': 2}),
        }

    def __init__(self, *args, wedding=None, **kwargs):
        super().__init__(*args, **kwargs)
        if wedding:
            self.fields['category'].queryset = BudgetCategory.objects.filter(wedding=wedding)
            self.fields['category'].label_from_instance = lambda obj: obj.name


class BudgetCategoryForm(forms.ModelForm):
    """Form for editing budget category allocation."""
    class Meta:
        model = BudgetCategory
        fields = ['name', 'icon', 'allocation_percentage']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'wp-input'}),
            'icon': forms.TextInput(attrs={'class': 'wp-input', 'style': 'width: 60px;'}),
            'allocation_percentage': forms.NumberInput(attrs={
                'class': 'wp-input',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
        }



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
            'date': forms.DateInput(attrs={'class': 'wp-input', 'type': 'date'}),
            'depositor': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Pria / Wanita / Bersama'}),
            'notes': forms.Textarea(attrs={'class': 'wp-input', 'rows': 2, 'placeholder': 'Catatan tambahan (opsional)'}),
        }
