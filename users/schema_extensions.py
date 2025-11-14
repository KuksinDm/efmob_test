from drf_spectacular.extensions import OpenApiAuthenticationExtension


class RequestUserAuthExt(OpenApiAuthenticationExtension):
    target_class = "users.authentication.RequestUserAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
