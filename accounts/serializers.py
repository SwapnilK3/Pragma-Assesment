from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from accounts import USER_ROLES

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details (used in responses)."""

    id = serializers.UUIDField(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'date_of_birth', 'gender', 'is_active',
            'created_at', 'updated_at', 'is_staff', "is_authenticated", 'is_superuser'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

#
# class UserListSerializer(serializers.ModelSerializer):
#     """Lightweight serializer for listing users."""
#
#     id = serializers.UUIDField(read_only=True)
#     full_name = serializers.CharField(source='name', read_only=True)
#
#     class Meta:
#         model = User
#         fields = ('id', 'email', 'full_name')
#

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    role = serializers.CharField(
        write_only=True,
        default=USER_ROLES.CUSTOMER,
    )

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'date_of_birth',
            'gender', 'role', 'password', 'password_confirm'
        )
        read_only_fields = ('id',)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower().strip()

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                "password_confirm": "Password fields didn't match."
            })
        if data['role'] not in USER_ROLES.CHOICES:
            raise serializers.ValidationError({
                "role": "not a valid role."
            })
        return data

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        role = validated_data.pop('role')
        if role == USER_ROLES.ADMIN:
            is_staff = True
            is_superuser = True
        else :
            is_staff = True if role == USER_ROLES.STAFF else False
            is_superuser = False


        user = User.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            is_staff=is_staff,
            is_superuser=is_superuser,
            password=validated_data['password'],
            date_of_birth=validated_data.get('date_of_birth', None),
            gender=validated_data.get('gender', None),
        )

        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )