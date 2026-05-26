from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser

from core.models import IngestionBatch, RawRecord, EmissionRecord, DataSource, AuditLog
from .parsers.sap_parser import parse_sap_csv
from .parsers.utility_parser import parse_utility_csv
from .parsers.travel_parser import parse_travel_csv

PARSER_MAP = {
    'SAP': parse_sap_csv,
    'UTILITY': parse_utility_csv,
    'TRAVEL': parse_travel_csv,
}

ELECTRICITY_EF = 0.20493   # kgCO2e/kWh, DEFRA 2023 UK grid average
DIESEL_EF = 2.68801        # kgCO2e/liter, DEFRA 2023


class UploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get('file')
        source_id = request.data.get('data_source_id')

        if not file:
            return Response({'error': 'No file provided'}, status=400)
        if not source_id:
            return Response({'error': 'data_source_id required'}, status=400)

        try:
            data_source = DataSource.objects.get(
                id=source_id,
                organization=request.user.profile.organization
            )
        except DataSource.DoesNotExist:
            return Response({'error': 'Data source not found'}, status=404)

        org = request.user.profile.organization

        try:
            file_content = file.read()
            file.seek(0)

            batch = IngestionBatch.objects.create(
                organization=org,
                data_source=data_source,
                uploaded_by=request.user,
                original_filename=file.name,
                file=file,
                status='PROCESSING',
            )
            parser = PARSER_MAP[data_source.source_type]
            parsed_rows = parser(file_content)

            errors = 0
            warnings = 0
            created_records = []

            for row_data in parsed_rows:
                raw = RawRecord.objects.create(
                    batch=batch,
                    row_number=row_data['row_number'],
                    raw_data=row_data['raw_data'],
                    parse_status=row_data['parse_status'],
                    parse_errors=row_data['errors'] + row_data['warnings'],
                )

                if row_data['parse_status'] == 'ERROR':
                    errors += 1
                    continue

                if row_data['parse_status'] == 'WARNING':
                    warnings += 1

                p = row_data['parsed']

                er_kwargs = dict(
                    organization=org,
                    batch=batch,
                    raw_record=raw,
                    data_source=data_source,
                    scope=p.get('scope', 3),
                    category=p.get('category', 'S3_PROCUREMENT'),
                    facility_code=p.get('plant', '') or p.get('account_id', '') or p.get('meter_id', ''),
                    cost_center=p.get('cost_center', ''),
                    vendor_name=p.get('vendor', '') or p.get('vendor_name', ''),
                    description=p.get('description', ''),
                    quantity_raw=p.get('quantity') or p.get('usage_raw') or 0,
                    unit_raw=p.get('uom', '') or p.get('usage_unit_raw', '') or p.get('unit', ''),
                    quantity_normalized=0,
                    unit_normalized='',
                    flagged_reasons=[w['message'] for w in row_data['warnings']],
                    is_estimated=p.get('is_estimated', False),
                    review_status='FLAGGED' if row_data['warnings'] else 'PENDING',
                )

                if p.get('activity_date') or p.get('posting_date') or p.get('departure_date'):
                    date_val = p.get('activity_date') or p.get('posting_date') or p.get('departure_date')
                    er_kwargs['activity_date'] = date_val
                if p.get('period_start'):
                    er_kwargs['period_start'] = p['period_start']
                if p.get('period_end'):
                    er_kwargs['period_end'] = p['period_end']

                qty_raw = float(er_kwargs['quantity_raw'])
                unit = er_kwargs['unit_raw'].lower()

                if data_source.source_type == 'UTILITY':
                    kwh = p.get('usage_kwh') or qty_raw
                    er_kwargs['quantity_normalized'] = kwh
                    er_kwargs['unit_normalized'] = 'kWh'
                    er_kwargs['emission_factor'] = ELECTRICITY_EF
                    er_kwargs['emission_factor_unit'] = 'kgCO2e/kWh'
                    er_kwargs['emission_factor_source'] = 'DEFRA 2023'
                    er_kwargs['co2e_kg'] = round(kwh * ELECTRICITY_EF, 4) if kwh else None

                elif data_source.source_type == 'SAP':
                    try:
                        from .parsers.unit_converter import normalize_volume
                        liters, _ = normalize_volume(qty_raw, unit)
                        er_kwargs['quantity_normalized'] = liters
                        er_kwargs['unit_normalized'] = 'liters'
                        er_kwargs['emission_factor'] = DIESEL_EF
                        er_kwargs['emission_factor_unit'] = 'kgCO2e/liter'
                        er_kwargs['emission_factor_source'] = 'DEFRA 2023'
                        er_kwargs['co2e_kg'] = round(liters * DIESEL_EF, 4)
                    except Exception:
                        er_kwargs['quantity_normalized'] = qty_raw
                        er_kwargs['unit_normalized'] = unit
                        er_kwargs['flagged_reasons'].append('Unit conversion failed — CO2e not calculated')
                        er_kwargs['review_status'] = 'FLAGGED'

                elif data_source.source_type == 'TRAVEL':
                    er_kwargs['quantity_normalized'] = p.get('quantity') or 0
                    er_kwargs['unit_normalized'] = p.get('unit', 'units')
                    er_kwargs['emission_factor'] = p.get('emission_factor')
                    er_kwargs['emission_factor_unit'] = 'kgCO2e/km' if p.get('unit') == 'km' else 'kgCO2e/night'
                    er_kwargs['emission_factor_source'] = p.get('emission_factor_source', 'DEFRA 2023')
                    er_kwargs['co2e_kg'] = p.get('co2e_kg')

                er = EmissionRecord.objects.create(**er_kwargs)

                AuditLog.objects.create(
                    emission_record=er,
                    actor=request.user,
                    action='CREATED',
                    new_values={'source': data_source.source_type, 'batch': str(batch.id)},
                )

                created_records.append(str(er.id))

            batch.row_count = len(parsed_rows)
            batch.error_count = errors
            batch.warning_count = warnings
            batch.status = 'DONE'
            batch.save()

            return Response({
                'batch_id': str(batch.id),
                'status': 'DONE',
                'row_count': len(parsed_rows),
                'errors': errors,
                'warnings': warnings,
                'records_created': len(created_records),
            }, status=201)

        except Exception as e:
            batch.status = 'FAILED'
            batch.notes = str(e)
            batch.save()
            return Response({'error': str(e), 'batch_id': str(batch.id)}, status=500)