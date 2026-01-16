from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.decorators import login_required
from django_rest.permissions import AllowAny
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import UserRegistrationSerializer, UserSerializer, UserLoginSerializer
from core.utils import rest_api_formatter

User = get_user_model()


class RegisterView(APIView):
    """API view for user registration."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return rest_api_formatter(
                status_code=status.HTTP_201_CREATED,
                success=True,
                message='User registered successfully',
                data={
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                },
            )
        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST,
            success=False,
            message='Validation failed',
            error_code='VALIDATION_ERROR',
            error_message='Invalid input data',
            error_fields=list(serializer.errors.keys())
        )


class LoginView(APIView):
    """API view for user login."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(request, email=email, password=password)

            if user is not None:
                if not user.is_active:
                    return rest_api_formatter(
                        data=None,
                        status_code=status.HTTP_403_FORBIDDEN,
                        success=False,
                        message='User account is disabled',
                        error_code='ACCOUNT_DISABLED',
                        error_message='User account is disabled'
                    )

                refresh = RefreshToken.for_user(user)
                return rest_api_formatter(
                    data={
                        'user': UserSerializer(user).data,
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        }
                    },
                    status_code=status.HTTP_200_OK,
                    success=True,
                    message='Login successful'
                )

            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_401_UNAUTHORIZED,
                success=False,
                message='Invalid email or password',
                error_code='INVALID_CREDENTIALS',
                error_message='Invalid email or password'
            )

        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST,
            success=False,
            message='Validation failed',
            error_code='VALIDATION_ERROR',
            error_message='Invalid input data',
            error_fields=list(serializer.errors.keys())
        )



#
# class LogoutView(APIView):
#     permission_classes = [AllowAny]
#     def post(self, request):
#         return rest_api_formatter(
#             data=None,
#             status_code=status.HTTP_200_OK,
#             success=True,
#             message='Logout successful'
#         )

