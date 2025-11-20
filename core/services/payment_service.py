from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from core.models import (
    Pago,
    AplicacionPago,
    Cuota,
    MovimientoCaja,
)


class PaymentError(Exception):
    pass


@transaction.atomic
def registrar_pago_con_aplicaciones(
    *,
    cliente_id: int,
    metodo: str,
    monto_total: Decimal,
    referencia: str | None,
    usuario_id: int,
    es_deposito_inicial: bool,
    aplicaciones: list[dict],
) -> Pago:

    suma_aplicaciones = sum(Decimal(str(a["monto"])) for a in aplicaciones)
    if suma_aplicaciones != Decimal(str(monto_total)):
        raise PaymentError(
            f"El monto_total ({monto_total}) no coincide con la suma de aplicaciones ({suma_aplicaciones})"
        )

    # 1. Crear el pago (YA se guarda en la BD y tiene id)
    pago = Pago.objects.create(
        cliente_id=cliente_id,
        metodo=metodo,
        referencia=referencia,
        monto_total=monto_total,
        usuario_id=usuario_id,
        es_deposito_inicial=es_deposito_inicial,
        # si en el modelo fecha tiene default/auto_now_add, esta línea es opcional:
        fecha=timezone.now(),
    )

    # 2. Crear aplicaciones
    for app in aplicaciones:
        tipo_objetivo = app["tipo_objetivo"]
        venta_id = app.get("venta_id")
        cuota_id = app.get("cuota_id")
        tipo_aplicacion = app["tipo_aplicacion"]
        monto = Decimal(str(app["monto"]))

        if tipo_objetivo == "VENTA" and not venta_id:
            raise PaymentError("venta_id es requerido cuando tipo_objetivo = 'VENTA'")
        if tipo_objetivo == "CUOTA" and not cuota_id:
            raise PaymentError("cuota_id es requerida cuando tipo_objetivo = 'CUOTA'")

        AplicacionPago.objects.create(
            pago=pago,  # ⬅️ objeto, no pago_id
            venta_id=venta_id,
            cuota_id=cuota_id,
            monto=monto,
            tipo=tipo_aplicacion,
        )

        if cuota_id:
            _aplicar_a_cuota(cuota_id=cuota_id, monto=monto)

    # 3. Movimiento de caja
    MovimientoCaja.objects.create(
        caja_id=1,
        tipo="INGRESO",
        monto=monto_total,
        motivo="Pago de cliente",
        referencia=referencia,
        pago=pago,  # ⬅️ objeto también
    )

    return pago


def _aplicar_a_cuota(*, cuota_id: int, monto: Decimal) -> None:
    cuota = Cuota.objects.select_for_update().get(pk=cuota_id)
    nuevo_saldo = cuota.saldo_cuota - monto
    if nuevo_saldo <= 0:
        cuota.saldo_cuota = Decimal("0.00")
        cuota.estado = "PAGADA"
    else:
        cuota.saldo_cuota = nuevo_saldo
    cuota.save(update_fields=["saldo_cuota", "estado"])
