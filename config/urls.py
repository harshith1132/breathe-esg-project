from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from ingestion.views import UploadView
from review.views import EmissionRecordViewSet, BatchListView

router = DefaultRouter()
router.register(r'records', EmissionRecordViewSet, basename='record')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/token/', obtain_auth_token),
    path('api/ingest/upload/', UploadView.as_view()),
    path('api/batches/', BatchListView.as_view()),
    path('api/', include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)