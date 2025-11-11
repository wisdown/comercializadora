# erp/core/views/order_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.permissions import HasAnyRole


class SoloVentasDemo(APIView):
    permission_classes = [HasAnyRole(["ADMIN", "VENTAS"])]

    def get(self, request):
        return Response({"ok": True}, status=status.HTTP_200_OK)


class PedidoCreateView(APIView):
    # No pongas instancia aquí
    permission_classes = []  # o déjalo sin definir

    def get_permissions(self):
        # Aquí sí devolvemos la instancia con los roles deseados
        return [HasAnyRole(["ADMIN", "VENTAS"])]

    def post(self, request):
        return Response(
            {"ok": True, "msg": "Pedido creado (demo)"}, status=status.HTTP_201_CREATED
        )

    # (opcional) para que GET no te dé 405 mientras pruebas:
    def get(self, request):
        return Response({"ok": True, "msg": "endpoint vivo"}, status=status.HTTP_200_OK)
