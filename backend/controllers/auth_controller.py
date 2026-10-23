"""Existing account API, with validated inputs, closed production signup and expiry."""
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response


class LoginInput(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(max_length=254, required=False, allow_blank=True)
    password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)


class RegistrationInput(LoginInput):
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)


def _user_payload(user):
    return {'id': user.id, 'username': user.username, 'email': user.email,
            'name': user.first_name or user.username,
            'canAnalyzeDocuments': user.has_perm('models.analyze_document') if settings.DOCUMENT_REQUIRE_AUTH else True}


def _issue_token(user):
    # One token per account, as in the existing API. A new login revokes the old
    # token and resets its fixed expiry; no persistent browser credential is needed.
    with transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)
        Token.objects.filter(user=user).delete()
        return Token.objects.create(user=user)


def _auth_response(user, response_status=200):
    token = _issue_token(user)
    return Response({'token': token.key, 'expiresIn': settings.TOKEN_TTL_SECONDS,
                     'user': _user_payload(user)}, status=response_status,
                    headers={'Cache-Control': 'no-store', 'Pragma': 'no-cache'})


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def register_user(request):
    if not getattr(settings, 'ALLOW_REGISTRATION', False):
        return Response({'code': 'REGISTRATION_CLOSED', 'message': 'Account registration is closed. Contact the application administrator.'}, status=403)
    serializer = RegistrationInput(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    email = data.get('email', '').lower()
    username = data.get('username') or email
    if not username or len(username) > 150:
        return Response({'code': 'INVALID_REQUEST', 'message': 'A valid username is required.'}, status=400)
    user = User(username=username, email=email, first_name=data.get('name', ''))
    try:
        user.full_clean(exclude=['password'])
        validate_password(data['password'], user)
    except ValidationError:
        return Response({'code': 'INVALID_ACCOUNT', 'message': 'Use a valid account name and a strong, uncommon password of at least eight characters.'}, status=400)
    if email and User.objects.filter(email__iexact=email).exists():
        return Response({'code': 'INVALID_ACCOUNT', 'message': 'The account could not be created.'}, status=400)
    try:
        with transaction.atomic():
            user.set_password(data['password'])
            user.save()
            return _auth_response(user, status.HTTP_201_CREATED)
    except IntegrityError:
        return Response({'code': 'INVALID_ACCOUNT', 'message': 'The account could not be created.'}, status=400)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login_user(request):
    serializer = LoginInput(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    identifier = data.get('username') or data.get('email', '')
    username = identifier
    if '@' in identifier:
        matches = list(User.objects.filter(email__iexact=identifier).values_list('username', flat=True)[:2])
        if len(matches) == 1:
            username = matches[0]
        elif len(matches) > 1:
            # Do not pick the first account when a legacy email is nonunique.
            User().set_password(data['password'])
            return Response({'code': 'INVALID_CREDENTIALS', 'message': 'Invalid email/username or password.'}, status=401)
    user = authenticate(request=request._request, username=username, password=data['password'])
    if user is None:
        return Response({'code': 'INVALID_CREDENTIALS', 'message': 'Invalid email/username or password.'}, status=401)
    return _auth_response(user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    Token.objects.filter(user=request.user).delete()
    if hasattr(request._request, 'session'):
        from django.contrib.auth import logout
        logout(request._request)
    return Response({'message': 'Logged out successfully.'}, headers={'Cache-Control': 'no-store'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    return Response({'user': _user_payload(request.user)}, headers={'Cache-Control': 'no-store'})
