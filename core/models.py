from django.db import models
from django.utils import timezone


# Create your models here.
class Pago(models.Model):
    id = models.AutoField(primary_key=True)  # ⬅️ IMPORTANTE: AutoField
    fecha = models.DateTimeField(default=timezone.now)  # o auto_now_add=True
    cliente = models.ForeignKey("Cliente", models.DO_NOTHING, db_column="cliente_id")
    metodo = models.CharField(max_length=20)  # enum en BD, char aquí
    referencia = models.CharField(max_length=120, blank=True, null=True)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    usuario = models.ForeignKey("Usuario", models.DO_NOTHING, db_column="usuario_id")
    es_deposito_inicial = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "pago"


class AplicacionPago(models.Model):
    id = models.BigAutoField(primary_key=True)
    pago = models.ForeignKey(Pago, models.DO_NOTHING, db_column="pago_id")
    cuota = models.ForeignKey(
        "Cuota", models.DO_NOTHING, db_column="cuota_id", blank=True, null=True
    )
    venta = models.ForeignKey(
        "Venta", models.DO_NOTHING, db_column="venta_id", blank=True, null=True
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    tipo = models.CharField(max_length=8)

    class Meta:
        managed = False
        db_table = "aplicacionpago"


class Venta(models.Model):
    fecha = models.DateTimeField()
    cliente = models.ForeignKey("Cliente", models.DO_NOTHING)
    usuario = models.ForeignKey("Usuario", models.DO_NOTHING)
    bodega = models.ForeignKey("Bodega", models.DO_NOTHING)
    tipo_pago = models.CharField(max_length=7)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=7)
    pedido = models.ForeignKey("Pedido", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "venta"


class Ventadetalle(models.Model):
    venta = models.ForeignKey(Venta, models.DO_NOTHING)
    producto = models.ForeignKey("Producto", models.DO_NOTHING)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    precio_unit = models.DecimalField(max_digits=12, decimal_places=2)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = "ventadetalle"


class Acuerdopago(models.Model):
    venta = models.ForeignKey(Venta, models.DO_NOTHING)
    tipo = models.CharField(max_length=10)
    capital = models.DecimalField(max_digits=12, decimal_places=2)
    interes_anual = models.DecimalField(max_digits=6, decimal_places=3)
    cuotas = models.IntegerField()
    periodicidad = models.CharField(max_length=9)
    fecha_inicio = models.DateField()
    mora_diaria = models.DecimalField(max_digits=6, decimal_places=4)
    estado = models.CharField(max_length=7)

    class Meta:
        managed = False
        db_table = "acuerdopago"


class Cuota(models.Model):
    id = models.BigAutoField(primary_key=True)
    acuerdo = models.ForeignKey(Acuerdopago, models.DO_NOTHING)
    no_cuota = models.IntegerField()
    fecha_venc = models.DateField()
    capital_prog = models.DecimalField(max_digits=12, decimal_places=2)
    interes_prog = models.DecimalField(max_digits=12, decimal_places=2)
    total_prog = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_cuota = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=12)

    class Meta:
        managed = False
        db_table = "cuota"
        unique_together = (("acuerdo", "no_cuota"),)


class MovimientoCaja(models.Model):
    id = models.BigAutoField(primary_key=True)
    caja = models.ForeignKey("Caja", models.DO_NOTHING, db_column="caja_id")
    fecha = models.DateTimeField(default=timezone.now)
    tipo = models.CharField(max_length=7)  # INGRESO/EGRESO
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.CharField(max_length=200, blank=True, null=True)
    referencia = models.CharField(max_length=120, blank=True, null=True)
    pago = models.ForeignKey(
        Pago, models.DO_NOTHING, db_column="pago_id", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "movimientocaja"


class Caja(models.Model):
    nombre = models.CharField(unique=True, max_length=80)
    moneda = models.CharField(max_length=10)
    activo = models.IntegerField()

    class Meta:
        managed = False
        db_table = "caja"


class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    dpi = models.CharField(max_length=30, blank=True, null=True)
    nit = models.CharField(unique=True, max_length=30, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=120, blank=True, null=True)
    estado = models.CharField(max_length=8)

    class Meta:
        managed = False
        db_table = "cliente"


class Usuario(models.Model):
    username = models.CharField(unique=True, max_length=60)
    nombre = models.CharField(max_length=120)
    email = models.CharField(max_length=120, blank=True, null=True)
    password_hash = models.CharField(max_length=255)
    activo = models.IntegerField()

    class Meta:
        managed = False
        db_table = "usuario"


class Bodega(models.Model):
    nombre = models.CharField(unique=True, max_length=120)
    ubicacion = models.CharField(max_length=200, blank=True, null=True)
    activo = models.IntegerField()

    class Meta:
        managed = False
        db_table = "bodega"


class Marca(models.Model):
    nombre = models.CharField(unique=True, max_length=100)
    activo = models.IntegerField()

    class Meta:
        managed = False
        db_table = "marca"


class Categoria(models.Model):
    nombre = models.CharField(unique=True, max_length=100)
    requiere_serie = models.IntegerField()
    activo = models.IntegerField()

    class Meta:
        managed = False
        db_table = "categoria"


class Impuesto(models.Model):
    nombre = models.CharField(unique=True, max_length=80)
    tasa = models.DecimalField(max_digits=6, decimal_places=4)

    class Meta:
        managed = False
        db_table = "impuesto"


class Producto(models.Model):
    sku = models.CharField(unique=True, max_length=60)
    nombre = models.CharField(max_length=150)
    marca = models.ForeignKey(Marca, models.DO_NOTHING, blank=True, null=True)
    categoria = models.ForeignKey(Categoria, models.DO_NOTHING, blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    requiere_serie = models.IntegerField()
    atributos_json = models.JSONField(blank=True, null=True)
    costo_ref = models.DecimalField(max_digits=12, decimal_places=2)
    precio_base = models.DecimalField(max_digits=12, decimal_places=2)
    impuesto = models.ForeignKey(Impuesto, models.DO_NOTHING, blank=True, null=True)
    activo = models.IntegerField()

    class Meta:
        managed = False
        db_table = "producto"


class Pedido(models.Model):
    fecha = models.DateTimeField()
    total = models.DecimalField(max_digits=12, decimal_places=2)
    cliente = models.ForeignKey(Cliente, models.DO_NOTHING)
    usuario = models.ForeignKey("Usuario", models.DO_NOTHING)
    bodega = models.ForeignKey(Bodega, models.DO_NOTHING)
    estado = models.CharField(max_length=9)
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    creado_por = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "pedido"


class Pedidodetalle(models.Model):
    pedido = models.ForeignKey(Pedido, models.DO_NOTHING)
    producto = models.ForeignKey("Producto", models.DO_NOTHING)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = "pedidodetalle"


## Vista cartera
class VCarteraAging(models.Model):
    # OJO: usamos cuota_id como PK lógico para que Django no invente un id
    cuota_id = models.BigIntegerField(primary_key=True, db_column="cuota_id")
    cliente_id = models.IntegerField()
    cliente = models.CharField(max_length=150)
    fecha_venc = models.DateField()
    dias_vencidos = models.IntegerField()
    saldo = models.DecimalField(max_digits=12, decimal_places=2)
    bucket = models.CharField(
        max_length=10
    )  # '0-AL-DIA', '1-30', '31-60', '61-90', '>90'

    class Meta:
        managed = False
        db_table = "v_cartera_aging"
        verbose_name = "Cartera Aging"
        verbose_name_plural = "Cartera Aging"


## fase 4 modelos de compras
class Proveedor(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    nit = models.CharField(max_length=30, blank=True, null=True)
    cui = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    email = models.CharField(max_length=120, blank=True, null=True)
    estado = models.CharField(max_length=8)  # 'ACTIVO' / 'INACTIVO'

    class Meta:
        managed = False
        db_table = "proveedor"
        unique_together = (("nit",), ("cui",))

    def __str__(self):
        return self.nombre


class Compra(models.Model):
    id = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey("Proveedor", models.DO_NOTHING)
    bodega = models.ForeignKey("Bodega", models.DO_NOTHING)
    fecha = models.DateTimeField()
    no_documento = models.CharField(max_length=60)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    usuario = models.ForeignKey("Usuario", models.DO_NOTHING)
    estado = models.CharField(max_length=10)  # REGISTRADA / ANULADA / CERRADA
    observaciones = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "compra"
        unique_together = (("proveedor", "no_documento"),)

    def __str__(self):
        return f"Compra #{self.id} - {self.no_documento}"


class CompraDetalle(models.Model):
    id = models.BigAutoField(primary_key=True)
    compra = models.ForeignKey("Compra", models.DO_NOTHING, related_name="detalles")
    producto = models.ForeignKey("Producto", models.DO_NOTHING)
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    costo_unit = models.DecimalField(max_digits=12, decimal_places=4)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        managed = False
        db_table = "compra_detalle"


class MovimientoInventario(models.Model):
    id = models.BigAutoField(primary_key=True)
    fecha = models.DateTimeField()
    tipo = models.CharField(max_length=8)  # COMPRA / AJUSTE / VENTA / TRASLADO
    bodega_origen = models.ForeignKey(
        "Bodega",
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="movimientos_salida",
    )
    bodega_destino = models.ForeignKey(
        "Bodega",
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="movimientos_entrada",
    )
    producto = models.ForeignKey("Producto", models.DO_NOTHING)
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    costo_unit = models.DecimalField(max_digits=12, decimal_places=4)
    referencia = models.CharField(max_length=120, blank=True, null=True)
    usuario = models.ForeignKey("Usuario", models.DO_NOTHING, blank=True, null=True)
    compra = models.ForeignKey("Compra", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "movimientoinventario"


class Existencia(models.Model):
    # Para Django necesitamos un primary_key: usamos producto como PK lógico
    producto = models.ForeignKey(
        "Producto",
        models.DO_NOTHING,
        db_column="producto_id",
        primary_key=True,
    )
    bodega = models.ForeignKey(
        "Bodega",
        models.DO_NOTHING,
        db_column="bodega_id",
    )
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    reservado = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = "existencia"
        unique_together = (("producto", "bodega"),)

    def __str__(self):
        return f"{self.producto_id} @ {self.bodega_id} = {self.cantidad}"
