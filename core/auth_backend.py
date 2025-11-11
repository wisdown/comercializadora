# core/auth_backend.py
from django.contrib.auth.models import User
from django.conf import settings
from django.db import connection
import bcrypt


def _dbg(*args):
    if getattr(settings, "DEBUG", False):
        print("[AUTH]", *args)


class DBUsuarioBackend:
    """
    Autentica usando la tabla Usuario (DDL propio).
    Valida bcrypt contra Usuario.password_hash y crea/actualiza un espejo en auth_user.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            _dbg("faltan credenciales")
            return None

        uname = (username or "").strip()
        pwd = (password or "").strip()

        # 1) Buscar usuario (case-insensitive) en tu tabla
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, nombre, email, password_hash, activo
                FROM Usuario
                WHERE LOWER(username) = LOWER(%s)
                LIMIT 1
            """,
                [uname],
            )
            row = cur.fetchone()

        _dbg("row:", row)
        if not row:
            _dbg("usuario no existe en Usuario")
            return None

        uid, db_uname, nombre, email, password_hash, activo = row

        if not activo:
            _dbg("usuario inactivo")
            return None
        if not password_hash:
            _dbg("password_hash NULL/vacio")
            return None

        # 2) Verificar bcrypt (manejar espacios accidentales)
        hash_clean = password_hash.strip()
        try:
            ok = bcrypt.checkpw(pwd.encode("utf-8"), hash_clean.encode("utf-8"))
        except Exception as e:
            _dbg("bcrypt error:", repr(e))
            return None

        _dbg("bcrypt ok?", ok)
        if not ok:
            return None

        # 3) Crear/actualizar espejo en auth_user
        user, _created = User.objects.get_or_create(
            username=db_uname,
            defaults={
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
                "email": (email or ""),
                "first_name": (nombre or "")[:30],
            },
        )

        changed = False
        if user.is_active != bool(activo):
            user.is_active = bool(activo)
            changed = True
        if user.email != (email or ""):
            user.email = email or ""
            changed = True
        if user.first_name != (nombre or "")[:30]:
            user.first_name = (nombre or "")[:30]
            changed = True
        if changed:
            user.save(update_fields=["is_active", "email", "first_name"])

        _dbg("login OK como auth_user id=", user.id)
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
