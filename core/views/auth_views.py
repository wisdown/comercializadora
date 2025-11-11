from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import connection
import bcrypt


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
