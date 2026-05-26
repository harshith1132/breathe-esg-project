import csv
import io
from datetime import datetime

UTILITY_COLUMN_ALIASES = {
    'account number': 'account_id', 'account_number': 'account_id', 'account id': 'account_id',
    'meter number': 'meter_id', 'meter_number': 'meter_id', 'meter id': 'meter_id',
    'service address': 'service_address', 'address': 'service_address',
    'statement start date': 'period_start', 'billing period start': 'period_start',
    'start date': 'period_start', 'from': 'period_start',
    'statement end date': 'period_end', 'billing period end': 'period_end',
    'end date': 'period_end', 'through': 'period_end', 'to': 'period_end',
    'usage': 'usage', 'energy usage': 'usage', 'electric usage': 'usage', 'consumption': 'usage',
    'tariff': 'tariff', 'rate schedule': 'tariff', 'rate code': 'tariff',
    'facility': 'facility', 'building': 'facility', 'site': 'facility',
    'unit': 'unit',
}


def parse_utility_date(date_str):
    date_str = date_str.strip()
    for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%m-%d-%Y', '%B %d, %Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def detect_energy_unit(header):
    header_lower = header.lower()
    if 'mwh' in header_lower:
        return 'MWh', 1000.0
    elif 'gwh' in header_lower:
        return 'GWh', 1_000_000.0
    return 'kWh', 1.0


def parse_utility_csv(file_content: bytes):
    text = file_content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        return []

    header_map = {}
    usage_header = None
    for h in reader.fieldnames:
        h_clean = h.strip().lower()
        if any(x in h_clean for x in ['usage', 'consumption', 'kwh', 'mwh']):
            usage_header = h
        mapped = UTILITY_COLUMN_ALIASES.get(h_clean, h_clean.replace(' ', '_'))
        header_map[h] = mapped

    results = []
    for row_num, row in enumerate(reader, start=2):
        normalized = {header_map[k]: v.strip() for k, v in row.items() if k}
        errors = []
        warnings = []

        period_start = parse_utility_date(normalized.get('period_start', ''))
        period_end = parse_utility_date(normalized.get('period_end', ''))

        if not period_start or not period_end:
            errors.append({'field': 'period',
                           'message': f"Cannot parse billing period: {normalized.get('period_start')} to {normalized.get('period_end')}"})
        elif period_start >= period_end:
            errors.append({'field': 'period', 'message': 'period_start must be before period_end'})

        usage_unit = 'kWh'
        kwh_factor = 1.0
        if usage_header:
            usage_unit, kwh_factor = detect_energy_unit(usage_header)

        # Also check the unit column if present
        unit_col = normalized.get('unit', '').strip().upper()
        if unit_col == 'MWH':
            usage_unit, kwh_factor = 'MWh', 1000.0

        usage_str = normalized.get('usage', '').replace(',', '')
        try:
            usage_raw = float(usage_str) if usage_str else None
        except ValueError:
            usage_raw = None
            errors.append({'field': 'usage', 'message': f"Cannot parse usage: {usage_str}"})

        if usage_raw is not None and usage_raw < 0:
            warnings.append({'field': 'usage', 'message': 'Negative usage — possible credit/reversal'})
        if usage_raw is not None and usage_raw > 500_000:
            warnings.append({'field': 'usage', 'message': f"Unusually high usage: {usage_raw} {usage_unit}"})

        usage_kwh = round(usage_raw * kwh_factor, 4) if usage_raw is not None else None

        results.append({
            'row_number': row_num,
            'raw_data': dict(row),
            'parsed': {
                'period_start': period_start.isoformat() if period_start else None,
                'period_end': period_end.isoformat() if period_end else None,
                'account_id': normalized.get('account_id', ''),
                'meter_id': normalized.get('meter_id', ''),
                'service_address': normalized.get('service_address', ''),
                'facility': normalized.get('facility', ''),
                'tariff': normalized.get('tariff', ''),
                'usage_raw': usage_raw,
                'usage_unit_raw': usage_unit,
                'usage_kwh': usage_kwh,
                'category': 'S2_ELECTRICITY',
                'scope': 2,
            },
            'errors': errors,
            'warnings': warnings,
            'parse_status': 'ERROR' if errors else ('WARNING' if warnings else 'OK'),
        })

    return results