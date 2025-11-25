# core/views/purchase_dashboard_views.py

from django.db.models import Sum, Value, DecimalField

from django.utils.dateparse import parse_date
from django.db.models import Sum, F
from django.db.models.functions import Coalesce

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.models import Compra, CompraDetalle


class PurchaseDashboardAPIView(APIView):
    """
    GET /api/v1/compras/dashboard/

    Filtros opcionales por query params:
    - fecha_desde: YYYY-MM-DD
    - fecha_hasta: YYYY-MM-DD
    - proveedor_id: int
    - bodega_id: int
    - estado: str
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        params = request.query_params

        fecha_desde = params.get("fecha_desde")
        fecha_hasta = params.get("fecha_hasta")
        proveedor_id = params.get("proveedor_id")
        bodega_id = params.get("bodega_id")
        estado = params.get("estado")

        # Base: todas las compras
        qs = Compra.objects.all()

        # Aplicar filtros
        if proveedor_id:
            qs = qs.filter(proveedor_id=proveedor_id)

        if bodega_id:
            qs = qs.filter(bodega_id=bodega_id)

        if estado:
            qs = qs.filter(estado=estado.upper())

        if fecha_desde:
            fecha_d = parse_date(fecha_desde)
            if fecha_d:
                qs = qs.filter(fecha__date__gte=fecha_d)

        if fecha_hasta:
            fecha_h = parse_date(fecha_hasta)
            if fecha_h:
                qs = qs.filter(fecha__date__lte=fecha_h)

        # --------- RESUMEN GENERAL ----------
        agg_resumen = qs.aggregate(
            total_compras=Coalesce(
                Sum("total"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )

        total_compras = agg_resumen["total_compras"]
        cantidad_compras = qs.count()

        resumen = {
            "total_compras": str(total_compras),
            "cantidad_compras": cantidad_compras,
        }

        # --------- AGRUPADO POR PROVEEDOR ----------
        por_proveedor_qs = (
            qs.values("proveedor_id", "proveedor__nombre")
            .annotate(
                total=Coalesce(
                    Sum("total"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
            .order_by("-total")[:10]
        )

        por_proveedor = [
            {
                "proveedor_id": row["proveedor_id"],
                "proveedor_nombre": row["proveedor__nombre"],
                "total": str(row["total"]),
            }
            for row in por_proveedor_qs
        ]

        # --------- AGRUPADO POR BODEGA ----------
        por_bodega_qs = (
            qs.values("bodega_id", "bodega__nombre")
            .annotate(
                total=Coalesce(
                    Sum("total"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
            .order_by("-total")[:10]
        )

        por_bodega = [
            {
                "bodega_id": row["bodega_id"],
                "bodega_nombre": row["bodega__nombre"],
                "total": str(row["total"]),
            }
            for row in por_bodega_qs
        ]

        # --------- TOP PRODUCTOS (por cantidad y costo) ----------
        detalles_qs = CompraDetalle.objects.filter(compra__in=qs)

        top_productos_qs = (
            detalles_qs.values("producto_id", "producto__nombre")
            .annotate(
                cantidad_total=Coalesce(
                    Sum("cantidad"),
                    Value(0),
                    output_field=DecimalField(max_digits=14, decimal_places=4),
                ),
                costo_total=Coalesce(
                    Sum("subtotal"),
                    Value(0),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
            )
            .order_by("-costo_total")[:10]
        )

        top_productos = [
            {
                "producto_id": row["producto_id"],
                "producto_nombre": row["producto__nombre"],
                "cantidad_total": str(row["cantidad_total"]),
                "costo_total": str(row["costo_total"]),
            }
            for row in top_productos_qs
        ]

        data = {
            "filtros": {
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "proveedor_id": proveedor_id,
                "bodega_id": bodega_id,
                "estado": estado.upper() if estado else None,
            },
            "resumen": resumen,
            "por_proveedor": por_proveedor,
            "por_bodega": por_bodega,
            "top_productos": top_productos,
        }

        return Response(data)
