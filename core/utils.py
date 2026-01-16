from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class Pagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            'current_page': self.page.number,
            'next_page': self.page.next_page_number() if self.page.has_next() else None,
            'previous_page': self.page.previous_page_number() if self.page.has_previous() else None,
            'total_pages': self.page.paginator.num_pages,
            'total_count': self.page.paginator.count,
            'page_count': len(data),
            'page_size': self.get_page_size(self.request),
            'results': data
        })


def rest_api_formatter(
        data,
        status_code=200,
        success=True,
        message="",
        error_code=None,
        error_message=None,
        error_fields=[],
):
    return Response(
        {
            "success": success,
            "message": message,
            "errors": {
                "code": error_code,
                "message": error_message,
                "fields": error_fields,
            },
            "data": data,
        },
        status=status_code,
    )
