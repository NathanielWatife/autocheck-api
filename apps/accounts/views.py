from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.conf import settings
from .serializers import *
from .models import *

User = get_user_model()
# Create your views here.
# Registration view
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        login(request, user)
        return Response({
            'message': 'User registered successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# login view
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    username= serializer.validated_data['username']
    password = serializer.validated_data['password']
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
    return Response({'error': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)


# logout view
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

# get user profile view
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    serializer = UserProfileSerializer(request.user.profile, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)

# update user profile view
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    # allow certain fields to be updated
    allowed_fields = ['phone_number', 'bio', 'avatar']
    data = {k: v for k, v in request.data.items() if k in allowed_fields}
    serializer = UserSerializer(user, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Profile updated successfully',
            'user': serializer.data
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# change password view
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = PasswordChangeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    user = request.user
    if not user.check_password(serializer.validated_data['old_password']):
        return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(serializer.validated_data['new_password'])
    user.save()
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, user)  # Important, to keep the user logged in
    return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)


# password reset request view
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    email = serializer.validated_data['email']
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"message": "Password reset email sent if the email exists."})
    # Generate token
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    frontend_url = settings.FRONTEND_URL
    reset_link = f"{frontend_url}/reset-password?uid={uid}&token={token}"
    subject = "Password Reset - AutoCheck Naija"
    html_message = render_to_string('registration/password_reset_email.html', {
        'reset_link': reset_link,
        'user': user,
    })
    send_mail(subject, '', settings.DEFAULT_FROM_EMAIL, [email], html_message=html_message, fail_silently=False)
    return Response({"message": "Password reset email sent if the email exists."})



# ---------- Password Reset Confirm ----------
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    uid = serializer.validated_data['uid']
    token = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']
    try:
        uid_decoded = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=uid_decoded)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        form = SetPasswordForm(user, {'new_password1': new_password, 'new_password2': new_password})
        if form.is_valid():
            form.save()
            return Response({"message": "Password has been reset successfully."})
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

# ---------- Save / Remove vehicle from garage ----------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_vehicle(request, vin):
    from apps.vehicles.models import Vehicle
    try:
        vehicle = Vehicle.objects.get(vin=vin)
    except Vehicle.DoesNotExist:
        return Response({"error": "Vehicle not found."}, status=status.HTTP_404_NOT_FOUND)
    profile = request.user.profile
    profile.saved_vehicles.add(vehicle)
    return Response({"message": f"Vehicle {vin} added to garage."})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unsave_vehicle(request, vin):
    from apps.vehicles.models import Vehicle
    try:
        vehicle = Vehicle.objects.get(vin=vin)
    except Vehicle.DoesNotExist:
        return Response({"error": "Vehicle not found."}, status=status.HTTP_404_NOT_FOUND)
    profile = request.user.profile
    profile.saved_vehicles.remove(vehicle)
    return Response({"message": f"Vehicle {vin} removed from garage."})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_garage(request):
    vehicles = request.user.profile.saved_vehicles.all()
    from apps.vehicles.serializers import VehicleSerializer
    serializer = VehicleSerializer(vehicles, many=True)
    return Response(serializer.data)
