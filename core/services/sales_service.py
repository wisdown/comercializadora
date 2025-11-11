# core/services/sales_service.py
from django.db import transaction, connection


class BillingError(Exception):
    """Error personalizado para facturación inválida."""

    pass


@transaction.atomic
def confirm_order_to_invoice(
    *, pedido_id: int, usuario_id: int, tipo_pago: str, total: float
) -> int:
    """
    Convierte un pedido en una venta (factura) consumiendo las reservas
    de productos o series y generando movimientos de inventario.
    """
    with connection.cursor() as cur:
        # Datos base del pedido
        cur.execute(
            "SELECT cliente_id, bodega_id, estado FROM Pedido WHERE id=%s FOR UPDATE",
            [pedido_id],
        )
        ped = cur.fetchone()
        if not ped or ped[2] not in ("RESERVADO", "ABIERTO"):
            raise BillingError("Pedido no válido para facturar")
        cliente_id, bodega_id = ped[0], ped[1]

        # Crear Venta
        cur.execute(
            """
            INSERT INTO Venta (cliente_id, usuario_id, bodega_id, tipo_pago, total, estado, pedido_id)
            VALUES (%s, %s, %s, %s, %s, 'EMITIDA', %s)
        """,
            [cliente_id, usuario_id, bodega_id, tipo_pago, total, pedido_id],
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        venta_id = cur.fetchone()[0]

        # Copiar detalle
        cur.execute(
            "SELECT producto_id, cantidad, precio_unit FROM PedidoDetalle WHERE pedido_id=%s",
            [pedido_id],
        )
        for producto_id, cantidad, precio_unit in cur.fetchall():
            cur.execute(
                """
                INSERT INTO VentaDetalle (venta_id, producto_id, cantidad, precio_unit)
                VALUES (%s, %s, %s, %s)
            """,
                [venta_id, producto_id, cantidad, precio_unit],
            )

        # Consumir reservas: series
        cur.execute(
            "SELECT producto_serie_id FROM ReservaSerie WHERE pedido_id=%s AND estado='ACTIVA' FOR UPDATE",
            [pedido_id],
        )
        for (serie_id,) in cur.fetchall():
            # Marcar DESPACHADA + asignar venta
            cur.execute(
                """
                UPDATE ProductoSerie
                SET estado='DESPACHADA', venta_id=%s
                WHERE id=%s
            """,
                [venta_id, serie_id],
            )

            # MovimientoInventario -1 por serie
            cur.execute(
                """
                INSERT INTO MovimientoInventario (tipo, bodega_origen_id, producto_id, cantidad, costo_unit, referencia, usuario_id)
                SELECT 'VENTA', %s, ps.producto_id, 1, p.costo_ref, CONCAT('VENTA ', %s), %s
                FROM ProductoSerie ps JOIN Producto p ON p.id=ps.producto_id
                WHERE ps.id=%s
            """,
                [bodega_id, venta_id, usuario_id, serie_id],
            )

            # Marcar reserva como CONSUMIDA
            cur.execute(
                "UPDATE ReservaSerie SET estado='CONSUMIDA' WHERE pedido_id=%s AND producto_serie_id=%s",
                [pedido_id, serie_id],
            )

        # Consumir reservas: no serie
        cur.execute(
            "SELECT producto_id, bodega_id, cantidad FROM ReservaStock WHERE pedido_id=%s AND estado='ACTIVA' FOR UPDATE",
            [pedido_id],
        )
        for producto_id, bodega_id, cantidad in cur.fetchall():
            # Descontar Existencia
            cur.execute(
                """
                UPDATE Existencia
                SET cantidad = cantidad - %s
                WHERE producto_id=%s AND bodega_id=%s
            """,
                [cantidad, producto_id, bodega_id],
            )

            # MovimientoInventario negativo
            cur.execute(
                """
                INSERT INTO MovimientoInventario (tipo, bodega_origen_id, producto_id, cantidad, costo_unit, referencia, usuario_id)
                SELECT 'VENTA', %s, p.id, %s, p.costo_ref, CONCAT('VENTA ', %s), %s
                FROM Producto p WHERE p.id=%s
            """,
                [bodega_id, cantidad, venta_id, usuario_id, producto_id],
            )

            # Marcar reserva consumida
            cur.execute(
                "UPDATE ReservaStock SET estado='CONSUMIDA' WHERE pedido_id=%s AND producto_id=%s",
                [pedido_id, producto_id],
            )

        # Cerrar pedido
        cur.execute("UPDATE Pedido SET estado='FACTURADO' WHERE id=%s", [pedido_id])
        return venta_id
