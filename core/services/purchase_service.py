# core/services/purchase_service.py

from decimal import Decimal
from django.db import transaction, IntegrityError
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from core.models import (
    Compra,
    CompraDetalle,
    Proveedor,
    Bodega,
    Producto,
    Usuario as UsuarioCore,
)
from core.services.inventory_service import InventoryService


class PurchaseService:
    """
    Servicio de dominio para el módulo de Compras.
    """

    @staticmethod
    @transaction.atomic
    def registrar_compra(data: dict, usuario) -> Compra:
        """
        data viene validado por PurchaseCreateSerializer.

        'usuario' aquí será normalmente request.user (User de Django).
        Dentro del servicio buscamos el UsuarioCore (tabla 'usuario').
        """

        # 1. Resolver usuario core (tabla `usuario`)
        if isinstance(usuario, UsuarioCore):
            usuario_core = usuario
        else:
            usuario_core = UsuarioCore.objects.get(username=usuario.username)

        proveedor = Proveedor.objects.get(pk=data["proveedor_id"])
        bodega = Bodega.objects.get(pk=data["bodega_id"])

        fecha = data.get("fecha") or timezone.now()
        no_documento = data["no_documento"].strip()
        observaciones = (data.get("observaciones") or "").strip()

        # 2. Validación previa: evitar duplicados (proveedor + no_documento)
        if Compra.objects.filter(
            proveedor=proveedor, no_documento=no_documento
        ).exists():
            raise ValidationError(
                {
                    "no_documento": [
                        f"Ya existe una compra para el proveedor "
                        f"'{proveedor.nombre}' con el documento '{no_documento}'."
                    ]
                }
            )

        # 3. Crear cabecera de compra (con try/except como red de seguridad)
        try:
            compra = Compra.objects.create(
                proveedor=proveedor,
                bodega=bodega,
                fecha=fecha,
                no_documento=no_documento,
                total=Decimal("0.00"),
                usuario=usuario_core,
                estado="REGISTRADA",
                observaciones=observaciones,
            )
        except IntegrityError as e:
            # Si por alguna condición de carrera se cuela el duplicado, lo atrapamos aquí
            raise ValidationError(
                {
                    "no_documento": [
                        "No se pudo registrar la compra porque ya existe un documento "
                        f"'{no_documento}' para este proveedor."
                    ]
                }
            ) from e

        total_compra = Decimal("0.00")

        # 4. Crear detalles + movimientos de inventario
        for item in data["items"]:
            producto_id = item["producto_id"]
            try:
                producto = Producto.objects.get(pk=producto_id)
            except Producto.DoesNotExist:
                raise ValidationError(
                    {"items": [f"El producto con id {producto_id} no existe."]}
                )

            cantidad = Decimal(item["cantidad"])
            costo_unit = Decimal(item["costo_unit"])
            subtotal = (cantidad * costo_unit).quantize(Decimal("0.01"))

            CompraDetalle.objects.create(
                compra=compra,
                producto=producto,
                cantidad=cantidad,
                costo_unit=costo_unit,
                subtotal=subtotal,
            )

            total_compra += subtotal

            # Movimiento de inventario + actualización de existencias
            InventoryService.registrar_entrada_compra(
                compra=compra,
                producto=producto,
                bodega=bodega,
                cantidad=cantidad,
                costo_unit=costo_unit,
                usuario=usuario_core,
            )

        # 5. Actualizar total en la compra
        compra.total = total_compra
        compra.save(update_fields=["total"])

        return compra
