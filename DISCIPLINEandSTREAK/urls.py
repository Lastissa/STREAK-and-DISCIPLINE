from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("social/", include('social_django.urls'), name="social"),
    path('v1/', include('origin.urls'), name = 'origin'),
    path('', views.Home.as_view(), name = 'true_base_dir'),
]

handler500  = 'origin.urls.handler500'
handler404  = 'origin.urls.handler404'