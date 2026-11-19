"""
Core forms: Registration, Login, Join Workspace, Checkout, WO Project, Wedding Settings.
"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from core.models import Wedding, WorkspaceInvitation, Order


def resolve_invite_code(code):
    """
    Resolve an 8-character invite code from WorkspaceInvitation (preferred)
    or fallback to legacy Wedding.invite_code (assigned as crew).
    Returns tuple: (wedding, target_role, invitation_obj_or_None, error_message_or_None)
    """
    code = (code or '').strip().upper()
    if not code:
        return None, None, None, 'Masukkan kode undangan 8 karakter.'

    inv = WorkspaceInvitation.objects.select_related('wedding').filter(code=code).first()
    if inv:
        if not inv.is_valid:
            return None, None, inv, 'Kode undangan sudah tidak aktif, kedaluwarsa, atau mencapai batas pemakaian.'
        return inv.wedding, inv.resolve_role_for_join(), inv, None

    wedding = Wedding.objects.filter(invite_code=code).first()
    if wedding:
        return wedding, 'crew', None, None

    return None, None, None, 'Kode undangan tidak ditemukan. Periksa kembali kode dari pengantin atau WO.'


class RegisterForm(forms.ModelForm):
    """User registration supporting creating a Wedding Owner workspace OR joining via role-bound invite code."""
    mode = forms.ChoiceField(
        choices=[('create', 'Buat Workspace Baru'), ('join', 'Gabung Workspace')],
        initial='create',
        required=False,
        widget=forms.HiddenInput(),
    )
    password = forms.CharField(
        min_length=8,
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
            wedding, target_role, invitation, err = resolve_invite_code(code)
            if err:
                self.add_error('invite_code', err)
            else:
                cleaned_data['target_wedding'] = wedding
                cleaned_data['target_role'] = target_role
                cleaned_data['target_invitation'] = invitation
        else:
            if not (cleaned_data.get('groom_name') or '').strip():
                self.add_error('groom_name', 'Nama pengantin pria wajib diisi untuk membuat workspace baru.')
            if not (cleaned_data.get('bride_name') or '').strip():
                self.add_error('bride_name', 'Nama pengantin wanita wajib diisi untuk membuat workspace baru.')

        return cleaned_data


class CheckoutForm(forms.ModelForm):
    """Simulated Payment Gateway checkout form for Wedding Owner or WO Manager packages."""
    plan_type = forms.ChoiceField(
        choices=Order.PLAN_CHOICES,
        initial='wedding_owner',
        widget=forms.HiddenInput(),
    )
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        initial='qris',
        widget=forms.RadioSelect(),
    )
    password = forms.CharField(
        min_length=8,
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
    # Couple-specific fields
    groom_name = forms.CharField(
        label='Nama Pengantin Pria',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Contoh: Dimas',
            'class': 'wp-input',
        }),
    )
    bride_name = forms.CharField(
        label='Nama Pengantin Wanita',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Contoh: Nadya',
            'class': 'wp-input',
        }),
    )
    wedding_date = forms.DateField(
        label='Perkiraan Tanggal Pernikahan (Opsional)',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'wp-input',
        }),
    )
    # WO-specific field
    organization_name = forms.CharField(
        label='Nama WO / Brand Organisasi',
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Contoh: Surya Wedding Organizer',
            'class': 'wp-input',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Username akun',
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

        plan = cleaned_data.get('plan_type') or 'wedding_owner'
        if plan == 'wedding_owner':
            if not (cleaned_data.get('groom_name') or '').strip():
                self.add_error('groom_name', 'Nama pengantin pria wajib diisi.')
            if not (cleaned_data.get('bride_name') or '').strip():
                self.add_error('bride_name', 'Nama pengantin wanita wajib diisi.')
        elif plan == 'wo_manager':
            if not (cleaned_data.get('organization_name') or '').strip():
                self.add_error('organization_name', 'Nama WO / brand wajib diisi untuk paket WO Manager.')
        return cleaned_data


class WOProjectCreateForm(forms.ModelForm):
    """Form for WO Manager to create a new client wedding project."""
    class Meta:
        model = Wedding
        fields = ['groom_name', 'bride_name', 'wedding_date', 'budget_style']
        widgets = {
            'groom_name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama Pengantin Pria'}),
            'bride_name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama Pengantin Wanita'}),
            'wedding_date': forms.DateInput(attrs={'type': 'date', 'class': 'wp-input'}),
            'budget_style': forms.Select(attrs={'class': 'wp-input'}),
        }


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
            'placeholder': 'CONTOH: AB12CD34',
            'class': 'wp-input font-mono',
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
