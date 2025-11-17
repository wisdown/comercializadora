from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import connection
import bcrypt
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken


class LoginView(APIView):
    """
    Login usando tu tabla Usuario (no auth_user).
    Devuelve JWT access + refresh.
    """

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "Usuario y password son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar usuario en tu tabla Usuario
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, nombre, email, password_hash, activo
                FROM usuario
                WHERE username=%s LIMIT 1
            """,
                [username],
            )
            row = cur.fetchone()

        if not row:
            return Response(
                {"detail": "Credenciales inválidas."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        uid, uname, nombre, email, password_hash, activo = row
        if not activo:
            return Response(
                {"detail": "Usuario inactivo."}, status=status.HTTP_403_FORBIDDEN
            )

        # Validar contraseña bcrypt
        if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
            return Response(
                {"detail": "Credenciales inválidas."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Sincronizar con auth_user (solo para emitir JWT)
        user, created = User.objects.get_or_create(
            username=uname,
            defaults={
                "is_active": True,
                "email": email or "",
                "first_name": (nombre or "")[:30],
            },
        )

        # Crear token JWT
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "usuario_id": uid,
                "username": uname,
                "nombre": nombre,
                "email": email,
            }
        )


class CambiarPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        actual = request.data.get("password_actual", "")
        nueva = request.data.get("password_nueva", "")
        if not actual or not nueva:
            return Response({"detail": "Datos incompletos."}, status=400)

        uname = request.user.username
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, password_hash FROM Usuario WHERE username=%s AND activo=1",
                [uname],
            )
            row = cur.fetchone()
            if not row:
                return Response({"detail": "Usuario no existe/activo."}, status=404)
            uid, hash_actual = row

            if not bcrypt.checkpw(actual.encode(), hash_actual.encode()):
                return Response({"detail": "Password actual incorrecto."}, status=400)

            nuevo_hash = bcrypt.hashpw(nueva.encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "UPDATE Usuario SET password_hash=%s WHERE id=%s", [nuevo_hash, uid]
            )

        return Response({"ok": True}, status=200)
