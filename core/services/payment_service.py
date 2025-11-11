# core/services/payment_service.py
from django.db import transaction, connection


@transaction.atomic
def registrar_pago_y_aplicar(
    *,
    cliente_id: int,
    metodo: str,
    referencia: str | None,
    monto_total: float,
    usuario_id: int,
    es_deposito_inicial: int = 0,
):
    """
    Registra un pago en la tabla Pago y devuelve su ID generado.
    Si 'es_deposito_inicial' = 1, indica que corresponde a un anticipo o depósito previo.
    """
    with connection.cursor() as cur:
        # Crear Pago
        cur.execute(
            """
            INSERT INTO Pago (cliente_id, metodo, referencia, monto_total, usuario_id, es_deposito_inicial)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            [
                cliente_id,
                metodo,
                referencia,
                monto_total,
                usuario_id,
                es_deposito_inicial,
            ],
        )

        cur.execute("SELECT LAST_INSERT_ID()")
        pago_id = cur.fetchone()[0]

        return pago_id
