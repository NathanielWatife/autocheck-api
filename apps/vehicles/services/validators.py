import re

def is_valid_vin(vin: str) -> bool:
    """Basic VIN validation: 17 chars, no I/O/Q, valid checksum (simplified)."""
    if not vin or len(vin) != 17:
        return False
    # Exclude I, O, Q
    if re.search(r'[IOQ]', vin):
        return False
    # All alphanumeric
    if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
        return False
    return True