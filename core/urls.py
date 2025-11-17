from django.urls import path
from core.views.auth_views import CambiarPasswordView
from core.views.auth_views import LoginView
from core.views.health import ping

from core.views.order_views import (
    PedidoCreateView,
    PedidoDetailView,
    PedidoItemsReplaceView,
    PedidoConfirmarView,
    PedidoCancelarView,
    SoloVentasDemo,  ## este de prueba
    PedidoCreateView,  ## este de prueba
)


urlpatterns = [
    path("ping", ping),  # GET /api/v1/ping → {"status":"ok"}
    path("auth/login", LoginView.as_view()),
    path("auth/cambiar-password", CambiarPasswordView.as_view()),
    path("demo/solo-ventas", SoloVentasDemo.as_view()),
    # PEDIDOS
    path("pedidos/", PedidoCreateView.as_view()),  # POST
    path("pedidos/<int:pedido_id>/", PedidoDetailView.as_view()),  # GET
    path("pedidos/<int:pedido_id>/items/", PedidoItemsReplaceView.as_view()),  # PUT
    path("pedidos/<int:pedido_id>/confirmar/", PedidoConfirmarView.as_view()),  # POST
    path("pedidos/<int:pedido_id>/cancelar/", PedidoCancelarView.as_view()),  # POST
]
