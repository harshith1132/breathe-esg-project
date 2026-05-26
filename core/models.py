import uuid
from django.db import models
from django.contrib.auth.models import User


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=32, choices=[('admin','Admin'),('analyst','Analyst'),('viewer','Viewer')], default='analyst')

    def __str__(self):
        return f"{self.user.email} ({self.organization.slug})"


class DataSource(models.Model):
    SOURCE_TYPES = [('SAP','SAP Fuel & Procurement'),('UTILITY','Utility Electricity'),('TRAVEL','Corporate Travel')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='data_sources')
    source_type = models.CharField(max_length=16, choices=SOURCE_TYPES)
    name = models.CharField(max_length=255)
    config = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organization.slug} / {self.name}"


class IngestionBatch(models.Model):
    STATUS = [('PENDING','Pending'),('PROCESSING','Processing'),('DONE','Done'),('FAILED','Failed')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='batches')
    data_source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, related_name='batches')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=512)
    file = models.FileField(upload_to='uploads/%Y/%m/')
    status = models.CharField(max_length=16, choices=STATUS, default='PENDING')
    row_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.original_filename} ({self.status})"


class RawRecord(models.Model):
    PARSE_STATUS = [('OK','Parsed successfully'),('WARNING','Parsed with warnings'),('ERROR','Parse failed')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='raw_records')
    row_number = models.IntegerField()
    raw_data = models.JSONField()
    parse_status = models.CharField(max_length=10, choices=PARSE_STATUS, default='OK')
    parse_errors = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('batch', 'row_number')


class EmissionRecord(models.Model):
    SCOPE_CHOICES = [(1,'Scope 1 - Direct emissions'),(2,'Scope 2 - Purchased electricity'),(3,'Scope 3 - Value chain')]
    CATEGORY_CHOICES = [('S1_FUEL_STATIONARY','Stationary combustion'),('S1_FUEL_MOBILE','Mobile combustion'),('S2_ELECTRICITY','Purchased electricity'),('S3_BUSINESS_TRAVEL_FLIGHT','Business travel - flight'),('S3_BUSINESS_TRAVEL_HOTEL','Business travel - hotel'),('S3_BUSINESS_TRAVEL_GROUND','Business travel - ground'),('S3_PROCUREMENT','Upstream procurement')]
    REVIEW_STATUS = [('PENDING','Pending review'),('FLAGGED','Flagged'),('APPROVED','Approved'),('REJECTED','Rejected')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='emission_records')
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='emission_records')
    raw_record = models.OneToOneField(RawRecord, on_delete=models.CASCADE, related_name='emission_record', null=True)
    data_source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True)
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category = models.CharField(max_length=64, choices=CATEGORY_CHOICES)
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    facility_code = models.CharField(max_length=128, blank=True)
    cost_center = models.CharField(max_length=128, blank=True)
    vendor_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    quantity_raw = models.DecimalField(max_digits=18, decimal_places=6)
    unit_raw = models.CharField(max_length=32)
    quantity_normalized = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    unit_normalized = models.CharField(max_length=32, default='')
    emission_factor = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    emission_factor_unit = models.CharField(max_length=64, blank=True)
    emission_factor_source = models.CharField(max_length=255, blank=True)
    co2e_kg = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    flagged_reasons = models.JSONField(default=list)
    is_estimated = models.BooleanField(default=False)
    review_status = models.CharField(max_length=16, choices=REVIEW_STATUS, default='PENDING')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_records')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    is_edited = models.BooleanField(default=False)
    original_values = models.JSONField(default=dict)
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='locked_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['organization','scope']),models.Index(fields=['organization','review_status']),models.Index(fields=['batch'])]

    def __str__(self):
        return f"{self.category} | {self.quantity_normalized} {self.unit_normalized} | {self.review_status}"


class AuditLog(models.Model):
    ACTION_CHOICES = [('CREATED','Record created'),('EDITED','Field edited'),('APPROVED','Approved'),('REJECTED','Rejected'),('FLAGGED','Flagged'),('LOCKED','Locked'),('NOTE_ADDED','Note added')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    emission_record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_log')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    old_values = models.JSONField(default=dict)
    new_values = models.JSONField(default=dict)
    note = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
