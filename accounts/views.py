import logging

from django.contrib.auth import get_user_model, authenticate
from django.db import IntegrityError, DatabaseError
from django_rest.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import UserRegistrationSerializer, UserSerializer, UserLoginSerializer
from core.utils import rest_api_formatter

User = get_user_model()
logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """API view for user registration."""

    permission_classes = [AllowAny]

    def post(self, request):
        logger.info(f"Registration attempt for email: {request.data.get('email', 'N/A')}")

        try:
            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                refresh = RefreshToken.for_user(user)

                logger.info(f"User registered successfully: {user.email} (ID: {user.id})")

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

            logger.warning(f"Registration validation failed: {serializer.errors}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Validation failed',
                error_code='VALIDATION_ERROR',
                error_message='Invalid input data',
                error_fields=list(serializer.errors.keys())
            )

        except IntegrityError as e:
            logger.error(f"Registration integrity error: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_409_CONFLICT,
                success=False,
                message='User with this email already exists',
                error_code='DUPLICATE_EMAIL',
                error_message='Email address is already registered'
            )

        except DatabaseError as e:
            logger.critical(f"Database error during registration: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Unexpected error during registration: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )


class LoginView(APIView):
    """API view for user login."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', 'N/A')
        logger.info(f"Login attempt for email: {email}")

        try:
            serializer = UserLoginSerializer(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data['email']
                password = serializer.validated_data['password']

                user = authenticate(request, email=email, password=password)

                if user is not None:
                    if not user.is_active:
                        logger.warning(f"Login attempt for disabled account: {email}")
                        return rest_api_formatter(
                            data=None,
                            status_code=status.HTTP_403_FORBIDDEN,
                            success=False,
                            message='User account is disabled',
                            error_code='ACCOUNT_DISABLED',
                            error_message='User account is disabled'
                        )

                    refresh = RefreshToken.for_user(user)
                    logger.info(f"User logged in successfully: {email} (ID: {user.id})")

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

                logger.warning(f"Invalid credentials for email: {email}")
                return rest_api_formatter(
                    data=None,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    success=False,
                    message='Invalid email or password',
                    error_code='INVALID_CREDENTIALS',
                    error_message='Invalid email or password'
                )

            logger.warning(f"Login validation failed: {serializer.errors}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Validation failed',
                error_code='VALIDATION_ERROR',
                error_message='Invalid input data',
                error_fields=list(serializer.errors.keys())
            )

        except DatabaseError as e:
            logger.critical(f"Database error during login: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Unexpected error during login: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )


class LogoutView(APIView):
    """API view for user logout."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.id if request.user else 'Unknown'
        logger.info(f"Logout attempt for user ID: {user_id}")

        try:
            refresh_token = request.data.get("refresh")

            if not refresh_token:
                logger.warning(f"Logout failed - no refresh token provided for user ID: {user_id}")
                return rest_api_formatter(
                    data=None,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False,
                    message="Refresh token is required",
                    error_code='MISSING_TOKEN',
                    error_message='Refresh token must be provided'
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            logger.info(f"User logged out successfully: {user_id}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_200_OK,
                success=True,
                message="Logout successful"
            )

        except TokenError as e:
            logger.warning(f"Logout failed - invalid token for user ID: {user_id}, error: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message="Invalid or expired token",
                error_code='INVALID_TOKEN',
                error_message='The provided token is invalid or has expired'
            )

        except Exception as e:
            logger.exception(f"Unexpected error during logout for user ID: {user_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )
