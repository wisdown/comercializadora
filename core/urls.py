from django.urls import path
from core.views.auth_views import CambiarPasswordView
from core.views.order_views import SoloVentasDemo
from core.views.order_views import PedidoCreateView
from core.views.health import ping

urlpatterns = [
    path("ping", ping),  # GET /api/v1/ping → {"status":"ok"}
    path("auth/cambiar-password", CambiarPasswordView.as_view()),
    path("demo/solo-ventas", SoloVentasDemo.as_view()),
    path("pedidos", PedidoCreateView.as_view()),
]
