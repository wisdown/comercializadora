# core/views/payment_views.py

from rest_framework import generics, status
from rest_framework.response import Response

from core.serializers.payment_serializers import (
    PagoCreateSerializer,
    PagoSerializer,
)


class PagoCreateAPIView(generics.CreateAPIView):
    """
    Endpoint:
        POST /api/pagos/
    """

    serializer_class = PagoCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pago = serializer.save()

        output_serializer = PagoSerializer(pago)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
