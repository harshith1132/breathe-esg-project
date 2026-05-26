import csv
import io
from datetime import datetime

SAP_UOM_MAP = {
    'L': 'liters', 'LT': 'liters',
    'GAL': 'gallons', 'GL': 'gallons',
    'KG': 'kg', 'TO': 'kg',
    'M3': 'm3',
    'ST': 'each', 'PC': 'each',
}

MATERIAL_GROUP_MAP = {
    'FUEL-STAT': ('S1_FUEL_STATIONARY', 1),
    'FUEL-MOB': ('S1_FUEL_MOBILE', 1),
    'ELEC': ('S2_ELECTRICITY', 2),
    'PROC': ('S3_PROCUREMENT', 3),
}

COLUMN_ALIASES = {
    'buchungsdatum': 'posting_date', 'postingdate': 'posting_date', 'datum': 'posting_date',
    'werk': 'plant', 'plant': 'plant',
    'kostenstelle': 'cost_center', 'costcenter': 'cost_center',
    'material': 'material_number', 'materialnumber': 'material_number', 'matnr': 'material_number',
    'materialgruppe': 'material_group', 'materialgroup': 'material_group', 'matkl': 'material_group',
    'menge': 'quantity', 'quantity': 'quantity', 'qty': 'quantity',
    'mengeneinheit': 'uom', 'meins': 'uom', 'uom': 'uom', 'unit': 'uom',
    'lieferant': 'vendor', 'vendor': 'vendor', 'lifnr': 'vendor',
    'bestellnummer': 'po_number', 'ponumber': 'po_number', 'ebeln': 'po_number',
}


def parse_sap_date(date_str):
    date_str = date_str.strip()
    for fmt in ('%d.%m.%Y', '%m/%d/%Y', '%Y%m%d', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def parse_sap_decimal(value_str):
    value_str = value_str.strip().replace(' ', '')
    if not value_str or value_str == '-':
        return None
    last_dot = value_str.rfind('.')
    last_comma = value_str.rfind(',')
    if last_comma > last_dot:
        value_str = value_str.replace('.', '').replace(',', '.')
    else:
        value_str = value_str.replace(',', '')
    try:
        return float(value_str)
    except ValueError:
        return None


def parse_sap_csv(file_content: bytes):
    text = file_content.decode('utf-8-sig')
    sample = text[:2000]
    delimiter = '\t' if sample.count('\t') > sample.count(';') else ';'
    if sample.count(',') > sample.count('\t') and sample.count(',') > sample.count(';'):
        delimiter = ','

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    results = []

    for row_num, row in enumerate(reader, start=2):
        normalized = {}
        for key, value in row.items():
            if key:
                clean_key = key.strip().lower().replace(' ', '').replace('-', '')
                mapped = COLUMN_ALIASES.get(clean_key, clean_key)
                normalized[mapped] = value.strip() if value else ''

        errors = []
        warnings = []

        posting_date = parse_sap_date(normalized.get('posting_date', ''))
        if not posting_date:
            errors.append({'field': 'posting_date', 'message': f"Cannot parse date: {normalized.get('posting_date')}"})

        qty_str = normalized.get('quantity', '')
        quantity = parse_sap_decimal(qty_str)
        if quantity is None:
            errors.append({'field': 'quantity', 'message': f"Cannot parse quantity: {qty_str}"})

        uom_raw = normalized.get('uom', '')
        uom_mapped = SAP_UOM_MAP.get(uom_raw.upper())
        if not uom_mapped:
            warnings.append({'field': 'uom', 'message': f"Unknown UoM '{uom_raw}', needs manual mapping"})

        material_group = normalized.get('material_group', '').upper()
        scope_info = MATERIAL_GROUP_MAP.get(material_group)
        if not scope_info:
            warnings.append({'field': 'material_group',
                             'message': f"Material group '{material_group}' not mapped — defaulting to S3_PROCUREMENT"})
            scope_info = ('S3_PROCUREMENT', 3)

        if quantity is not None and quantity < 0:
            warnings.append({'field': 'quantity', 'message': f"Negative quantity ({quantity}) — possible reversal/credit"})

        results.append({
            'row_number': row_num,
            'raw_data': dict(row),
            'parsed': {
                'posting_date': posting_date.isoformat() if posting_date else None,
                'plant': normalized.get('plant', ''),
                'cost_center': normalized.get('cost_center', ''),
                'material_number': normalized.get('material_number', ''),
                'material_group': material_group,
                'quantity': quantity,
                'uom': uom_mapped or uom_raw,
                'vendor': normalized.get('vendor', ''),
                'po_number': normalized.get('po_number', ''),
                'category': scope_info[0],
                'scope': scope_info[1],
            },
            'errors': errors,
            'warnings': warnings,
            'parse_status': 'ERROR' if errors else ('WARNING' if warnings else 'OK'),
        })

    return results