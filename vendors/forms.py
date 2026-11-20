"""
Vendor forms: VendorCandidate CRUD.
"""
from django import forms
from vendors.models import VendorCandidate


class VendorCandidateForm(forms.ModelForm):
    """Form for creating/editing vendor candidates."""
    class Meta:
        model = VendorCandidate
        fields = [
            'name', 'category', 'contact_pic', 'phone',
            'price_estimate', 'offer_link', 'status',
            'score_price', 'score_quality', 'score_facility', 'score_reputation',
            'weight_price', 'weight_quality', 'weight_facility', 'weight_reputation',
            'notes',
        ]
        labels = {
            'name': 'Nama Vendor *',
            'category': 'Kategori *',
            'contact_pic': 'PIC / Kontak',
            'phone': 'No. HP / WhatsApp',
            'price_estimate': 'Estimasi Harga (Rp)',
            'offer_link': 'Link Penawaran',
            'status': 'Status Keputusan',
            'score_price': 'Skor Harga (1-5)',
            'score_quality': 'Skor Kualitas (1-5)',
            'score_facility': 'Skor Fasilitas (1-5)',
            'score_reputation': 'Skor Reputasi (1-5)',
            'notes': 'Catatan',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama vendor'}),
            'category': forms.Select(attrs={'class': 'wp-input'}),
            'contact_pic': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama PIC'}),
            'phone': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': '08xxxxxxxxxx'}),
            'price_estimate': forms.NumberInput(attrs={'class': 'wp-input', 'placeholder': '0'}),
            'offer_link': forms.URLInput(attrs={'class': 'wp-input', 'placeholder': 'https://...'}),
            'status': forms.Select(attrs={'class': 'wp-input'}),
            'score_price': forms.NumberInput(attrs={'class': 'wp-input', 'min': '1', 'max': '5', 'placeholder': '1-5'}),
            'score_quality': forms.NumberInput(attrs={'class': 'wp-input', 'min': '1', 'max': '5', 'placeholder': '1-5'}),
            'score_facility': forms.NumberInput(attrs={'class': 'wp-input', 'min': '1', 'max': '5', 'placeholder': '1-5'}),
            'score_reputation': forms.NumberInput(attrs={'class': 'wp-input', 'min': '1', 'max': '5', 'placeholder': '1-5'}),
            'weight_price': forms.HiddenInput(),
            'weight_quality': forms.HiddenInput(),
            'weight_facility': forms.HiddenInput(),
            'weight_reputation': forms.HiddenInput(),
            'notes': forms.Textarea(attrs={'class': 'wp-input', 'rows': 2, 'placeholder': 'Catatan hasil survei / bonus paket (opsional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['price_estimate', 'score_price', 'score_quality', 'score_facility', 'score_reputation',
                  'weight_price', 'weight_quality', 'weight_facility', 'weight_reputation']:
            if f in self.fields:
                self.fields[f].required = False

    def clean_price_estimate(self):
        return self.cleaned_data.get('price_estimate') or 0

    def clean_score_price(self):
        return self.cleaned_data.get('score_price') or 3

    def clean_score_quality(self):
        return self.cleaned_data.get('score_quality') or 3

    def clean_score_facility(self):
        return self.cleaned_data.get('score_facility') or 3

    def clean_score_reputation(self):
        return self.cleaned_data.get('score_reputation') or 3

    def clean_weight_price(self):
        val = self.cleaned_data.get('weight_price')
        return 30 if val is None else val

    def clean_weight_quality(self):
        val = self.cleaned_data.get('weight_quality')
        return 30 if val is None else val

    def clean_weight_facility(self):
        val = self.cleaned_data.get('weight_facility')
        return 20 if val is None else val

    def clean_weight_reputation(self):
        val = self.cleaned_data.get('weight_reputation')
        return 20 if val is None else val
