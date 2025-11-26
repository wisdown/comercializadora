# core/serializers/provider_serializers.py

from rest_framework import serializers

from core.models import Proveedor


class ProveedorSerializer(serializers.ModelSerializer):
    """Serializer principal para listar, crear y actualizar proveedores."""

    class Meta:
        model = Proveedor
        fields = [
            "id",
            "nombre",
            "nit",
            "cui",
            "direccion",
            "telefono",
            "email",
            "estado",
        ]
        read_only_fields = ["id"]


class ProveedorListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados, si se requiere optimizar la salida."""

    class Meta:
        model = Proveedor
        fields = [
            "id",
            "nombre",
            "nit",
            "estado",
        ]
