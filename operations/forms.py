"""
Operations forms: TaskMilestone, RundownEvent, AssetCustodian, FabricEntry.
"""
from django import forms
from operations.models import TaskMilestone, RundownEvent, AssetCustodian, FabricEntry


class TaskMilestoneForm(forms.ModelForm):
    """Form for creating custom task milestones."""
    class Meta:
        model = TaskMilestone
        fields = ['phase', 'category', 'title', 'assignee', 'is_critical', 'linked_tool']
        widgets = {
            'phase': forms.Select(attrs={'class': 'wp-input'}),
            'category': forms.Select(attrs={'class': 'wp-input'}),
            'title': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Judul tugas'}),
            'assignee': forms.Select(attrs={'class': 'wp-input'}),
            'linked_tool': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama tool terkait (opsional)'}),
        }


class RundownEventForm(forms.ModelForm):
    """Form for creating D-Day rundown entries."""
    class Meta:
        model = RundownEvent
        fields = ['start_time', 'end_time', 'activity', 'location', 'pic', 'notes']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'wp-input'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'wp-input'}),
            'activity': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama agenda'}),
            'location': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Lokasi'}),
            'pic': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'PIC Teknis'}),
            'notes': forms.Textarea(attrs={'class': 'wp-input', 'rows': 2}),
        }


class AssetCustodianForm(forms.ModelForm):
    """Form for tracking D-Day assets."""
    class Meta:
        model = AssetCustodian
        fields = ['name', 'asset_category', 'pic_name', 'pic_contact', 'vehicle_info', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama barang'}),
            'asset_category': forms.Select(attrs={'class': 'wp-input'}),
            'pic_name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama PIC pembawa'}),
            'pic_contact': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': '08xxxxxxxxxx'}),
            'vehicle_info': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Plat nomor / nama driver'}),
            'status': forms.Select(attrs={'class': 'wp-input'}),
            'notes': forms.Textarea(attrs={'class': 'wp-input', 'rows': 2}),
        }


class FabricEntryForm(forms.ModelForm):
    """Form for fabric yardage calculator entries."""
    class Meta:
        model = FabricEntry
        fields = ['recipient_name', 'gender', 'garment_type', 'size_category']
        widgets = {
            'recipient_name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama penerima seragam'}),
            'gender': forms.Select(attrs={'class': 'wp-input'}),
            'garment_type': forms.Select(attrs={'class': 'wp-input'}),
            'size_category': forms.Select(attrs={'class': 'wp-input'}),
        }



from operations.models import DocumentRequirement, SeserahanItem

class DocumentRequirementForm(forms.ModelForm):
    class Meta:
        model = DocumentRequirement
        fields = ['name', 'party', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama Dokumen'}),
            'party': forms.Select(attrs={'class': 'wp-input'}),
            'status': forms.Select(attrs={'class': 'wp-input'}),
            'notes': forms.Textarea(attrs={'class': 'wp-input', 'rows': 1}),
        }

class SeserahanItemForm(forms.ModelForm):
    class Meta:
        model = SeserahanItem
        fields = ['name', 'category', 'est_price', 'actual_price', 'status', 'pic', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Nama Barang'}),
            'category': forms.TextInput(attrs={'class': 'wp-input', 'placeholder': 'Kategori'}),
            'est_price': forms.NumberInput(attrs={'class': 'wp-input'}),
            'actual_price': forms.NumberInput(attrs={'class': 'wp-input'}),
            'status': forms.Select(attrs={'class': 'wp-input'}),
            'pic': forms.TextInput(attrs={'class': 'wp-input'}),
            'notes': forms.Textarea(attrs={'class': 'wp-input', 'rows': 1}),
        }
