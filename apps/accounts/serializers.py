from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import *

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'nin', 'is_dealer', 'dealer_verified', 'credits')
        read_only_fields = ('id', 'is_dealer', 'dealer_verified', 'credits')


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = UserProfile
        fields = ('id', 'user', 'saved_vehicles', 'bio', 'avatar', 'watchlist', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at')


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    phone_number = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name', 'phone_number', 'nin')

        def validate(self, attrs):
            if attrs['password'] != attrs['password2']:
                raise serializers.ValidationError({"password": "Password fields didn't match."})
            return attrs

        def create(self, validated_data):
            validated_data.pop('password2')
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data.get('email', ''),
                password=validated_data['password'],
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                phone_number=validated_data.get('phone_number', ''),
                nin=validated_data.get('nin', '')
            )
            return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "New password fields didn't match."})
        return attrs

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])