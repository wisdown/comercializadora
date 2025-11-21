# core/views/payment_query_views.py

from rest_framework import generics
from core.models import Pago
from core.serializers.payment_serializers import PagoSerializer
from core.models import VCarteraAging
from rest_framework.response import Response
from rest_framework.views import APIView
from decimal import Decimal
from collections import defaultdict


class PagosPorClienteListAPIView(generics.ListAPIView):
    """
    GET /api/clientes/<cliente_id>/pagos/

    Lista todos los pagos de un cliente, con sus aplicaciones.
    """

    serializer_class = PagoSerializer

    def get_queryset(self):
        cliente_id = self.kwargs["cliente_id"]
        return Pago.objects.filter(cliente_id=cliente_id).order_by("-fecha", "-id")


class PagosPorVentaListAPIView(generics.ListAPIView):
    """
    GET /api/ventas/<venta_id>/pagos/

    Lista todos los pagos que han aplicado a una venta específica.
    (Filtra por aplicaciones ligadas a esa venta)
    """

    serializer_class = PagoSerializer

    def get_queryset(self):
        venta_id = self.kwargs["venta_id"]
        # Pagos que tienen al menos una AplicacionPago con esa venta
        return (
            Pago.objects.filter(aplicacionpago__venta_id=venta_id)
            .distinct()
            .order_by("-fecha", "-id")
        )


class EstadoCuentaClienteAPIView(APIView):
    """
    GET /api/v1/clientes/<cliente_id>/estado-cuenta/
    Opcional: ?solo_vencidas=1  → filtra solo cuotas vencidas (buckets != '0-AL-DIA')
    """

    def get(self, request, cliente_id: int):
        qs = VCarteraAging.objects.filter(cliente_id=cliente_id)

        # 🔹 Leer query param
        solo_vencidas = request.query_params.get("solo_vencidas")

        # 🔹 Si viene ?solo_vencidas=1 → filtramos a buckets vencidos
        if solo_vencidas == "1":
            qs = qs.exclude(bucket="0-AL-DIA")

        # Caso: cliente sin cuotas que cumplan el filtro
        if not qs.exists():
            data = {
                "cliente_id": cliente_id,
                "cliente": None,
                "resumen": {
                    "total_deuda": "0.00",
                    "total_vencido": "0.00",
                },
                "aging": {
                    "0-AL-DIA": "0.00",
                    "1-30": "0.00",
                    "31-60": "0.00",
                    "61-90": "0.00",
                    ">90": "0.00",
                },
                "cuotas": [],
                "filtros": {
                    "solo_vencidas": solo_vencidas == "1",
                },
            }
            return Response(data)

        cliente_nombre = qs.first().cliente

        total_deuda = Decimal("0.00")
        total_vencido = Decimal("0.00")
        buckets = defaultdict(lambda: Decimal("0.00"))
        cuotas = []

        for row in qs:
            total_deuda += row.saldo
            buckets[row.bucket] += row.saldo

            if row.bucket in ("1-30", "31-60", "61-90", ">90"):
                total_vencido += row.saldo

            cuotas.append(
                {
                    "cuota_id": row.cuota_id,
                    "fecha_venc": row.fecha_venc,
                    "dias_vencidos": row.dias_vencidos,
                    "saldo": str(row.saldo),
                    "bucket": row.bucket,
                }
            )

        data = {
            "cliente_id": cliente_id,
            "cliente": cliente_nombre,
            "resumen": {
                "total_deuda": str(total_deuda),
                "total_vencido": str(total_vencido),
            },
            "aging": {
                "0-AL-DIA": str(buckets.get("0-AL-DIA", Decimal("0.00"))),
                "1-30": str(buckets.get("1-30", Decimal("0.00"))),
                "31-60": str(buckets.get("31-60", Decimal("0.00"))),
                "61-90": str(buckets.get("61-90", Decimal("0.00"))),
                ">90": str(buckets.get(">90", Decimal("0.00"))),
            },
            "cuotas": cuotas,
            "filtros": {
                "solo_vencidas": solo_vencidas == "1",
            },
        }

        return Response(data)


class CarteraDashboardAPIView(APIView):
    """
    GET /api/v1/cartera/dashboard/

    Resumen global de la cartera:
    - Total deuda
    - Total vencido
    - Totales por bucket (aging)
    - Top clientes con mayor deuda vencida
    """

    def get(self, request):
        qs = VCarteraAging.objects.all()

        total_deuda_global = Decimal("0.00")
        total_vencida_global = Decimal("0.00")
        buckets = defaultdict(lambda: Decimal("0.00"))
        deuda_vencida_por_cliente = defaultdict(
            lambda: {"cliente": "", "monto": Decimal("0.00")}
        )

        for row in qs:
            total_deuda_global += row.saldo
            buckets[row.bucket] += row.saldo

            # Vencido = cualquier bucket distinto de 0-AL-DIA
            if row.bucket in ("1-30", "31-60", "61-90", ">90"):
                total_vencida_global += row.saldo
                key = row.cliente_id
                deuda_vencida_por_cliente[key]["cliente"] = row.cliente
                deuda_vencida_por_cliente[key]["monto"] += row.saldo

        # Calcular top morosos (ordenar por monto vencido desc, tomar top 5)
        top_morosos = sorted(
            [
                {
                    "cliente_id": cliente_id,
                    "cliente": info["cliente"],
                    "total_vencido": str(info["monto"]),
                }
                for cliente_id, info in deuda_vencida_por_cliente.items()
            ],
            key=lambda x: Decimal(x["total_vencido"]),
            reverse=True,
        )[:5]

        data = {
            "resumen_global": {
                "total_deuda_global": str(total_deuda_global),
                "total_vencida_global": str(total_vencida_global),
            },
            "aging_global": {
                "0-AL-DIA": str(buckets.get("0-AL-DIA", Decimal("0.00"))),
                "1-30": str(buckets.get("1-30", Decimal("0.00"))),
                "31-60": str(buckets.get("31-60", Decimal("0.00"))),
                "61-90": str(buckets.get("61-90", Decimal("0.00"))),
                ">90": str(buckets.get(">90", Decimal("0.00"))),
            },
            "top_morosos": top_morosos,
        }

        return Response(data)
