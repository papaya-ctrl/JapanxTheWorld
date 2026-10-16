from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "name": user.first_name or user.username,
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    """
    POST /api/auth/register
    Body: { "username" or "email", "password", "name" (optional) }
    """
    email = (request.data.get("email") or "").strip().lower()
    username = (request.data.get("username") or email).strip()
    password = request.data.get("password") or ""
    name = (request.data.get("name") or "").strip()

    if not username or not password:
        return Response(
            {
                "code": "INVALID_REQUEST",
                "message": "Username/email and password are required.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 6:
        return Response(
            {
                "code": "WEAK_PASSWORD",
                "message": "Password must be at least 6 characters long.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists() or (email and User.objects.filter(email=email).exists()):
        return Response(
            {
                "code": "USER_ALREADY_EXISTS",
                "message": "An account with this username or email already exists.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=name,
    )
    token, _ = Token.objects.get_or_create(user=user)

    return Response(
        {
            "token": token.key,
            "user": _user_payload(user),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    """
    POST /api/auth/login
    Body: { "username" or "email", "password" }
    """
    identifier = (request.data.get("username") or request.data.get("email") or "").strip()
    password = request.data.get("password") or ""

    if not identifier or not password:
        return Response(
            {
                "code": "INVALID_REQUEST",
                "message": "Email/username and password are required.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Email ဖြင့် login ဝင်လာပါက သက်ဆိုင်ရာ username ကို ရှာပေးသည်
    username = identifier
    if "@" in identifier:
        matched_user = User.objects.filter(email=identifier.lower()).first()
        if matched_user:
            username = matched_user.username

    user = authenticate(username=username, password=password)
    if not user:
        return Response(
            {
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email/username or password.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {
            "token": token.key,
            "user": _user_payload(user),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """
    POST /api/auth/logout
    Requires Header: Authorization: Token <key>
    """
    Token.objects.filter(user=request.user).delete()
    return Response(
        {"message": "Logged out successfully."},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    GET /api/auth/me
    Requires Header: Authorization: Token <key>
    """
    return Response(
        {"user": _user_payload(request.user)},
        status=status.HTTP_200_OK,
    )
