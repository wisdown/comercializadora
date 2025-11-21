from rest_framework import status, viewsets, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.models import Compra
from core.serializers.purchase_serializers import (
    PurchaseCreateSerializer,
    CompraSerializer,
)
from core.services.purchase_service import PurchaseService


class PurchaseViewSet(viewsets.ModelViewSet):
    """
    /api/v1/compras/
    """

    queryset = Compra.objects.all().order_by("-fecha")
    serializer_class = CompraSerializer
    permission_classes = [IsAuthenticated]

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


class PurchasesBySupplierListView(generics.ListAPIView):
    """
    GET /api/v1/proveedores/<id>/compras/
    """

    serializer_class = CompraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        proveedor_id = self.kwargs["proveedor_id"]
        return Compra.objects.filter(proveedor_id=proveedor_id).order_by("-fecha")
