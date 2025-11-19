# core/serializers/catalog_serializers.py
from rest_framework import serializers


class CatalogListFilterSerializer(serializers.Serializer):
    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=500, default=100
    )
    offset = serializers.IntegerField(required=False, min_value=0, default=0)


class ClienteCreateUpdateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    dpi = serializers.CharField(max_length=30, required=False, allow_blank=True)
    nit = serializers.CharField(max_length=30, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    estado = serializers.ChoiceField(
        choices=["ACTIVO", "INACTIVO"], required=False, default="ACTIVO"
    )


class BodegaCreateUpdateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=120)
    ubicacion = serializers.CharField(
        max_length=200, required=False, allow_null=True, allow_blank=True
    )
    activo = serializers.BooleanField(required=False, default=True)


class ProductoCreateUpdateSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=60)
    nombre = serializers.CharField(max_length=150)

    marca_id = serializers.IntegerField(required=False, allow_null=True)
    categoria_id = serializers.IntegerField(required=False, allow_null=True)
    modelo = serializers.CharField(
        max_length=100, required=False, allow_null=True, allow_blank=True
    )

    requiere_serie = serializers.BooleanField(required=False, default=False)

    atributos_json = serializers.JSONField(required=False, allow_null=True)

    costo_ref = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, default=0
    )
    precio_base = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, default=0
    )

    impuesto_id = serializers.IntegerField(required=False, allow_null=True)

    activo = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        """
        Validación de negocio adicional:
        - precio_base >= costo_ref (si ambos se envían)
        """
        costo = attrs.get("costo_ref", None)
        precio = attrs.get("precio_base", None)

        if costo is not None and precio is not None:
            if precio < costo:
                raise serializers.ValidationError(
                    "El precio_base no puede ser menor que el costo_ref."
                )
        return attrs
