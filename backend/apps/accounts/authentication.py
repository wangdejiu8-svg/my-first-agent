from django.conf import settings
from django.middleware import csrf
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck, TokenAuthentication, get_authorization_header


class CookieTokenAuthentication(TokenAuthentication):
    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if auth:
            return super().authenticate(request)

        token = request.COOKIES.get(settings.AUTH_TOKEN_COOKIE_NAME)
        if not token:
            return None
        user_auth_tuple = self.authenticate_credentials(token)
        self.enforce_csrf(request)
        csrf.get_token(request)
        return user_auth_tuple

    def enforce_csrf(self, request):
        check = CSRFCheck(lambda request: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")
