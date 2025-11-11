# core/services/inventory_service.py
from django.db import transaction, connection


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
