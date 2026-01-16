from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    """Custom authentication backend using email instead of username."""

    def authenticate(
            self, request,
            username=None,
            email=None,
            password=None,
            **kwargs
    ):

        # Django admin sends 'username', so we need to handle both
        email = email or username

        if not email or not password:
            return None

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
