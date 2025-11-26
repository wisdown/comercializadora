# core/services/inventory_service.py
from decimal import Decimal
from django.utils import timezone
from django.db import transaction, connection


from core.models import (
    MovimientoInventario,
    Existencia,
    Bodega,
    Producto,
    Compra,
    Usuario,
    Venta,
)


@transaction.atomic
def ingreso_inventario(*, bodega_destino_id: int, items: list, usuario_id: int):
    """
    Registra el ingreso de inventario en una bodega, creando series o
    actualizando existencias según corresponda.
    """
    with connection.cursor() as cur:
        for it in items:
            producto_id = it["producto_id"]
            cantidad = it["cantidad"]
            costo_unit = it.get("costo_unit", 0)
            series = it.get("series", [])

            if series:
                # Crear series
                for s in series:
                    cur.execute(
                        """
                        INSERT INTO ProductoSerie (producto_id, serie, estado, bodega_id)
                        VALUES (%s, %s, 'EN_BODEGA', %s)
                    """,
                        [producto_id, s, bodega_destino_id],
                    )

                    # Movimiento por serie = 1
                    cur.execute(
                        """
                        INSERT INTO MovimientoInventario (tipo, bodega_destino_id, producto_id, cantidad, costo_unit, referencia, usuario_id)
                        VALUES ('COMPRA', %s, %s, 1, %s, 'INGRESO SERIE', %s)
                    """,
                        [bodega_destino_id, producto_id, costo_unit, usuario_id],
                    )
            else:
                # Actualizar Existencia (UPSERT básico)
                cur.execute(
                    """
                    INSERT INTO Existencia (producto_id, bodega_id, cantidad)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE cantidad = cantidad + VALUES(cantidad)
                """,
                    [producto_id, bodega_destino_id, cantidad],
                )

                # Movimiento de compra
                cur.execute(
                    """
                    INSERT INTO MovimientoInventario (tipo, bodega_destino_id, producto_id, cantidad, costo_unit, referencia, usuario_id)
                    VALUES ('COMPRA', %s, %s, %s, %s, 'INGRESO', %s)
                """,
                    [bodega_destino_id, producto_id, cantidad, costo_unit, usuario_id],
                )


class InventoryService:
    """
    Servicio centralizado para manejar movimientos de inventario y existencias.
    """

    ## registrar_entrada_compra
    @staticmethod
    @transaction.atomic
    def registrar_entrada_compra(
        *,
        compra: Compra,
        producto: Producto,
        bodega: Bodega,
        cantidad: Decimal,
        costo_unit: Decimal,
        usuario: Usuario,
    ) -> MovimientoInventario:
        """
        Registra:
        - MovimientoInventario tipo COMPRA (entrada a bodega_destino)
        - Actualiza tabla existencia (suma a cantidad)
        """

        movimiento = MovimientoInventario.objects.create(
            fecha=compra.fecha,
            tipo="COMPRA",
            bodega_origen=None,
            bodega_destino=bodega,
            producto=producto,
            cantidad=cantidad,
            costo_unit=costo_unit,
            referencia=f"COMPRA #{compra.id} DOC: {compra.no_documento}",
            usuario=usuario,
            compra=compra,
        )

        existencia, created = Existencia.objects.get_or_create(
            producto=producto,
            bodega=bodega,
            defaults={
                "cantidad": Decimal("0.0000"),
                "reservado": Decimal("0.00"),
            },
        )

        existencia.cantidad = (
            Decimal(existencia.cantidad) + Decimal(cantidad)
        ).quantize(Decimal("0.0001"))
        existencia.save(update_fields=["cantidad"])

        return movimiento

    ## revertir_compra
    @staticmethod
    @transaction.atomic
    def revertir_compra(
        *,
        compra: Compra,
        usuario: Usuario,
    ):
        """
        Reversa total de la compra:
        - Por cada movimiento de tipo COMPRA ligado a esta compra,
          crea un movimiento inverso (tipo AJUSTE, salida de bodega_destino)
        - Resta existencias en la tabla existencia.

        Asume que NO se valida si habrá existencias negativas (eso puede agregarse después).
        """

        # Traer todos los movimientos de inventario asociados a la compra
        movimientos = MovimientoInventario.objects.filter(compra=compra, tipo="COMPRA")

        for mov in movimientos:
            bodega = mov.bodega_destino
            producto = mov.producto
            cantidad = Decimal(mov.cantidad)

            if bodega is None:
                # Por seguridad, si no hay bodega_destino, lo saltamos
                continue

            # 1. Crear movimiento inverso (salida)
            MovimientoInventario.objects.create(
                fecha=timezone.now(),
                tipo="AJUSTE",  # usamos AJUSTE como reversa de COMPRA
                bodega_origen=bodega,
                bodega_destino=None,
                producto=producto,
                cantidad=cantidad * Decimal("-1"),  # cantidad negativa
                costo_unit=mov.costo_unit,
                referencia=f"ANULACION COMPRA #{compra.id} DOC: {compra.no_documento}",
                usuario=usuario,
                compra=compra,
            )

            # 2. Actualizar existencias (restar la cantidad)
            try:
                existencia = Existencia.objects.get(producto=producto, bodega=bodega)
            except Existencia.DoesNotExist:
                # Si no existe registro de existencia, no hay nada que restar
                continue

            existencia.cantidad = (Decimal(existencia.cantidad) - cantidad).quantize(
                Decimal("0.0001")
            )
            existencia.save(update_fields=["cantidad"])

    ## registrar_salida_venta
    @staticmethod
    @transaction.atomic
    def registrar_salida_venta(
        *,
        venta: Venta,
        producto: Producto,
        bodega: Bodega,
        cantidad: Decimal,
        costo_unit: Decimal,
        usuario: Usuario,
    ) -> MovimientoInventario:
        """Registra una SALIDA de inventario por VENTA.

        - Crea un MovimientoInventario tipo VENTA/SALIDA.
        - Resta la cantidad de Existencia.
        - Opcional: validar stock suficiente.
        """

        # 1) Obtener o crear existencia
        existencia, _ = Existencia.objects.select_for_update().get_or_create(
            producto=producto,
            bodega=bodega,
            defaults={"cantidad": Decimal("0")},
        )

        if existencia.cantidad < cantidad:
            # Aquí podrías lanzar una excepción personalizada
            # o manejarlo según la política de negocio.
            raise ValueError(
                f"Stock insuficiente para el producto {producto.id} en bodega {bodega.id}. "
                f"Disponible: {existencia.cantidad}, requerido: {cantidad}"
            )

        cantidad_antes = existencia.cantidad
        cantidad_despues = cantidad_antes - cantidad

        # 2) Actualizar existencia (restar)
        existencia.cantidad = cantidad_despues
        existencia.save()

        # 3) Crear movimiento de inventario
        movimiento = MovimientoInventario.objects.create(
            fecha=venta.fecha if hasattr(venta, "fecha") else timezone.now(),
            tipo="VENTA",  # o "SALIDA", según tu DDL
            bodega_origen=bodega,
            bodega_destino=None,
            producto=producto,
            cantidad=cantidad,
            costo_unit=costo_unit,
            referencia=f"VENTA #{venta.id}",
            usuario=usuario,
            venta=venta,  # si el modelo tiene FK venta_id; si no, quitar este campo
            existencia_antes=cantidad_antes,
            existencia_despues=cantidad_despues,
        )

        return movimiento

    ##reversar_salida_venta
    @staticmethod
    @transaction.atomic
    def reversar_salida_venta(
        *,
        venta: Venta,
        producto: Producto,
        bodega: Bodega,
        cantidad: Decimal,
        usuario: Usuario,
    ) -> MovimientoInventario:
        """Reversa una salida de inventario por VENTA (por ejemplo, al anular una venta).

        - Suma nuevamente la cantidad a Existencia.
        - Crea un MovimientoInventario de tipo AJUSTE/ANULACION.
        """

        existencia, _ = Existencia.objects.select_for_update().get_or_create(
            producto=producto,
            bodega=bodega,
            defaults={"cantidad": Decimal("0")},
        )

        cantidad_antes = existencia.cantidad
        cantidad_despues = cantidad_antes + cantidad

        existencia.cantidad = cantidad_despues
        existencia.save()

        movimiento = MovimientoInventario.objects.create(
            fecha=timezone.now(),
            tipo="AJUSTE",  # o "ANULACION_VENTA" si manejas códigos específicos
            bodega_origen=None,
            bodega_destino=bodega,
            producto=producto,
            cantidad=cantidad,
            costo_unit=Decimal("0"),  # o el costo que definas según tu política
            referencia=f"REVERSA VENTA #{venta.id}",
            usuario=usuario,
            venta=venta,
            existencia_antes=cantidad_antes,
            existencia_despues=cantidad_despues,
        )

        return movimiento
