from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if (
        isinstance(exc, (NotAuthenticated, AuthenticationFailed))
        and response is not None
    ):
        response.status_code = 401

    return response
