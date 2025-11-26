from django.urls import path, include
from rest_framework.routers import DefaultRouter

from core.views.auth_views import CambiarPasswordView, LoginView
from core.views.health import ping


from core.views.order_views import (
    PedidoCreateView,
    PedidoDetailView,
    PedidoItemsReplaceView,
    PedidoConfirmarView,
    PedidoCancelarView,
    SoloVentasDemo,  ## este de prueba
)

from core.views.catalog_views import (
    ClienteListView,
    ClienteDetailView,
    BodegaListView,
    BodegaDetailView,
    ProductoListView,
    ProductoDetailView,
)

## Provider
from core.views.provider_views import (
    ProveedorListCreateAPIView,
    ProveedorDetailAPIView,
)

## pagos
from core.views.payment_views import PagoCreateAPIView
from core.views.payment_query_views import (
    PagosPorClienteListAPIView,
    PagosPorVentaListAPIView,
    EstadoCuentaClienteAPIView,
    CarteraDashboardAPIView,  # 👈 nuevo
)

## PurchaseView= vistas de compras
"""Dashboard de Compras"""
from core.views.purchase_dashboard_views import PurchaseDashboardAPIView
from core.views.purchase_views import PurchaseViewSet, PurchasesBySupplierListView
from core.views.purchase_export_views import PurchaseExportExcelAPIView

router = DefaultRouter()
# ... otros registros
router.register(r"compras", PurchaseViewSet, basename="compras")


urlpatterns = [
    # 👇 1) Rutas especiales de compras
    path(
        "compras/dashboard/",
        PurchaseDashboardAPIView.as_view(),
        name="compras-dashboard",
    ),
    path(
        "compras/exportar/",
        PurchaseExportExcelAPIView.as_view(),
        name="compras-exportar",
    ),
    # 👇 2) Rutas del router (compras/, compras/<id>/, etc.)
    path("", include(router.urls)),
    # 👇 3) Resto de rutas que ya tenías
    path("ping", ping),
    path("auth/login", LoginView.as_view()),
    path("auth/cambiar-password", CambiarPasswordView.as_view()),
    path("demo/solo-ventas", SoloVentasDemo.as_view()),
    # PEDIDOS
    path("pedidos/", PedidoCreateView.as_view()),
    path("pedidos/<int:pedido_id>/", PedidoDetailView.as_view()),
    path("pedidos/<int:pedido_id>/items/", PedidoItemsReplaceView.as_view()),
    path("pedidos/<int:pedido_id>/confirmar/", PedidoConfirmarView.as_view()),
    path("pedidos/<int:pedido_id>/cancelar/", PedidoCancelarView.as_view()),
    # CATÁLOGOS CLIENTES
    path("catalogos/clientes/", ClienteListView.as_view()),
    path("catalogos/clientes/<int:pk>/", ClienteDetailView.as_view()),
    # CATÁLOGOS BODEGA
    path("catalogos/bodegas/", BodegaListView.as_view()),
    path("catalogos/bodegas/<int:pk>/", BodegaDetailView.as_view()),
    # CATÁLOGOS PRODUCTO
    path("catalogos/productos/", ProductoListView.as_view()),
    path("catalogos/productos/<int:pk>/", ProductoDetailView.as_view()),
    # PAGOS
    path("pagos/", PagoCreateAPIView.as_view(), name="pago-create"),
    path(
        "clientes/<int:cliente_id>/pagos/",
        PagosPorClienteListAPIView.as_view(),
        name="pagos-por-cliente",
    ),
    path(
        "ventas/<int:venta_id>/pagos/",
        PagosPorVentaListAPIView.as_view(),
        name="pagos-por-venta",
    ),
    path(
        "clientes/<int:cliente_id>/estado-cuenta/",
        EstadoCuentaClienteAPIView.as_view(),
        name="estado-cuenta-cliente",
    ),
    # DASHBOARD CARTERA
    path(
        "cartera/dashboard/",
        CarteraDashboardAPIView.as_view(),
        name="cartera-dashboard",
    ),
    # COMPRAS POR PROVEEDOR
    path(
        "proveedores/<int:proveedor_id>/compras/",
        PurchasesBySupplierListView.as_view(),
    ),
    # CATÁLOGOS PROVEEDORES
    path("catalogos/proveedores/", ProveedorListCreateAPIView.as_view()),
    path("catalogos/proveedores/<int:pk>/", ProveedorDetailAPIView.as_view()),
]
