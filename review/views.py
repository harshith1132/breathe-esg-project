from django.utils import timezone
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend

from core.models import EmissionRecord, AuditLog, IngestionBatch
from .serializers import EmissionRecordSerializer, AuditLogSerializer, BatchSerializer


class EmissionRecordViewSet(viewsets.ModelViewSet):
    serializer_class = EmissionRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['scope', 'category', 'review_status', 'batch', 'is_estimated']
    ordering_fields = ['activity_date', 'period_start', 'co2e_kg', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return EmissionRecord.objects.filter(
            organization=self.request.user.profile.organization
        ).select_related('batch', 'data_source', 'reviewed_by')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        record = self.get_object()
        if record.is_locked:
            return Response({'error': 'Record is locked for audit'}, status=400)
        old_status = record.review_status
        record.review_status = 'APPROVED'
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.review_notes = request.data.get('notes', '')
        record.save()
        AuditLog.objects.create(
            emission_record=record, actor=request.user, action='APPROVED',
            old_values={'review_status': old_status},
            new_values={'review_status': 'APPROVED'},
            note=record.review_notes,
        )
        return Response(EmissionRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        record = self.get_object()
        if record.is_locked:
            return Response({'error': 'Record is locked for audit'}, status=400)
        old_status = record.review_status
        record.review_status = 'REJECTED'
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.review_notes = request.data.get('notes', '')
        record.save()
        AuditLog.objects.create(
            emission_record=record, actor=request.user, action='REJECTED',
            old_values={'review_status': old_status},
            new_values={'review_status': 'REJECTED'},
        )
        return Response(EmissionRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        record = self.get_object()
        reason = request.data.get('reason', '')
        old_status = record.review_status
        record.review_status = 'FLAGGED'
        reasons = record.flagged_reasons or []
        if reason and reason not in reasons:
            reasons.append(reason)
        record.flagged_reasons = reasons
        record.save()
        AuditLog.objects.create(
            emission_record=record, actor=request.user, action='FLAGGED',
            old_values={'review_status': old_status},
            new_values={'review_status': 'FLAGGED', 'reason': reason},
        )
        return Response(EmissionRecordSerializer(record).data)

    @action(detail=True, methods=['patch'])
    def edit(self, request, pk=None):
        EDITABLE_FIELDS = [
            'quantity_raw', 'unit_raw', 'quantity_normalized', 'unit_normalized',
            'emission_factor', 'co2e_kg', 'facility_code', 'cost_center',
            'activity_date', 'period_start', 'period_end', 'description', 'review_notes'
        ]
        record = self.get_object()
        if record.is_locked:
            return Response({'error': 'Record is locked for audit'}, status=400)
        old_values = {}
        new_values = {}
        for field in EDITABLE_FIELDS:
            if field in request.data:
                old_values[field] = str(getattr(record, field, None))
                setattr(record, field, request.data[field])
                new_values[field] = request.data[field]
        if new_values:
            if not record.is_edited:
                record.original_values = old_values
            record.is_edited = True
            record.save()
            AuditLog.objects.create(
                emission_record=record, actor=request.user, action='EDITED',
                old_values=old_values, new_values=new_values,
            )
        return Response(EmissionRecordSerializer(record).data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        record = self.get_object()
        logs = record.audit_log.all()
        return Response(AuditLogSerializer(logs, many=True).data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        from django.db.models import Sum, Count
        qs = self.get_queryset()
        approved_qs = qs.filter(review_status='APPROVED')
        by_scope = approved_qs.values('scope').annotate(
            total_co2e=Sum('co2e_kg'),
            record_count=Count('id'),
        )
        return Response({
            'approved_by_scope': list(by_scope),
            'pending_count': qs.filter(review_status='PENDING').count(),
            'flagged_count': qs.filter(review_status='FLAGGED').count(),
            'approved_count': approved_qs.count(),
            'rejected_count': qs.filter(review_status='REJECTED').count(),
            'total_co2e_approved': approved_qs.aggregate(t=Sum('co2e_kg'))['t'] or 0,
        })


class BatchListView(ListAPIView):
    serializer_class = BatchSerializer

    def get_queryset(self):
        return IngestionBatch.objects.filter(
            organization=self.request.user.profile.organization
        ).order_by('-uploaded_at')