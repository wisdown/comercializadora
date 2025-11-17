# core/serializers/order_serializers.py
from rest_framework import serializers


class PedidoItemSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)


class PedidoCreateSerializer(serializers.Serializer):
    cliente_id = serializers.IntegerField()
    bodega_id = serializers.IntegerField()
    items = PedidoItemSerializer(many=True)


class PedidoItemsReplaceSerializer(serializers.Serializer):
    items = PedidoItemSerializer(many=True)


class PedidoListFilterSerializer(serializers.Serializer):
    cliente_id = serializers.IntegerField(required=False)
    estado = serializers.ChoiceField(
        required=False,
        choices=["ABIERTO", "RESERVADO", "FACTURADO", "CANCELADO"],
    )
    fecha_desde = serializers.DateField(required=False)
    fecha_hasta = serializers.DateField(required=False)
