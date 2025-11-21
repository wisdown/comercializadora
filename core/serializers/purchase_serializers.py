from rest_framework import serializers
from core.models import Compra, CompraDetalle, Proveedor, Producto


class PurchaseItemInputSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=14, decimal_places=4)
    costo_unit = serializers.DecimalField(max_digits=12, decimal_places=4)


class PurchaseCreateSerializer(serializers.Serializer):
    proveedor_id = serializers.IntegerField()
    bodega_id = serializers.IntegerField()
    fecha = serializers.DateTimeField(required=False)
    no_documento = serializers.CharField(max_length=60)
    observaciones = serializers.CharField(
        max_length=255, required=False, allow_blank=True, allow_null=True
    )
    items = PurchaseItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Debe indicar al menos un producto.")
        return value


class CompraDetalleSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = CompraDetalle
        fields = [
            "id",
            "producto_id",
            "producto_nombre",
            "cantidad",
            "costo_unit",
            "subtotal",
        ]


class CompraSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)
    bodega_nombre = serializers.CharField(source="bodega.nombre", read_only=True)
    usuario_username = serializers.CharField(source="usuario.username", read_only=True)
    detalles = CompraDetalleSerializer(many=True, read_only=True)

    class Meta:
        model = Compra
        fields = [
            "id",
            "proveedor_id",
            "proveedor_nombre",
            "bodega_id",
            "bodega_nombre",
            "fecha",
            "no_documento",
            "total",
            "usuario_id",
            "usuario_username",
            "estado",
            "observaciones",
            "detalles",
        ]
