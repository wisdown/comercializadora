# core/views/catalog_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.serializers.catalog_serializers import (
    CatalogListFilterSerializer,
    ClienteCreateUpdateSerializer,
    BodegaCreateUpdateSerializer,
    ProductoCreateUpdateSerializer,
)
from core.services.catalog_service import (
    listar_catalogo,
    obtener_catalogo_por_id,
    ##catalog Clientes
    crear_cliente,
    actualizar_cliente,
    desactivar_cliente,
    ## Catalogo Bodega
    crear_bodega,
    actualizar_bodega,
    desactivar_bodega,
    ## Catalogo Bodega
    crear_producto,
    actualizar_producto,
    desactivar_producto,
    listar_productos_detallado,
    obtener_producto_detallado,
)


## Clientes metodos get post
class ClienteListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ser = CatalogListFilterSerializer(data=request.query_params)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        registros = listar_catalogo(
            nombre="cliente",
            limit=data.get("limit", 100),
            offset=data.get("offset", 0),
        )
        return Response(registros)

    def post(self, request):
        ser = ClienteCreateUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        nuevo_id = crear_cliente(ser.validated_data)
        reg = obtener_catalogo_por_id("cliente", nuevo_id)
        return Response(reg, status=status.HTTP_201_CREATED)


##metodos: post put delete
class ClienteDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        reg = obtener_catalogo_por_id("cliente", pk)
        if not reg:
            return Response({"detail": "Cliente no encontrado"}, status=404)
        return Response(reg)

    def put(self, request, pk):
        ser = ClienteCreateUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        ok = actualizar_cliente(pk, ser.validated_data)
        if not ok:
            return Response({"detail": "Cliente no encontrado"}, status=404)

        reg = obtener_catalogo_por_id("cliente", pk)
        return Response(reg)

    def delete(self, request, pk):
        ok = desactivar_cliente(pk)
        if not ok:
            return Response({"detail": "Cliente no encontrado"}, status=404)
        return Response(status=204)


## Bodega
class BodegaListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ser = CatalogListFilterSerializer(data=request.query_params)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        registros = listar_catalogo(
            nombre="bodega",
            limit=data.get("limit", 100),
            offset=data.get("offset", 0),
        )
        return Response(registros)

    def post(self, request):
        ser = BodegaCreateUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        bodega_id = crear_bodega(ser.validated_data)
        reg = obtener_catalogo_por_id("bodega", bodega_id)
        return Response(reg, status=status.HTTP_201_CREATED)


class BodegaDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        reg = obtener_catalogo_por_id("bodega", pk)
        if not reg:
            return Response(
                {"detail": "Bodega no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(reg)

    def put(self, request, pk: int):
        ser = BodegaCreateUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        ok = actualizar_bodega(pk, ser.validated_data)
        if not ok:
            return Response(
                {"detail": "Bodega no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reg = obtener_catalogo_por_id("bodega", pk)
        return Response(reg)

    def delete(self, request, pk: int):
        ok = desactivar_bodega(pk)
        if not ok:
            return Response(
                {"detail": "Bodega no encontrada o ya inactiva."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


## producto
class ProductoListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ser = CatalogListFilterSerializer(data=request.query_params)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        registros = listar_productos_detallado(
            limit=data.get("limit", 100),
            offset=data.get("offset", 0),
        )
        return Response(registros)

    def post(self, request):
        ser = ProductoCreateUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            prod_id = crear_producto(ser.validated_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        reg = obtener_producto_detallado(prod_id)
        return Response(reg, status=status.HTTP_201_CREATED)


##
class ProductoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        reg = obtener_producto_detallado(pk)
        if not reg:
            return Response(
                {"detail": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(reg)

    def put(self, request, pk: int):
        ser = ProductoCreateUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            ok = actualizar_producto(pk, ser.validated_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if not ok:
            return Response(
                {"detail": "Producto no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reg = obtener_producto_detallado(pk)
        return Response(reg)

    def delete(self, request, pk: int):
        ok = desactivar_producto(pk)
        if not ok:
            return Response(
                {
                    "detail": (
                        "No se puede desactivar el producto porque tiene existencia "
                        "positiva o no fue encontrado."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
