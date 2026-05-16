from django import forms
from .models import OutageReport

class OutageReportForm(forms.ModelForm):
    class Meta:
        model = OutageReport
        fields = [
            'outage_type', 'location_text', 'latitude', 'longitude',
            'description', 'contact_info', 'photo', 'is_anonymous', 'anonymous_name'
        ]
        widgets = {
            'outage_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'outageType'
            }),
            'location_text': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'locationText',
                'placeholder': 'e.g., Umudim Village, Abia State',
                'required': True
            }),
            'latitude': forms.HiddenInput(attrs={'id': 'latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'longitude'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please describe the outage... How long has it been? Any additional details?',
                'required': True
            }),
            'contact_info': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number or email (optional - for updates)'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'photoInput'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'isAnonymous'
            }),
            'anonymous_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name to display (optional)',
                'id': 'anonymousName'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_anonymous'].required = False
        self.fields['anonymous_name'].required = False
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
        self.fields['photo'].required = False
        self.fields['contact_info'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        is_anonymous = cleaned_data.get('is_anonymous')
        
        if not cleaned_data.get('location_text'):
            self.add_error('location_text', 'Please provide a location')
        
        return cleaned_data
    
    
class AdminReportUpdateForm(forms.ModelForm):
    class Meta:
        model = OutageReport
        fields = ['status', 'admin_notes', 'resolution_notes', 'estimated_restoration_time', 'assigned_to']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control', 'id': 'statusSelect'}),
            'admin_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 
                                                  'placeholder': 'Internal notes for team'}),
            'resolution_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                                       'placeholder': 'Notes to show user when resolved'}),
            'estimated_restoration_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'assigned_to': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Team/Person assigned'}),
        }