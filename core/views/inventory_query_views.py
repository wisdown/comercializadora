# core/views/inventory_query_views.py

from django.db.models import Q
from rest_framework import generics, permissions

from core.models import Existencia, MovimientoInventario
from core.serializers.inventory_serializers import (
    InventarioActualSerializer,
    KardexMovimientoSerializer,
)


class InventarioActualListAPIView(generics.ListAPIView):
    """Lista de existencias actuales por producto y bodega.

    Filtros (query params):
    - producto_id
    - bodega_id
    - search: texto para buscar por nombre o código de producto (opcional)
    """

    serializer_class = InventarioActualSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Existencia.objects.select_related("producto", "bodega").all()

        params = self.request.query_params

        producto_id = params.get("producto_id")
        bodega_id = params.get("bodega_id")
        search = params.get("search")

        if producto_id:
            qs = qs.filter(producto_id=producto_id)

        if bodega_id:
            qs = qs.filter(bodega_id=bodega_id)

        if search:
            # Siempre buscar por nombre
            q = Q(producto__nombre__icontains=search)
            # Si el texto es numérico, también buscar por código/id numérico
            if search.isdigit():
                # ajusta según tu modelo: producto__codigo o producto_id
                q |= Q(producto__codigo=int(search))
                # o si no tienes campo codigo y usas el id:
                # q |= Q(producto_id=int(search))
            qs = qs.filter(q)

        # Opcional: excluir registros con cantidad = 0
        qs = qs.exclude(cantidad=0)

        return qs.order_by("producto__nombre", "bodega__nombre")


class KardexProductoListAPIView(generics.ListAPIView):
    """Lista de movimientos de inventario (kardex) para un producto.

    URL: /api/v1/inventario/<producto_id>/kardex/

    Filtros (query params):
    - bodega_id (opcional)
    - fecha_desde (YYYY-MM-DD, opcional)
    - fecha_hasta (YYYY-MM-DD, opcional)
    """

    serializer_class = KardexMovimientoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        producto_id = self.kwargs["producto_id"]
        params = self.request.query_params

        bodega_id = params.get("bodega_id")
        fecha_desde = params.get("fecha_desde")
        fecha_hasta = params.get("fecha_hasta")

        qs = MovimientoInventario.objects.select_related("producto", "bodega_origen")
        qs = qs.filter(producto_id=producto_id)

        if bodega_id:
            # El kardex suele asociarse a la bodega de origen (para salidas)
            qs = qs.filter(bodega_origen_id=bodega_id)

        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)

        if fecha_hasta:
            qs = qs.filter(fecha__date__lte=fecha_hasta)

        return qs.order_by("fecha", "id")
