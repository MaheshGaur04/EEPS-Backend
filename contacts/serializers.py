from rest_framework import serializers

from .models import Contact


class ContactCreateSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=255)
    email = serializers.EmailField()
    phone = serializers.RegexField(
        regex=r'^\+?[0-9\s-]{10,15}$',
        error_messages={'invalid': 'Please enter a valid phone number'},
    )
    message = serializers.CharField(min_length=10)
    source = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        return Contact.objects.create(
            name=validated_data['name'].strip(),
            email=validated_data['email'].lower().strip(),
            phone=validated_data['phone'].strip(),
            message=validated_data['message'].strip(),
            source=(validated_data.get('source') or 'landing_page').strip(),
        )


class ContactSerializer(serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    id = serializers.IntegerField(read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = Contact
        fields = [
            'id', '_id', 'name', 'email', 'phone', 'message', 'source',
            'reviewed', 'replied', 'createdAt', 'updatedAt',
        ]

    def get__id(self, obj):
        return str(obj.pk)
