import csv
import io
import math
from datetime import datetime

AIRPORT_COORDS = {
    'JFK': (40.6413, -73.7781), 'LAX': (33.9425, -118.4081),
    'ORD': (41.9742, -87.9073), 'LHR': (51.4775, -0.4614),
    'CDG': (49.0097, 2.5479),   'DXB': (25.2532, 55.3657),
    'SIN': (1.3644, 103.9915),  'HKG': (22.3080, 113.9185),
    'SFO': (37.6213, -122.3790),'BOS': (42.3656, -71.0096),
    'MIA': (25.7959, -80.2870), 'DEL': (28.5562, 77.1000),
    'BOM': (19.0896, 72.8656),  'HYD': (17.2403, 78.4294),
    'ATL': (33.6407, -84.4277), 'DFW': (32.8998, -97.0403),
    'SEA': (47.4502, -122.3088),'NRT': (35.7720, 140.3929),
    'ICN': (37.4602, 126.4407), 'SYD': (-33.9399, 151.1753),
}

FLIGHT_EF_SHORT = 0.255
FLIGHT_EF_LONG = 0.195
HOTEL_EF_PER_NIGHT = 21.4

SEGMENT_TYPE_MAP = {
    'air': 'S3_BUSINESS_TRAVEL_FLIGHT',
    'flight': 'S3_BUSINESS_TRAVEL_FLIGHT',
    'hotel': 'S3_BUSINESS_TRAVEL_HOTEL',
    'lodging': 'S3_BUSINESS_TRAVEL_HOTEL',
    'car': 'S3_BUSINESS_TRAVEL_GROUND',
    'car rental': 'S3_BUSINESS_TRAVEL_GROUND',
    'rental car': 'S3_BUSINESS_TRAVEL_GROUND',
    'taxi': 'S3_BUSINESS_TRAVEL_GROUND',
    'train': 'S3_BUSINESS_TRAVEL_GROUND',
    'rail': 'S3_BUSINESS_TRAVEL_GROUND',
    'bus': 'S3_BUSINESS_TRAVEL_GROUND',
}

TRAVEL_COLUMN_ALIASES = {
    'trip id': 'trip_id', 'record locator': 'trip_id', 'booking reference': 'trip_id',
    'employee id': 'employee_id',
    'traveler': 'traveler_name', 'traveler name': 'traveler_name', 'employee name': 'traveler_name',
    'cost center': 'cost_center', 'department': 'cost_center',
    'segment type': 'segment_type', 'type': 'segment_type', 'travel type': 'segment_type',
    'departure date': 'departure_date', 'check-in date': 'departure_date', 'start date': 'departure_date',
    'return date': 'return_date', 'check-out date': 'return_date', 'end date': 'return_date',
    'origin': 'origin', 'from': 'origin', 'departure': 'origin',
    'destination': 'destination', 'to': 'destination', 'arrival': 'destination',
    'vendor': 'vendor_name', 'airline': 'vendor_name', 'hotel name': 'vendor_name',
    'amount': 'amount', 'total cost': 'amount',
    'currency': 'currency',
    'nights': 'nights', 'number of nights': 'nights',
}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def estimate_flight_distance_km(origin, destination):
    warnings = []
    o_coords = AIRPORT_COORDS.get(origin.upper())
    d_coords = AIRPORT_COORDS.get(destination.upper())

    if not o_coords:
        warnings.append({'field': 'origin', 'message': f"Airport '{origin}' not in lookup — distance estimated as 0"})
        return None, warnings
    if not d_coords:
        warnings.append({'field': 'destination', 'message': f"Airport '{destination}' not in lookup — distance estimated as 0"})
        return None, warnings

    distance = haversine_km(*o_coords, *d_coords) * 1.1
    warnings.append({'field': 'distance',
                     'message': f"Distance estimated from coordinates ({distance:.0f} km, great-circle + 10% correction)"})
    return round(distance, 1), warnings


def parse_travel_date(date_str):
    date_str = date_str.strip()
    for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%m-%d-%Y', '%d %b %Y', '%b %d, %Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def parse_travel_csv(file_content: bytes):
    text = file_content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        return []

    header_map = {}
    for h in reader.fieldnames:
        h_clean = h.strip().lower()
        mapped = TRAVEL_COLUMN_ALIASES.get(h_clean, h_clean.replace(' ', '_').replace('-', '_'))
        header_map[h] = mapped

    results = []
    for row_num, row in enumerate(reader, start=2):
        normalized = {header_map[k]: v.strip() for k, v in row.items() if k}
        errors = []
        warnings = []
        is_estimated = False

        segment_type_raw = normalized.get('segment_type', '').lower()
        category = SEGMENT_TYPE_MAP.get(segment_type_raw)
        if not category:
            errors.append({'field': 'segment_type', 'message': f"Unknown segment type: '{segment_type_raw}'"})

        departure_date = parse_travel_date(normalized.get('departure_date', ''))
        if not departure_date:
            warnings.append({'field': 'departure_date',
                             'message': f"Cannot parse date: {normalized.get('departure_date')}"})

        quantity = None
        unit = None
        co2e_kg = None
        ef_used = None

        if category == 'S3_BUSINESS_TRAVEL_FLIGHT':
            origin = normalized.get('origin', '').strip().upper()
            destination = normalized.get('destination', '').strip().upper()
            distance_km, dist_warnings = estimate_flight_distance_km(origin, destination)
            warnings.extend(dist_warnings)
            is_estimated = True

            if distance_km:
                quantity = distance_km
                unit = 'km'
                ef = FLIGHT_EF_SHORT if distance_km < 1000 else FLIGHT_EF_LONG
                ef_used = ef
                co2e_kg = round(distance_km * ef, 3)
            else:
                errors.append({'field': 'distance', 'message': 'Cannot compute distance — missing airport coordinates'})

        elif category == 'S3_BUSINESS_TRAVEL_HOTEL':
            nights_str = normalized.get('nights', '1')
            try:
                nights = float(nights_str) if nights_str else 1.0
            except ValueError:
                nights = 1.0
                warnings.append({'field': 'nights', 'message': f"Cannot parse nights '{nights_str}', defaulting to 1"})
            quantity = nights
            unit = 'nights'
            ef_used = HOTEL_EF_PER_NIGHT
            co2e_kg = round(nights * HOTEL_EF_PER_NIGHT, 3)
            is_estimated = True

        elif category == 'S3_BUSINESS_TRAVEL_GROUND':
            quantity = 1
            unit = 'trip'
            warnings.append({'field': 'quantity',
                             'message': 'Ground transport distance unavailable — emissions need manual entry'})

        results.append({
            'row_number': row_num,
            'raw_data': dict(row),
            'parsed': {
                'trip_id': normalized.get('trip_id', ''),
                'employee_id': normalized.get('employee_id', ''),
                'traveler_name': normalized.get('traveler_name', ''),
                'cost_center': normalized.get('cost_center', ''),
                'segment_type': segment_type_raw,
                'category': category,
                'scope': 3,
                'departure_date': departure_date.isoformat() if departure_date else None,
                'origin': normalized.get('origin', ''),
                'destination': normalized.get('destination', ''),
                'vendor_name': normalized.get('vendor_name', ''),
                'quantity': quantity,
                'unit': unit,
                'co2e_kg': co2e_kg,
                'emission_factor': ef_used,
                'emission_factor_source': 'DEFRA 2023',
                'is_estimated': is_estimated,
            },
            'errors': errors,
            'warnings': warnings,
            'parse_status': 'ERROR' if errors else ('WARNING' if warnings else 'OK'),
        })

    return results