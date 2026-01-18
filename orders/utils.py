from core.models import Address


def create_shipping_address(shipping_address_details):
    country_code = shipping_address_details.get('country_code')

    address_data = dict(
        address_line_1 = shipping_address_details['address_line_1'],
        address_line_2 = shipping_address_details.get('address_line_2', None),
        city = shipping_address_details['city'],
        city_area = shipping_address_details.get('city_area', None),
        country = country_code.upper(),
        country_area = shipping_address_details['country_area'],
        postal_code = shipping_address_details['postal_code'],
        phone = shipping_address_details['phone'],
    )
    address_obj = Address.objects.create(**address_data)
    return address_obj

#TODO Shift this to a model for category wise tax
def get_tax_rate():
    return 0

