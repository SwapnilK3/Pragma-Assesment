from django.core.exceptions import ValidationError
from phonenumber_field.phonenumber import to_python
from phonenumbers.phonenumberutil import is_possible_number


def validate_possible_number(phone, country=None):
    """
    Validate phone number using phonenumbers library.
    Provides detailed error messages for different validation failures.
    """
    if not phone:
        raise ValidationError(
            "Phone number is required.",
            code="required",
        )
    
    try:
        phone_number = to_python(phone, country)
    except Exception:
        raise ValidationError(
            "Invalid phone number format. Please use international format with country code (e.g., +91 9876543210).",
            code="invalid_format",
        )
    
    if not phone_number:
        raise ValidationError(
            "Could not parse phone number. Please ensure you've included the country code (e.g., +91 for India, +1 for US).",
            code="parse_error",
        )
    
    if not is_possible_number(phone_number):
        raise ValidationError(
            f"Phone number {phone} has incorrect length for the country code provided. Please check the number of digits.",
            code="invalid_length",
        )
    
    if not phone_number.is_valid():
        raise ValidationError(
            f"Phone number {phone} is not valid. Please verify the number is correct for your region.",
            code="invalid",
        )
    
    return phone_number