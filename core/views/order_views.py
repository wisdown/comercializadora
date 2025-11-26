# erp/core/views/order_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.permissions import HasAnyRole
from rest_framework.permissions import IsAuthenticated

from core.serializers.order_serializers import (
    PedidoCreateSerializer,
    PedidoItemsReplaceSerializer,
    PedidoListFilterSerializer,
)

from core.services.order_service import (
    crear_pedido,
    obtener_pedido,
    reemplazar_items_pedido,
    confirmar_pedido,
    cancelar_pedido,
    listar_pedidos,
    StockError,
    PedidoError,
)


class PedidoCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Lista pedidos con filtros opcionales vía query params:
        - cliente_id
        - estado
        - fecha_desde (YYYY-MM-DD)
        - fecha_hasta (YYYY-MM-DD)
        """
        ser = PedidoListFilterSerializer(data=request.query_params)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        pedidos = listar_pedidos(**ser.validated_data)
        return Response(pedidos)

    def post(self, request):
        ser = PedidoCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        try:
            pedido_id = crear_pedido(
                cliente_id=data["cliente_id"],
                bodega_id=data["bodega_id"],
                items=data["items"],
                username=request.user.username,
            )
            pedido = obtener_pedido(pedido_id)
            return Response(pedido, status=status.HTTP_201_CREATED)
        except StockError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PedidoError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PedidoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pedido_id: int):
        pedido = obtener_pedido(pedido_id)
        if not pedido:
            return Response(
                {"detail": "Pedido no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(pedido)


class PedidoItemsReplaceView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pedido_id: int):
        ser = PedidoItemsReplaceSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            pedido = reemplazar_items_pedido(
                pedido_id=pedido_id,
                items=ser.validated_data["items"],
                username=request.user.username,
            )
            return Response(pedido)
        except StockError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PedidoError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PedidoConfirmarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pedido_id: int):
        try:
            pedido = confirmar_pedido(pedido_id, request.user.username)
            return Response(pedido)
        except StockError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PedidoError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


## PedidoCancelarView
class PedidoCancelarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pedido_id: int):
        try:
            pedido = cancelar_pedido(pedido_id, request.user.username)
            return Response(pedido)
        except PedidoError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


##este es otro servicio que se uso de prueba
class SoloVentasDemo(APIView):
    permission_classes = [HasAnyRole(["ADMIN", "VENTAS"])]

    def get(self, request):
        return Response({"ok": True}, status=status.HTTP_200_OK)
