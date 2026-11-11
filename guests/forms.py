"""
Guest forms: Guest CRUD, CateringConfig.
"""
from django import forms
from guests.models import Guest, CateringConfig


class GuestForm(forms.ModelForm):
    """Form for creating/editing guest entries."""
    class Meta:
        model = Guest
        fields = ['name', 'phone', 'relation_side', 'category', 'pax_allocation', 'rsvp_status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama tamu undangan'}),
            'phone': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': '08xxxxxxxxxx'}),
            'relation_side': forms.Select(attrs={'class': 'wp-input'}),
            'category': forms.Select(attrs={'class': 'wp-input'}),
            'pax_allocation': forms.NumberInput(attrs={'class': 'wp-input', 'min': '1', 'max': '10'}),
            'rsvp_status': forms.Select(attrs={'class': 'wp-input'}),
            'notes': forms.Textarea(attrs={'class': 'wp-input', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pax_allocation'].required = False

    def clean_pax_allocation(self):
        return self.cleaned_data.get('pax_allocation') or 2


class CateringConfigForm(forms.ModelForm):
    """Form for configuring catering calculation parameters."""
    class Meta:
        model = CateringConfig
        fields = [
            'attendance_rate', 'pax_multiplier', 'vip_buffer_rate',
            'stall_portion_per_pax', 'stall_variety_count',
            'crew_count', 'akad_pax',
        ]
        widgets = {
            'attendance_rate': forms.NumberInput(attrs={'class': 'wp-input', 'step': '0.01'}),
            'pax_multiplier': forms.NumberInput(attrs={'class': 'wp-input', 'step': '0.1'}),
            'vip_buffer_rate': forms.NumberInput(attrs={'class': 'wp-input', 'step': '0.01'}),
            'stall_portion_per_pax': forms.NumberInput(attrs={'class': 'wp-input'}),
            'stall_variety_count': forms.NumberInput(attrs={'class': 'wp-input'}),
            'crew_count': forms.NumberInput(attrs={'class': 'wp-input'}),
            'akad_pax': forms.NumberInput(attrs={'class': 'wp-input'}),
        }
