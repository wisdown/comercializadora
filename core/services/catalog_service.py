# core/services/catalog_service.py
from django.db import transaction, connection

# Tablas válidas (protegemos contra inyección)
VALID_TABLES = {
    "cliente": "cliente",
    "bodega": "bodega",
    "producto": "producto",
}


def _fetchall_dict(cur):
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _fetchone_dict(cur):
    cols = [c[0] for c in cur.description]
    row = cur.fetchone()
    if not row:
        return None
    return dict(zip(cols, row))


def listar_catalogo(nombre: str, limit: int = 100, offset: int = 0):
    """
    Lista registros de una tabla de catálogo (cliente, bodega, producto).
    Solo lectura.
    """
    table = VALID_TABLES.get(nombre)
    if not table:
        raise ValueError(f"Catálogo desconocido: {nombre}")

    sql = f"SELECT * FROM {table} ORDER BY id LIMIT %s OFFSET %s"
    with connection.cursor() as cur:
        cur.execute(sql, [limit, offset])
        return _fetchall_dict(cur)


def obtener_catalogo_por_id(nombre: str, pk: int):
    """
    Obtiene un registro por ID en una tabla de catálogo.
    """
    table = VALID_TABLES.get(nombre)
    if not table:
        raise ValueError(f"Catálogo desconocido: {nombre}")

    sql = f"SELECT * FROM {table} WHERE id = %s"
    with connection.cursor() as cur:
        cur.execute(sql, [pk])
        return _fetchone_dict(cur)


## crud del catalogo Clientes
@transaction.atomic
def crear_cliente(data: dict) -> int:
    with connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO cliente
                (nombre, dpi, nit, telefono, direccion, email, estado)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                data.get("nombre"),
                data.get("dpi"),
                data.get("nit"),
                data.get("telefono"),
                data.get("direccion"),
                data.get("email"),
                data.get("estado", "ACTIVO"),
            ],
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        return cur.fetchone()[0]


@transaction.atomic
def actualizar_cliente(pk: int, data: dict) -> bool:
    with connection.cursor() as cur:
        cur.execute(
            """
            UPDATE cliente
            SET nombre=%s,
                dpi=%s,
                nit=%s,
                telefono=%s,
                direccion=%s,
                email=%s,
                estado=%s
            WHERE id=%s
            """,
            [
                data.get("nombre"),
                data.get("dpi"),
                data.get("nit"),
                data.get("telefono"),
                data.get("direccion"),
                data.get("email"),
                data.get("estado"),
                pk,
            ],
        )
        return cur.rowcount > 0


@transaction.atomic
def desactivar_cliente(pk: int) -> bool:
    with connection.cursor() as cur:
        cur.execute(
            """
            UPDATE cliente
            SET estado = 'INACTIVO'
            WHERE id = %s
            """,
            [pk],
        )
        return cur.rowcount > 0


## crud del catalogo Bodega
@transaction.atomic
def crear_bodega(data: dict) -> int:
    with connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO bodega (nombre, ubicacion, activo)
            VALUES (%s, %s, %s)
            """,
            [
                data.get("nombre"),
                data.get("ubicacion"),
                1 if data.get("activo", True) else 0,
            ],
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        return cur.fetchone()[0]


@transaction.atomic
def actualizar_bodega(pk: int, data: dict) -> bool:
    with connection.cursor() as cur:
        cur.execute(
            """
            UPDATE bodega
            SET nombre=%s,
                ubicacion=%s,
                activo=%s
            WHERE id=%s
            """,
            [
                data.get("nombre"),
                data.get("ubicacion"),
                1 if data.get("activo", True) else 0,
                pk,
            ],
        )
        return cur.rowcount > 0


@transaction.atomic
def desactivar_bodega(pk: int) -> bool:
    with connection.cursor() as cur:
        cur.execute(
            """
            UPDATE bodega
            SET activo = 0
            WHERE id = %s
            """,
            [pk],
        )
        return cur.rowcount > 0


## crud del catalogo Producto
## Helper para validar FKs
def _existe_registro(tabla: str, pk: int) -> bool:
    """
    Verifica si existe un registro en una tabla por id.
    Ajusta solo si tus nombres de tabla son diferentes.
    """
    with connection.cursor() as cur:
        cur.execute(f"SELECT 1 FROM {tabla} WHERE id=%s LIMIT 1", [pk])
        return cur.fetchone() is not None


## Helper para verificar existencia en “existencia”
def _producto_tiene_existencia(pk: int) -> bool:
    """
    Devuelve True si el producto tiene existencia positiva en alguna bodega.
    """
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT SUM(cantidad)
            FROM existencia
            WHERE producto_id = %s
            """,
            [pk],
        )
        row = cur.fetchone()
        if not row or row[0] is None:
            return False
        return row[0] > 0


@transaction.atomic
def crear_producto(data: dict) -> int:
    """
    Crea un producto validando FKs y reglas básicas.
    """
    marca_id = data.get("marca_id")
    categoria_id = data.get("categoria_id")
    impuesto_id = data.get("impuesto_id")

    # Validación de FKs si vienen informados
    if marca_id is not None and marca_id != "":
        if not _existe_registro("marca", marca_id):
            raise ValueError(f"Marca {marca_id} no existe.")

    if categoria_id is not None and categoria_id != "":
        if not _existe_registro("categoria", categoria_id):
            raise ValueError(f"Categoría {categoria_id} no existe.")

    if impuesto_id is not None and impuesto_id != "":
        if not _existe_registro("impuesto", impuesto_id):
            raise ValueError(f"Impuesto {impuesto_id} no existe.")

    # Manejo de atributos_json → dict o None
    import json

    atributos = data.get("atributos_json")
    if atributos is not None:
        atributos = json.dumps(atributos)

    with connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO producto
                (sku, nombre, marca_id, categoria_id, modelo,
                 requiere_serie, atributos_json,
                 costo_ref, precio_base, impuesto_id, activo)
            VALUES
                (%s,  %s,     %s,       %s,           %s,
                 %s,            %s,
                 %s,       %s,          %s,         %s)
            """,
            [
                data.get("sku"),
                data.get("nombre"),
                marca_id,
                categoria_id,
                data.get("modelo"),
                1 if data.get("requiere_serie", False) else 0,
                atributos,
                data.get("costo_ref", 0),
                data.get("precio_base", 0),
                impuesto_id,
                1 if data.get("activo", True) else 0,
            ],
        )
        cur.execute("SELECT LAST_INSERT_ID()")
        return cur.fetchone()[0]


@transaction.atomic
def actualizar_producto(pk: int, data: dict) -> bool:
    marca_id = data.get("marca_id")
    categoria_id = data.get("categoria_id")
    impuesto_id = data.get("impuesto_id")

    if marca_id is not None and marca_id != "":
        if not _existe_registro("marca", marca_id):
            raise ValueError(f"Marca {marca_id} no existe.")

    if categoria_id is not None and categoria_id != "":
        if not _existe_registro("categoria", categoria_id):
            raise ValueError(f"Categoría {categoria_id} no existe.")

    if impuesto_id is not None and impuesto_id != "":
        if not _existe_registro("impuesto", impuesto_id):
            raise ValueError(f"Impuesto {impuesto_id} no existe.")

    import json

    atributos = data.get("atributos_json")
    if atributos is not None:
        atributos = json.dumps(atributos)

    with connection.cursor() as cur:
        cur.execute(
            """
            UPDATE producto
            SET sku=%s,
                nombre=%s,
                marca_id=%s,
                categoria_id=%s,
                modelo=%s,
                requiere_serie=%s,
                atributos_json=%s,
                costo_ref=%s,
                precio_base=%s,
                impuesto_id=%s,
                activo=%s
            WHERE id=%s
            """,
            [
                data.get("sku"),
                data.get("nombre"),
                marca_id,
                categoria_id,
                data.get("modelo"),
                1 if data.get("requiere_serie", False) else 0,
                atributos,
                data.get("costo_ref", 0),
                data.get("precio_base", 0),
                impuesto_id,
                1 if data.get("activo", True) else 0,
                pk,
            ],
        )
        return cur.rowcount > 0


@transaction.atomic
def desactivar_producto(pk: int) -> bool:
    """
    Borrado lógico: marca activo=0 solo si NO tiene existencia positiva.
    """
    if _producto_tiene_existencia(pk):
        # Aquí podríamos levantar una excepción o devolver False.
        # Opto por False para que la vista devuelva un mensaje más amigable.
        return False

    with connection.cursor() as cur:
        cur.execute(
            """
            UPDATE producto
            SET activo = 0
            WHERE id = %s
            """,
            [pk],
        )
        return cur.rowcount > 0


def listar_productos_detallado(limit: int = 100, offset: int = 0):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT
                p.id,
                p.sku,
                p.nombre,
                p.modelo,
                p.requiere_serie,
                p.costo_ref,
                p.precio_base,
                p.activo,
                p.marca_id,
                m.nombre AS marca_nombre,
                p.categoria_id,
                c.nombre AS categoria_nombre,
                p.impuesto_id,
                i.nombre AS impuesto_nombre,
                i.tasa AS impuesto_tasa
            FROM producto p
            LEFT JOIN marca m ON p.marca_id = m.id
            LEFT JOIN categoria c ON p.categoria_id = c.id
            LEFT JOIN impuesto i ON p.impuesto_id = i.id
            ORDER BY p.id DESC
            LIMIT %s OFFSET %s
            """,
            [limit, offset],
        )
        return _fetchall_dict(cur)


def obtener_producto_detallado(pk: int):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT
                p.id,
                p.sku,
                p.nombre,
                p.modelo,
                p.requiere_serie,
                p.costo_ref,
                p.precio_base,
                p.activo,
                p.marca_id,
                m.nombre AS marca_nombre,
                p.categoria_id,
                c.nombre AS categoria_nombre,
                p.impuesto_id,
                i.nombre AS impuesto_nombre,
                i.tasa AS impuesto_tasa
            FROM producto p
            LEFT JOIN marca m ON p.marca_id = m.id
            LEFT JOIN categoria c ON p.categoria_id = c.id
            LEFT JOIN impuesto i ON p.impuesto_id = i.id
            WHERE p.id = %s
            """,
            [pk],
        )
        return _fetchone_dict(cur)
