"""
Core forms: Registration, Login, Join Workspace, Wedding Settings.
"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from core.models import Wedding


class RegisterForm(forms.ModelForm):
    """User registration with wedding workspace creation."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'wp-input',
        }),
    )
    password_confirm = forms.CharField(
        label='Konfirmasi Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Ulangi password',
            'class': 'wp-input',
        }),
    )
    groom_name = forms.CharField(
        label='Nama Pengantin Pria',
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Nama lengkap pria',
            'class': 'wp-input',
        }),
    )
    bride_name = forms.CharField(
        label='Nama Pengantin Wanita',
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Nama lengkap wanita',
            'class': 'wp-input',
        }),
    )
    wedding_date = forms.DateField(
        label='Tanggal Pernikahan',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'wp-input',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Username',
                'class': 'wp-input',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'Email',
                'class': 'wp-input',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('password_confirm'):
            raise forms.ValidationError('Password tidak cocok.')
        return cleaned_data


class LoginForm(AuthenticationForm):
    """Styled login form."""
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Username',
        'class': 'wp-input',
        'autofocus': True,
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Password',
        'class': 'wp-input',
    }))


class JoinWorkspaceForm(forms.Form):
    """Join an existing workspace via invite code."""
    invite_code = forms.CharField(
        label='Kode Undangan',
        max_length=8,
        widget=forms.TextInput(attrs={
            'placeholder': 'Masukkan 8-digit kode',
            'class': 'wp-input',
            'style': 'text-transform: uppercase; letter-spacing: 3px; text-align: center; font-size: 1.25rem;',
        }),
    )


class WeddingSettingsForm(forms.ModelForm):
    """Edit wedding workspace settings."""
    class Meta:
        model = Wedding
        fields = ['groom_name', 'bride_name', 'wedding_date', 'total_budget', 'budget_style']
        widgets = {
            'groom_name': forms.TextInput(attrs={'class': 'wp-input'}),
            'bride_name': forms.TextInput(attrs={'class': 'wp-input'}),
            'wedding_date': forms.DateInput(attrs={'type': 'date', 'class': 'wp-input'}),
            'total_budget': forms.NumberInput(attrs={'class': 'wp-input'}),
            'budget_style': forms.Select(attrs={'class': 'wp-input'}),
        }
