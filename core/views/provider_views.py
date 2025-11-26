# core/views/provider_views.py

from rest_framework import generics, permissions

from core.models import Proveedor
from core.serializers.provider_serializers import (
    ProveedorSerializer,
    ProveedorListSerializer,
)


class ProveedorListCreateAPIView(generics.ListCreateAPIView):
    """GET: lista proveedores, POST: crea proveedor."""

    queryset = Proveedor.objects.all().order_by("nombre")
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        # Si en el futuro se quiere usar un serializer más ligero para la lista,
        # se puede cambiar aquí. Por ahora usamos el completo.
        if self.request.method == "GET":
            return ProveedorListSerializer
        return ProveedorSerializer

    ## cambiamos el metodo
    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        nombre = params.get("nombre")
        nit = params.get("nit")
        # Por defecto solo ACTIVO si no se envía parámetro
        estado = params.get("estado", "ACTIVO")

        if nombre:
            qs = qs.filter(nombre__icontains=nombre)

        if nit:
            qs = qs.filter(nit__icontains=nit)

        if estado:
            qs = qs.filter(estado__iexact=estado)

        return qs


## hasta aqui


class ProveedorDetailAPIView(generics.RetrieveUpdateAPIView):
    """GET / PUT / PATCH sobre un proveedor específico.

    Importante: NO permite DELETE porque la eliminación física de proveedores
    está deshabilitada por motivos de auditoría. Para "eliminar" se debe
    cambiar el campo `estado` a INACTIVO mediante PUT/PATCH.
    """

    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [permissions.IsAuthenticated]
