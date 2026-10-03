from uuid import uuid4

from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import UserProfile


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=8)

    def validate_email(self, value):
        email = value.strip().lower()
        if (
            UserProfile.objects.filter(email__iexact=email).exists()
            or get_user_model().objects.filter(email__iexact=email).exists()
        ):
            raise serializers.ValidationError('An account with this email already exists.')
        return email

    def validate_password(self, value):
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value

    def create(self, validated_data):
        user_model = get_user_model()
        email = validated_data['email']
        user = user_model(username=uuid4().hex, email=email)
        user.set_password(validated_data['password'])
        user.save()
        UserProfile.objects.create(
            user=user,
            email=email,
            display_name=validated_data.get('display_name', '').strip(),
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs['email'].strip().lower()
        profile = UserProfile.objects.select_related('user').filter(email__iexact=email).first()
        account = profile.user if profile else get_user_model().objects.filter(email__iexact=email).order_by('pk').first()
        user = None
        if account is not None:
            user = authenticate(
                request=self.context.get('request'),
                username=account.get_username(),
                password=attrs['password'],
            )
        if user is None or not user.is_active:
            raise serializers.ValidationError({'detail': 'Email or password is incorrect.'})
        attrs['user'] = user
        return attrs
