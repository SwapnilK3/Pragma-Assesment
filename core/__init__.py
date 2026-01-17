class MediaType:
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    AUDIO = "audio"

    CHOICES = (
        (IMAGE, "Image"),
        (VIDEO, "Video"),
        (FILE, "File"),
        (AUDIO, "Audio")
    )


class MediaAccess:
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"

    CHOICES = (
        (PUBLIC, "Public"),
        (PRIVATE, "Private"),
        (PROTECTED, "Protected")
    )


class Currency:
    INR = '₹'
    USD = '$'
    EUR = '€'

    CHOICES = (
        (INR, 'INR'),
        (USD, 'USD'),
        (EUR, 'EUR')
    )
