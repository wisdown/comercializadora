# core/services/order_service.py
from decimal import Decimal
from django.db import connection, transaction
from django.utils import timezone


class StockError(Exception):
    """Errores relacionados con existencias / stock."""

    ...


class PedidoError(Exception):
    """Errores de flujo de negocio de pedidos."""

    ...


def _fetchall_dict(cur):
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _get_usuario_id(username: str) -> int:
    """
    Obtiene el id de la tabla `usuario` a partir del username.
    """
    with connection.cursor() as cur:
        cur.execute(
            "SELECT id FROM usuario WHERE username=%s LIMIT 1",
            [username],
        )
        row = cur.fetchone()
    if not row:
        raise PedidoError(
            f"Usuario de negocio no encontrado para username={username!r}"
        )
    return int(row[0])


def obtener_pedido(pedido_id: int):
    """
    Devuelve un dict con cabecera + detalle del pedido.
    """
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, fecha, total, cliente_id, usuario_id, bodega_id, estado
            FROM pedido
            WHERE id = %s
            """,
            [pedido_id],
        )
        row = cur.fetchone()
        if not row:
            return None

        head = dict(
            zip(
                [
                    "id",
                    "fecha",
                    "total",
                    "cliente_id",
                    "usuario_id",
                    "bodega_id",
                    "estado",
                ],
                row,
            )
        )

        cur.execute(
            """
            SELECT producto_id, cantidad, precio_unitario, subtotal
            FROM pedidodetalle
            WHERE pedido_id = %s
            """,
            [pedido_id],
        )
        items = _fetchall_dict(cur)

    head["items"] = items
    return head


# ---------------------------------------------------------------------
# 1) Crear pedido (NO descuenta stock, solo valida existencia)
# ---------------------------------------------------------------------
@transaction.atomic
def crear_pedido(cliente_id: int, bodega_id: int, items: list, username: str) -> int:
    """
    Crea un pedido:
    - Valida que haya existencia suficiente en `existencia` para cada item.
    - Inserta cabecera en `pedido` (estado = 'PENDIENTE').
    - Inserta detalle en `pedidodetalle`.
    NO modifica la tabla `existencia` (el consumo real se hará al facturar).
    """
    if not items:
        raise PedidoError("El pedido requiere al menos un ítem.")

    usuario_id = _get_usuario_id(username)
    now = timezone.now()
    total = Decimal("0.00")

    with connection.cursor() as cur:
        # Validar stock actual para cada producto
        for it in items:
            pid = int(it["producto_id"])
            qty = Decimal(it["cantidad"])

            cur.execute(
                """
                SELECT cantidad
                FROM existencia
                WHERE producto_id = %s AND bodega_id = %s
                """,
                [pid, bodega_id],
            )
            row = cur.fetchone()
            if not row:
                raise StockError(
                    f"Producto {pid}: no existe registro de stock en bodega {bodega_id}."
                )
            cantidad = Decimal(str(row[0]))
            if qty > cantidad:
                raise StockError(
                    f"Producto {pid}: existencia {cantidad}, solicitado {qty}."
                )

        # Insertar cabecera
        cur.execute(
            """
            INSERT INTO pedido (fecha, total, cliente_id, usuario_id, bodega_id, estado)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [now, Decimal("0.00"), cliente_id, usuario_id, bodega_id, "ABIERTO"],
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        pedido_id = int(cur.fetchone()[0])

        # Insertar detalle + acumular total
        for it in items:
            pid = int(it["producto_id"])
            qty = Decimal(it["cantidad"])
            pu = Decimal(it["precio_unitario"])
            sub = (qty * pu).quantize(Decimal("0.01"))
            total += sub

            cur.execute(
                """
                INSERT INTO pedidodetalle (pedido_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [pedido_id, pid, qty, pu, sub],
            )

        # Actualizar total
        cur.execute(
            "UPDATE pedido SET total = %s WHERE id = %s",
            [total, pedido_id],
        )

    return pedido_id


# ---------------------------------------------------------------------
# 2) Reemplazar ítems del pedido (solo PENDIENTE)
# ---------------------------------------------------------------------
@transaction.atomic
def reemplazar_items_pedido(pedido_id: int, items: list, username: str):
    """
    Reemplaza COMPLETAMENTE los ítems de un pedido PENDIENTE.
    - Vuelve a validar existencias.
    - Borra el detalle anterior.
    - Inserta el nuevo detalle y recalcula total.
    """
    if not items:
        raise PedidoError("Debes enviar al menos un ítem.")

    with connection.cursor() as cur:
        # Bloquear cabecera
        cur.execute(
            "SELECT estado, bodega_id FROM pedido WHERE id = %s FOR UPDATE",
            [pedido_id],
        )
        row = cur.fetchone()
        if not row:
            raise PedidoError("Pedido no existe.")

        estado, bodega_id = row
        if estado != "ABIERTO":
            raise PedidoError("Solo pedidos en estado ABIERTO pueden confirmarse.")

        # Validar stock con las nuevas cantidades
        for it in items:
            pid = int(it["producto_id"])
            qty = Decimal(it["cantidad"])
            cur.execute(
                """
                SELECT cantidad
                FROM existencia
                WHERE producto_id = %s AND bodega_id = %s
                """,
                [pid, bodega_id],
            )
            row = cur.fetchone()
            if not row:
                raise StockError(
                    f"Producto {pid}: no existe registro de stock en bodega {bodega_id}."
                )
            cantidad = Decimal(str(row[0]))
            if qty > cantidad:
                raise StockError(
                    f"Producto {pid}: existencia {cantidad}, solicitado {qty}."
                )

        # Limpiar detalle actual
        cur.execute(
            "DELETE FROM pedidodetalle WHERE pedido_id = %s",
            [pedido_id],
        )

        # Insertar nuevo detalle y recalcular total
        total = Decimal("0.00")
        for it in items:
            pid = int(it["producto_id"])
            qty = Decimal(it["cantidad"])
            pu = Decimal(it["precio_unitario"])
            sub = (qty * pu).quantize(Decimal("0.01"))
            total += sub

            cur.execute(
                """
                INSERT INTO pedidodetalle (pedido_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [pedido_id, pid, qty, pu, sub],
            )

        cur.execute(
            "UPDATE pedido SET total = %s WHERE id = %s",
            [total, pedido_id],
        )

    return obtener_pedido(pedido_id)


# ---------------------------------------------------------------------
# 3) Confirmar pedido (FACTURAR): descuenta stock y cambia estado
# ---------------------------------------------------------------------
@transaction.atomic
def confirmar_pedido(pedido_id: int, username: str):
    """
    Confirma (factura) un pedido:
    - Verifica que esté en estado PENDIENTE.
    - Verifica existencia nuevamente.
    - Descuenta de `existencia.cantidad`.
    - Cambia estado a 'FACTURADO'.
    (Por ahora NO crea registro en tabla venta; se puede agregar después.)
    """
    with connection.cursor() as cur:
        # Leer pedido con lock
        cur.execute(
            """
            SELECT id, total, cliente_id, usuario_id, bodega_id, estado
            FROM pedido
            WHERE id = %s
            FOR UPDATE
            """,
            [pedido_id],
        )
        row = cur.fetchone()
        if not row:
            raise PedidoError("Pedido no existe.")
        _id, total, cliente_id, usuario_id, bodega_id, estado = row

        if estado != "ABIERTO":
            raise PedidoError("Solo pedidos en estado ABIERTO pueden confirmarse.")

        # Leer detalle
        cur.execute(
            """
            SELECT producto_id, cantidad
            FROM pedidodetalle
            WHERE pedido_id = %s
            """,
            [pedido_id],
        )
        items = cur.fetchall()

        # Validar existencia y descontar
        for pid, qty in items:
            qty = Decimal(str(qty))

            cur.execute(
                """
                SELECT cantidad
                FROM existencia
                WHERE producto_id = %s AND bodega_id = %s
                FOR UPDATE
                """,
                [pid, bodega_id],
            )
            row = cur.fetchone()
            if not row:
                raise StockError(
                    f"Producto {pid}: no existe registro de stock en bodega {bodega_id}."
                )
            cantidad = Decimal(str(row[0]))
            if qty > cantidad:
                raise StockError(
                    f"Producto {pid}: existencia {cantidad}, requerido {qty}."
                )

            cur.execute(
                """
                UPDATE existencia
                SET cantidad = cantidad - %s
                WHERE producto_id = %s AND bodega_id = %s
                """,
                [qty, pid, bodega_id],
            )

        # Cambiar estado del pedido
        cur.execute(
            "UPDATE pedido SET estado = %s WHERE id = %s",
            ["FACTURADO", pedido_id],
        )

    return obtener_pedido(pedido_id)


@transaction.atomic
def cancelar_pedido(pedido_id: int, username: str):
    """
    Cancela un pedido:
    - Solo se permite cancelar si NO está FACTURADO.
    - Si ya está CANCELADO, devuelve el pedido tal cual (operación idempotente).
    - Con el modelo actual, NO se modifica `existencia` porque el stock
      solo se descuenta al confirmar (FACTURAR).
    """
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, estado, bodega_id
            FROM pedido
            WHERE id = %s
            FOR UPDATE
            """,
            [pedido_id],
        )
        row = cur.fetchone()
        if not row:
            raise PedidoError("Pedido no existe.")

        _id, estado, bodega_id = row

        if estado == "FACTURADO":
            raise PedidoError("No se puede cancelar un pedido FACTURADO.")

        if estado == "CANCELADO":
            # Ya estaba cancelado; devolvemos su estado actual
            return obtener_pedido(pedido_id)

        # Estados posibles aquí: ABIERTO o RESERVADO (si algún día lo usas)
        # Como aún no hay reservas reales de stock, no tocamos `existencia`.
        cur.execute(
            "UPDATE pedido SET estado = %s WHERE id = %s",
            ["CANCELADO", pedido_id],
        )

    return obtener_pedido(pedido_id)


def listar_pedidos(cliente_id=None, estado=None, fecha_desde=None, fecha_hasta=None):
    """
    Lista pedidos con filtros opcionales.
    - cliente_id: filtra por cliente.
    - estado: 'ABIERTO','RESERVADO','FACTURADO','CANCELADO'.
    - fecha_desde / fecha_hasta: rango sobre pedido.fecha (date o datetime).
    Devuelve solo cabeceras (sin items) para hacer el listado más ligero.
    """
    sql = """
        SELECT id, fecha, total, cliente_id, usuario_id, bodega_id, estado
        FROM pedido
    """
    condiciones = []
    params = []

    if cliente_id is not None:
        condiciones.append("cliente_id = %s")
        params.append(cliente_id)

    if estado:
        condiciones.append("estado = %s")
        params.append(estado)

    if fecha_desde:
        condiciones.append("fecha >= %s")
        params.append(fecha_desde)

    if fecha_hasta:
        condiciones.append("fecha <= %s")
        params.append(fecha_hasta)

    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)

    sql += " ORDER BY fecha DESC, id DESC LIMIT 100"

    with connection.cursor() as cur:
        cur.execute(sql, params)
        return _fetchall_dict(cur)
