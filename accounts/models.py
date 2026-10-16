from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
    CONSULTANT = 'CONSULTANT', 'Consultant'
    TECHNICIAN = 'TECHNICIAN', 'Technician'
    CUSTOMER = 'CUSTOMER', 'Customer'


class UserManager(BaseUserManager):
    def create_user(self, email, mobile, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        if not mobile:
            raise ValueError('Mobile is required')
        email = self.normalize_email(email)
        user = self.model(email=email, mobile=mobile, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, mobile, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.SUPER_ADMIN)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('full_name', extra_fields.get('full_name', 'Super Admin'))
        extra_fields.setdefault('location', extra_fields.get('location', 'HQ'))
        return self.create_user(email, mobile, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    mobile = models.CharField(max_length=15, unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CUSTOMER)
    location = models.CharField(max_length=255)

    company_name = models.CharField(max_length=255, blank=True, null=True)
    consultant_type = models.CharField(max_length=255, blank=True, null=True)
    technical_specialization = models.CharField(max_length=255, blank=True, null=True)
    system_type = models.CharField(max_length=255, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    otp = models.CharField(max_length=10, blank=True, null=True)
    otp_expires = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['mobile', 'full_name', 'location']

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} <{self.email}>'


class AdminMessage(models.Model):
    """Message from a super admin to a customer (shown as notifications)."""

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='admin_messages',
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_admin_messages',
    )
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Message to {self.recipient_id} @ {self.created_at}'
