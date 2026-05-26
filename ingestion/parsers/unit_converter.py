VOLUME_TO_LITERS = {
    'l': 1.0, 'liter': 1.0, 'liters': 1.0, 'litre': 1.0, 'litres': 1.0,
    'gal': 3.78541, 'gallon': 3.78541, 'gallons': 3.78541,
    'usg': 3.78541,
    'm3': 1000.0, 'm³': 1000.0,
    'cf': 28.3168,
}

ENERGY_TO_KWH = {
    'kwh': 1.0, 'kw-h': 1.0,
    'mwh': 1000.0,
    'gwh': 1_000_000.0,
    'mmbtu': 293.071,
    'btu': 0.000293071,
    'gj': 277.778,
    'mj': 0.277778,
    'therm': 29.3071,
}

DISTANCE_TO_KM = {
    'km': 1.0, 'kilometers': 1.0, 'kilometres': 1.0,
    'mi': 1.60934, 'mile': 1.60934, 'miles': 1.60934,
    'm': 0.001, 'meters': 0.001, 'metres': 0.001,
}


class UnitConversionError(Exception):
    pass


def normalize_volume(value: float, unit: str):
    unit_clean = unit.strip().lower()
    factor = VOLUME_TO_LITERS.get(unit_clean)
    if factor is None:
        raise UnitConversionError(f"Cannot convert unit '{unit}' to liters")
    return round(value * factor, 6), 'liters'


def normalize_energy(value: float, unit: str):
    unit_clean = unit.strip().lower()
    factor = ENERGY_TO_KWH.get(unit_clean)
    if factor is None:
        raise UnitConversionError(f"Cannot convert unit '{unit}' to kWh")
    return round(value * factor, 6), 'kWh'


def normalize_distance(value: float, unit: str):
    unit_clean = unit.strip().lower()
    factor = DISTANCE_TO_KM.get(unit_clean)
    if factor is None:
        raise UnitConversionError(f"Cannot convert unit '{unit}' to km")
    return round(value * factor, 6), 'km'