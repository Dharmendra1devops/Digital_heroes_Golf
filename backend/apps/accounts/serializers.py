from uuid import uuid4

from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import UserProfile
from apps.charities.models import Charity
from apps.charities.services import select_charity
from apps.scores.models import GolfScore
from apps.subscriptions.models import Subscription


class AdminUserScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfScore
        fields = ('id', 'score_date', 'score')

    def validate_score(self, value):
        if not 1 <= value <= 45:
            raise serializers.ValidationError('Stableford scores must be between 1 and 45.')
        return value


class AdminUserSubscriptionSerializer(serializers.ModelSerializer):
    plan_interval = serializers.CharField(source='plan.interval', read_only=True)

    class Meta:
        model = Subscription
        fields = (
            'id', 'plan_interval', 'status', 'current_period_start',
            'current_period_end', 'cancel_at_period_end',
        )


class AdminUserSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    is_admin = serializers.BooleanField(read_only=True)
    subscriptions = AdminUserSubscriptionSerializer(many=True, read_only=True)
    scores = AdminUserScoreSerializer(many=True, read_only=True)

    @staticmethod
    def serialize_user(user):
        profile = getattr(user, 'profile', None)
        return {
            'id': user.pk,
            'email': profile.email if profile else user.email,
            'display_name': profile.display_name if profile else user.get_full_name(),
            'is_active': user.is_active,
            'date_joined': user.date_joined,
            'is_admin': user.is_staff or user.is_superuser,
            'subscriptions': list(user.subscriptions.all()),
            'scores': list(user.golf_scores.all()),
        }

    def to_representation(self, instance):
        return super().to_representation(self.serialize_user(instance))


class AdminUserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254, required=False)
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        user = self.instance
        if user is None:
            raise serializers.ValidationError('A member account is required.')
        if user.is_staff or user.is_superuser:
            raise serializers.ValidationError('Staff accounts cannot be edited in member management.')
        email = attrs.get('email')
        if email:
            email = email.strip().lower()
            user_model = get_user_model()
            if (
                UserProfile.objects.filter(email__iexact=email).exclude(user=user).exists()
                or user_model.objects.filter(email__iexact=email).exclude(pk=user.pk).exists()
            ):
                raise serializers.ValidationError({'email': 'An account with this email already exists.'})
            attrs['email'] = email
        return attrs

    def update(self, instance, validated_data):
        profile = getattr(instance, 'profile', None)
        if profile is None:
            profile = UserProfile.objects.create(
                user=instance,
                email=validated_data.get('email', instance.email).strip().lower(),
            )
        if 'email' in validated_data:
            profile.email = validated_data['email']
            instance.email = validated_data['email']
            instance.save(update_fields=('email',))
        if 'display_name' in validated_data:
            profile.display_name = validated_data['display_name'].strip()
        profile.save()
        if 'is_active' in validated_data:
            instance.is_active = validated_data['is_active']
            instance.save(update_fields=('is_active',))
        return instance


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=8)
    charity_id = serializers.UUIDField(required=False)
    contribution_bps = serializers.IntegerField(required=False, default=1000)

    def validate(self, attrs):
        if Charity.objects.filter(is_active=True).exists() and 'charity_id' not in attrs:
            raise serializers.ValidationError({
                'charity_id': 'Choose a charity to support when creating your account.',
            })
        if not 1000 <= attrs['contribution_bps'] <= 10000:
            raise serializers.ValidationError({
                'contribution_bps': 'Contribution must be between 10% and 100%.',
            })
        if 'charity_id' in attrs and not Charity.objects.filter(
            pk=attrs['charity_id'],
            is_active=True,
        ).exists():
            raise serializers.ValidationError({
                'charity_id': 'Choose an active charity.',
            })
        return attrs

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
        if 'charity_id' in validated_data:
            select_charity(
                user,
                validated_data['charity_id'],
                validated_data['contribution_bps'],
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


class MemberProfileUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=120, required=True, allow_blank=True)

    def update(self, instance, validated_data):
        profile, _created = UserProfile.objects.get_or_create(
            user=instance,
            defaults={'email': instance.email.strip().lower()},
        )
        profile.display_name = validated_data['display_name'].strip()
        profile.save(update_fields=('display_name', 'updated_at'))
        return instance


class MemberPasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Your current password is incorrect.')
        return value

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(value, user=self.context['request'].user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value
