# erp/core/permissions.py
from django.db import connection
from rest_framework.permissions import BasePermission


def user_has_role(django_user, role_name: str) -> bool:
    """
    Verifica si el usuario (username de Django) tiene el rol en tus tablas
    Usuario / UsuarioRol / Rol.
    """
    if not django_user or not django_user.is_authenticated:
        return False
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM Usuario u
            JOIN UsuarioRol ur ON ur.usuario_id = u.id
            JOIN Rol r ON r.id = ur.rol_id
            WHERE u.username = %s AND r.nombre = %s AND u.activo = 1
            LIMIT 1
        """,
            [django_user.username, role_name],
        )
        return cur.fetchone() is not None


class HasAnyRole(BasePermission):
    """
    Permiso DRF: permite el acceso si el usuario tiene
    al menos uno de los roles indicados.
    Uso en vistas: permission_classes = [HasAnyRole(['ADMIN','VENTAS'])]
    """

    roles = []

    def __init__(self, roles=None):
        if roles is not None:
            self.roles = roles

    def has_permission(self, request, view):
        return any(user_has_role(request.user, r) for r in self.roles)
