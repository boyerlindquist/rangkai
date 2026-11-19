"""
Core forms: Registration, Login, Join Workspace, Wedding Settings.
"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from core.models import Wedding


class RegisterForm(forms.ModelForm):
    """User registration supporting both creating a new workspace and joining via invite code."""
    mode = forms.ChoiceField(
        choices=[('create', 'Buat Workspace Baru'), ('join', 'Gabung Workspace')],
        initial='create',
        required=False,
        widget=forms.HiddenInput(),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Minimal 8 karakter',
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
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Nama panggilan / lengkap pria',
            'class': 'wp-input',
        }),
    )
    bride_name = forms.CharField(
        label='Nama Pengantin Wanita',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Nama panggilan / lengkap wanita',
            'class': 'wp-input',
        }),
    )
    wedding_date = forms.DateField(
        label='Tanggal Pernikahan (Opsional)',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'wp-input',
        }),
    )
    invite_code = forms.CharField(
        label='Kode Undangan (8 Karakter)',
        max_length=8,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'CONTOH: AB12CD34',
            'class': 'wp-input font-mono',
            'style': 'text-transform: uppercase; letter-spacing: 0.14em; text-align: center;',
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
                'placeholder': 'email@contoh.com',
                'class': 'wp-input',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('password_confirm'):
            self.add_error('password_confirm', 'Konfirmasi password tidak cocok.')

        mode = cleaned_data.get('mode') or 'create'
        cleaned_data['mode'] = mode

        if mode == 'join':
            code = (cleaned_data.get('invite_code') or '').strip().upper()
            cleaned_data['invite_code'] = code
            if not code:
                self.add_error('invite_code', 'Masukkan kode undangan 8 karakter dari pasangan/owner.')
            else:
                try:
                    cleaned_data['target_wedding'] = Wedding.objects.get(invite_code=code)
                except Wedding.DoesNotExist:
                    self.add_error('invite_code', 'Kode undangan tidak ditemukan. Periksa kembali kode dari pasanganmu.')
        else:
            if not (cleaned_data.get('groom_name') or '').strip():
                self.add_error('groom_name', 'Nama pengantin pria wajib diisi untuk membuat workspace baru.')
            if not (cleaned_data.get('bride_name') or '').strip():
                self.add_error('bride_name', 'Nama pengantin wanita wajib diisi untuk membuat workspace baru.')

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
