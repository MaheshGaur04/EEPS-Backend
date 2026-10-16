from rest_framework import serializers

from accounts.serializers import UserPublicSerializer

from .models import ServiceRequest, ServiceRequestPriority, ServiceRequestStatus


class ServiceRequestWriteSerializer(serializers.Serializer):
    subject = serializers.CharField(min_length=3, max_length=255)
    category = serializers.CharField(min_length=2, max_length=100)
    serviceType = serializers.CharField(min_length=2, max_length=100)
    systemSize = serializers.CharField(min_length=1, max_length=100)
    propertyAddress = serializers.CharField(min_length=5, max_length=500)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    preferredDate = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    priority = serializers.ChoiceField(choices=ServiceRequestPriority.choices, default=ServiceRequestPriority.MEDIUM, required=False)
    description = serializers.CharField(min_length=10)

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        for key in ('latitude', 'longitude'):
            if key in data and isinstance(data[key], str) and data[key].strip() != '':
                try:
                    data[key] = float(data[key])
                except ValueError:
                    pass
        return super().to_internal_value(data)


class ServiceRequestSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    id = serializers.IntegerField(read_only=True)
    serviceType = serializers.CharField(source='service_type')
    systemSize = serializers.CharField(source='system_size')
    propertyAddress = serializers.CharField(source='property_address')
    preferredDate = serializers.CharField(source='preferred_date', allow_null=True, required=False)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    archivedAt = serializers.DateTimeField(source='archived_at', read_only=True, allow_null=True)
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = ServiceRequest
        fields = [
            'id', '_id', 'user', 'subject', 'category', 'serviceType', 'systemSize',
            'propertyAddress', 'latitude', 'longitude', 'preferredDate', 'priority',
            'description', 'status', 'archived', 'archivedAt', 'createdAt', 'updatedAt',
        ]

    def get__id(self, obj):
        return str(obj.pk)


class ServiceRequestListSerializer(ServiceRequestSerializer):
    """Lighter list without nested user when not needed."""

    class Meta(ServiceRequestSerializer.Meta):
        fields = [
            'id', '_id', 'subject', 'category', 'serviceType', 'systemSize',
            'propertyAddress', 'latitude', 'longitude', 'preferredDate', 'priority',
            'description', 'status', 'archived', 'archivedAt', 'createdAt', 'updatedAt',
            'user',
        ]
