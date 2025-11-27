# core/serializers/inventory_serializers.py

from rest_framework import serializers

from core.models import Existencia, MovimientoInventario, Producto, Bodega


class InventarioActualSerializer(serializers.ModelSerializer):
    """Representa la existencia actual de un producto en una bodega."""

    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    producto_codigo = serializers.CharField(source="producto.codigo", read_only=True)
    bodega_nombre = serializers.CharField(source="bodega.nombre", read_only=True)

    class Meta:
        model = Existencia
        fields = [
            ##"id",
            "producto_id",
            "producto_codigo",
            "producto_nombre",
            "bodega_id",
            "bodega_nombre",
            "cantidad",
        ]


class KardexMovimientoSerializer(serializers.ModelSerializer):
    """Movimiento de inventario para el kardex."""

    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    bodega_nombre = serializers.CharField(source="bodega_origen.nombre", read_only=True)

    class Meta:
        model = MovimientoInventario
        fields = [
            "id",
            "fecha",
            "tipo",
            "producto_id",
            "producto_nombre",
            "bodega_origen_id",
            "bodega_nombre",
            "bodega_destino_id",
            "cantidad",
            "costo_unit",
            "referencia",
        ]
