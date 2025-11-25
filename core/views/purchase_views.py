# core/views/purchase_views.py

from django.utils.dateparse import parse_date

from rest_framework import status, viewsets, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from core.models import Compra
from core.serializers.purchase_serializers import (
    PurchaseCreateSerializer,
    CompraSerializer,
)
from core.services.purchase_service import PurchaseService


class PurchaseViewSet(viewsets.ModelViewSet):
    """
    /api/v1/compras/

    Filtros disponibles por query params:

    - proveedor_id: int
    - bodega_id: int
    - estado: str (REGISTRADA, ANULADA, CERRADA, etc.)
    - fecha_desde: YYYY-MM-DD
    - fecha_hasta: YYYY-MM-DD

    Ejemplos:

    GET /api/v1/compras/?proveedor_id=1
    GET /api/v1/compras/?bodega_id=1&estado=REGISTRADA
    GET /api/v1/compras/?fecha_desde=2025-11-01&fecha_hasta=2025-11-30
    """

    queryset = Compra.objects.all().order_by("-fecha")
    serializer_class = CompraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        proveedor_id = params.get("proveedor_id")
        bodega_id = params.get("bodega_id")
        estado = params.get("estado")
        fecha_desde = params.get("fecha_desde")
        fecha_hasta = params.get("fecha_hasta")

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

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return PurchaseCreateSerializer
        return CompraSerializer

    def create(self, request, *args, **kwargs):
        serializer = PurchaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        compra = PurchaseService.registrar_compra(
            data=serializer.validated_data,
            usuario=request.user,
        )

        out_serializer = CompraSerializer(compra)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, pk=None):
        """
        POST /api/v1/compras/<id>/anular/

        Body opcional:
        {
          "motivo": "El proveedor facturó mal la cantidad"
        }
        """
        motivo = request.data.get("motivo")
        compra = PurchaseService.anular_compra(
            compra_id=pk,
            usuario=request.user,
            motivo=motivo,
        )
        serializer = CompraSerializer(compra)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PurchasesBySupplierListView(generics.ListAPIView):
    """
    GET /api/v1/proveedores/<id>/compras/

    También soporta filtros por query params:
    - fecha_desde: YYYY-MM-DD
    - fecha_hasta: YYYY-MM-DD
    - bodega_id: int
    - estado: str
    """

    serializer_class = CompraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        proveedor_id = self.kwargs["proveedor_id"]
        qs = Compra.objects.filter(proveedor_id=proveedor_id).order_by("-fecha")

        params = self.request.query_params
        bodega_id = params.get("bodega_id")
        estado = params.get("estado")
        fecha_desde = params.get("fecha_desde")
        fecha_hasta = params.get("fecha_hasta")

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

        return qs
