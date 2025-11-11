# core/services/reservation_service.py
from datetime import datetime, timedelta
from django.db import connection


class ReservationError(Exception):
    """Error personalizado para reservas inválidas."""

    pass


def crear_pedido_con_reserva(cliente_id, usuario_id, bodega_id, items, vence_horas=24):
    """
    Crea un pedido con sus detalles y realiza las reservas de stock o series.
    """
    with connection.cursor() as cur:
        # 1) Crear pedido
        cur.execute(
            """
            INSERT INTO Pedido (cliente_id, usuario_id, bodega_id, estado)
            VALUES (%s, %s, %s, 'ABIERTO')
        """,
            [cliente_id, usuario_id, bodega_id],
        )

        cur.execute("SELECT LAST_INSERT_ID()")
        pedido_id = cur.fetchone()[0]

        # 2) Insert detalle + reservas
        vence_el = datetime.now() + timedelta(hours=vence_horas)

        for it in items:
            cur.execute(
                """
                INSERT INTO PedidoDetalle (pedido_id, producto_id, cantidad, precio_unit)
                VALUES (%s, %s, %s, %s)
            """,
                [pedido_id, it["producto_id"], it["cantidad"], it["precio_unit"]],
            )

            if it.get("usar_series"):
                # Bloquear series disponibles en esa bodega
                series = it.get("series") or []
                if not series:
                    raise ReservationError("Debe seleccionar series disponibles")

                for serie_id in series:
                    # SELECT ... FOR UPDATE de la serie
                    cur.execute(
                        """
                        SELECT id, estado, bodega_id FROM ProductoSerie
                        WHERE id = %s FOR UPDATE
                    """,
                        [serie_id],
                    )
                    row = cur.fetchone()

                    if not row or row[1] != "EN_BODEGA" or row[2] != bodega_id:
                        raise ReservationError("Serie no disponible en esta bodega")

                    # Marcar RESERVADA
                    cur.execute(
                        """
                        UPDATE ProductoSerie
                        SET estado = 'RESERVADA', pedido_id = %s
                        WHERE id = %s
                    """,
                        [pedido_id, serie_id],
                    )

                    # Insertar ReservaSerie
                    cur.execute(
                        """
                        INSERT INTO ReservaSerie (pedido_id, producto_serie_id, vence_el, estado)
                        VALUES (%s, %s, %s, 'ACTIVA')
                    """,
                        [pedido_id, serie_id, vence_el],
                    )
            else:
                # No serie: reservar cantidad (chequeo de disponible)
                # Bloquear existencia con SELECT ... FOR UPDATE
                cur.execute(
                    """
                    SELECT cantidad FROM Existencia
                    WHERE producto_id = %s AND bodega_id = %s FOR UPDATE
                """,
                    [it["producto_id"], bodega_id],
                )
                row = cur.fetchone()
                fisico = row[0] if row else 0

                # Calcular reservado actual
                cur.execute(
                    """
                    SELECT COALESCE(SUM(cantidad), 0) FROM ReservaStock
                    WHERE producto_id = %s AND bodega_id = %s AND estado = 'ACTIVA'
                """,
                    [it["producto_id"], bodega_id],
                )
                reservado = cur.fetchone()[0]
                disponible = fisico - reservado

                if it["cantidad"] > disponible:
                    raise ReservationError("Stock insuficiente para reservar")

                # Insertar reserva
                cur.execute(
                    """
                    INSERT INTO ReservaStock (pedido_id, producto_id, bodega_id, cantidad, vence_el, estado)
                    VALUES (%s, %s, %s, %s, %s, 'ACTIVA')
                """,
                    [pedido_id, it["producto_id"], bodega_id, it["cantidad"], vence_el],
                )

        # 3) Cambiar estado a RESERVADO
        cur.execute("UPDATE Pedido SET estado = 'RESERVADO' WHERE id = %s", [pedido_id])
        return pedido_id
