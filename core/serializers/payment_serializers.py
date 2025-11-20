# core/serializers/payment_serializers.py

from decimal import Decimal
from rest_framework import serializers

from core.models import Pago, AplicacionPago
from core.services.payment_service import (
    registrar_pago_con_aplicaciones,
    PaymentError,
)


class AplicacionPagoInputSerializer(serializers.Serializer):
    """
    Representa una línea de aplicación de pago dentro del request.
    Solo para ENTRADA.
    """

    TIPO_OBJETIVO_CHOICES = (
        ("VENTA", "VENTA"),
        ("CUOTA", "CUOTA"),
    )

    TIPO_APLICACION_CHOICES = (
        ("CUOTA", "CUOTA"),
        ("ANTICIPO", "ANTICIPO"),
        ("MORA", "MORA"),
        ("INTERES", "INTERES"),
        ("CAPITAL", "CAPITAL"),
        ("OTRO", "OTRO"),
    )

    tipo_objetivo = serializers.ChoiceField(choices=TIPO_OBJETIVO_CHOICES)
    venta_id = serializers.IntegerField(required=False, allow_null=True)
    cuota_id = serializers.IntegerField(required=False, allow_null=True)
    tipo_aplicacion = serializers.ChoiceField(choices=TIPO_APLICACION_CHOICES)
    monto = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate(self, attrs):
        tipo_objetivo = attrs.get("tipo_objetivo")
        venta_id = attrs.get("venta_id")
        cuota_id = attrs.get("cuota_id")

        if tipo_objetivo == "VENTA" and not venta_id:
            raise serializers.ValidationError(
                {"venta_id": "Es requerido cuando tipo_objetivo = 'VENTA'."}
            )
        if tipo_objetivo == "CUOTA" and not cuota_id:
            raise serializers.ValidationError(
                {"cuota_id": "Es requerido cuando tipo_objetivo = 'CUOTA'."}
            )

        return attrs


class AplicacionPagoSerializer(serializers.ModelSerializer):
    """
    Para SALIDA de datos (cuando devolvemos el pago creado).
    """

    class Meta:
        model = AplicacionPago
        fields = [
            "id",
            "venta_id",
            "cuota_id",
            "monto",
            "tipo",
        ]


class PagoSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura del pago con sus aplicaciones.
    """

    aplicaciones = AplicacionPagoSerializer(
        many=True,
        source="aplicacionpago_set",  # si tienes related_name distinto, cámbialo aquí
        read_only=True,
    )

    class Meta:
        model = Pago
        fields = [
            "id",
            "fecha",
            "cliente_id",
            "metodo",
            "referencia",
            "monto_total",
            "usuario_id",
            "es_deposito_inicial",
            "aplicaciones",
        ]


class PagoCreateSerializer(serializers.Serializer):
    """
    Serializer para recibir un pago con sus aplicaciones (POST).
    """

    cliente_id = serializers.IntegerField()
    metodo = serializers.ChoiceField(
        choices=("EFECTIVO", "POS", "TRANSFERENCIA", "DEPOSITO")
    )
    monto_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    referencia = serializers.CharField(
        max_length=120,
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    es_deposito_inicial = serializers.BooleanField(required=False, default=False)

    # Por ahora viene en el body; más adelante se puede sacar del usuario autenticado
    usuario_id = serializers.IntegerField()

    aplicaciones = AplicacionPagoInputSerializer(many=True)

    def validate(self, attrs):
        """
        Chequeo previo: suma de aplicaciones == monto_total.
        (El servicio también lo valida, pero aquí damos error 400 más claro.)
        """
        aplicaciones = attrs.get("aplicaciones", [])
        monto_total = attrs.get("monto_total")

        suma = sum(Decimal(str(a["monto"])) for a in aplicaciones)
        if monto_total is not None and suma != monto_total:
            raise serializers.ValidationError(
                {
                    "aplicaciones": (
                        f"La suma de aplicaciones ({suma}) no coincide con monto_total ({monto_total})."
                    )
                }
            )

        return attrs

    def create(self, validated_data):
        aplicaciones_data = validated_data.pop("aplicaciones")

        try:
            pago = registrar_pago_con_aplicaciones(
                cliente_id=validated_data["cliente_id"],
                metodo=validated_data["metodo"],
                monto_total=validated_data["monto_total"],
                referencia=validated_data.get("referencia"),
                usuario_id=validated_data["usuario_id"],
                es_deposito_inicial=validated_data.get("es_deposito_inicial", False),
                aplicaciones=aplicaciones_data,
            )
        except PaymentError as e:
            raise serializers.ValidationError({"detail": str(e)})

        return pago


## Endpoints de consulta de pagos
class PagoSerializer(serializers.ModelSerializer):
    aplicaciones = AplicacionPagoSerializer(
        many=True,
        source="aplicacionpago_set",  # o el related_name que tengas
        read_only=True,
    )

    class Meta:
        model = Pago
        fields = [
            "id",
            "fecha",
            "cliente_id",
            "metodo",
            "referencia",
            "monto_total",
            "usuario_id",
            "es_deposito_inicial",
            "aplicaciones",
        ]
