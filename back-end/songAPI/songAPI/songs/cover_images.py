from pathlib import PurePosixPath

from django.conf import settings
from django.templatetags.static import static


OPTIMIZED_COVER_PREFIX = 'book-covers/optimized/'


def get_book_cover_url(book):
    if not book or not book.cover_image:
        return ''

    storage_name = book.cover_image.name or ''
    if storage_name.startswith(OPTIMIZED_COVER_PREFIX):
        static_url = static(f'book-covers/{PurePosixPath(storage_name).name}')
        public_api_base_url = settings.PUBLIC_API_BASE_URL.rstrip('/')
        return f'{public_api_base_url}{static_url}' if public_api_base_url else static_url

    try:
        return book.cover_image.url
    except ValueError:
        return ''
