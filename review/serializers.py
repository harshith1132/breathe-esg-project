from rest_framework import serializers
from core.models import EmissionRecord, AuditLog, IngestionBatch


class EmissionRecordSerializer(serializers.ModelSerializer):
    reviewed_by_email = serializers.SerializerMethodField()
    data_source_name = serializers.SerializerMethodField()
    batch_filename = serializers.SerializerMethodField()

    class Meta:
        model = EmissionRecord
        fields = '__all__'

    def get_reviewed_by_email(self, obj):
        return obj.reviewed_by.email if obj.reviewed_by else None

    def get_data_source_name(self, obj):
        return obj.data_source.name if obj.data_source else None

    def get_batch_filename(self, obj):
        return obj.batch.original_filename if obj.batch else None


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = '__all__'

    def get_actor_email(self, obj):
        return obj.actor.email if obj.actor else None


class BatchSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.SerializerMethodField()
    data_source_name = serializers.SerializerMethodField()

    class Meta:
        model = IngestionBatch
        fields = '__all__'

    def get_uploaded_by_email(self, obj):
        return obj.uploaded_by.email if obj.uploaded_by else None

    def get_data_source_name(self, obj):
        return obj.data_source.name if obj.data_source else None