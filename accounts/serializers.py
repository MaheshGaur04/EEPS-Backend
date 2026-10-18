from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import serializers

from .models import AdminMessage, User, UserRole

_DUMMY_PASSWORD_HASH = make_password('dummy-password-for-login-timing')


class AdminMessageSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    isRead = serializers.BooleanField(source='is_read', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    senderName = serializers.SerializerMethodField()

    class Meta:
        model = AdminMessage
        fields = ['_id', 'body', 'isRead', 'createdAt', 'senderName']

    def get__id(self, obj):
        return str(obj.pk)

    def get_senderName(self, obj):
        if obj.sender_id and obj.sender:
            return obj.sender.full_name
        return 'Earth Energy Admin'


class UserPublicSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    _id = serializers.SerializerMethodField()
    fullName = serializers.CharField(source='full_name')
    companyName = serializers.CharField(source='company_name', required=False, allow_null=True, allow_blank=True)
    consultantType = serializers.CharField(source='consultant_type', required=False, allow_null=True, allow_blank=True)
    technicalSpecialization = serializers.CharField(
        source='technical_specialization', required=False, allow_null=True, allow_blank=True
    )
    systemType = serializers.CharField(source='system_type', required=False, allow_null=True, allow_blank=True)
    isActive = serializers.BooleanField(source='is_active')
    isVerified = serializers.BooleanField(source='is_verified')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', '_id', 'fullName', 'email', 'mobile', 'role', 'location',
            'companyName', 'consultantType', 'technicalSpecialization', 'systemType',
            'isActive', 'isVerified', 'createdAt', 'updatedAt',
        ]

    def get__id(self, obj):
        return str(obj.pk)


class RegisterSerializer(serializers.Serializer):
    fullName = serializers.CharField(min_length=2, max_length=255)
    email = serializers.EmailField()
    mobile = serializers.RegexField(
        regex=r'^\d{10}$',
        error_messages={'invalid': 'Mobile number must be exactly 10 digits'},
    )
    password = serializers.CharField(min_length=12, write_only=True)
    location = serializers.CharField(min_length=2, max_length=255)

    def validate(self, attrs):
        email = attrs['email'].lower().strip()
        mobile = attrs['mobile'].strip()
        if User.objects.filter(Q(email__iexact=email) | Q(mobile=mobile)).exists():
            raise serializers.ValidationError('User with this email or mobile already exists')
        attrs['email'] = email
        password_user = User(
            full_name=attrs['fullName'],
            email=email,
            mobile=mobile,
            location=attrs['location'],
        )
        try:
            validate_password(attrs['password'], user=password_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            mobile=validated_data['mobile'],
            password=validated_data['password'],
            full_name=validated_data['fullName'],
            location=validated_data['location'],
            role=UserRole.CUSTOMER,
            is_verified=True,
        )


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs['identifier'].strip()
        password = attrs['password']

        user = User.objects.filter(
            Q(email__iexact=identifier.lower()) | Q(mobile=identifier)
        ).first()

        if not user:
            check_password(password, _DUMMY_PASSWORD_HASH)
            raise serializers.ValidationError('Invalid email/mobile or password')

        if not user.check_password(password) or not user.is_active:
            raise serializers.ValidationError('Invalid email/mobile or password')

        attrs['user'] = user
        return attrs
