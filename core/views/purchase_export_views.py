# core/views/purchase_export_views.py

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse

from core.services.purchase_export_service import PurchaseExportService


class PurchaseExportExcelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # 1. Filtrar compras
        qs = PurchaseExportService.filtrar_compras(request.query_params)

        # 2. Crear Excel
        wb = PurchaseExportService.generar_excel(qs)

        # 3. Responder archivo XLSX
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="compras_export.xlsx"'

        wb.save(response)
        return response
