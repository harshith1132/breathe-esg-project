from django.contrib import admin
from django import forms
from .models import Organization, UserProfile, DataSource, IngestionBatch, RawRecord, EmissionRecord, AuditLog

class DataSourceForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = '__all__'

    def clean_config(self):
        return self.cleaned_data.get('config') or {}

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    form = DataSourceForm
    list_display = ['name', 'source_type', 'organization', 'created_at']

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role']

@admin.register(IngestionBatch)
class IngestionBatchAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'status', 'row_count', 'error_count', 'uploaded_at']

@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['category', 'scope', 'quantity_normalized', 'unit_normalized', 'co2e_kg', 'review_status']
    list_filter = ['scope', 'review_status', 'category']

admin.site.register(RawRecord)
admin.site.register(AuditLog)
