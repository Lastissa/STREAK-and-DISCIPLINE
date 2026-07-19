from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', views.Home.as_view(), name = 'true_base_dir'),
    
    path('v1/', include('origin.urls'))
]

