import re


def normalize_phone(raw):
    """Normalize an Iranian mobile number to 09XXXXXXXXX when possible."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if digits.startswith("0098"):
        digits = digits[4:]
    elif digits.startswith("98") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    return digits


def is_valid_mobile(raw):
    return bool(re.fullmatch(r"09\d{9}", normalize_phone(raw)))
