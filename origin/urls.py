from django.urls import path
from origin import views
from django.shortcuts import render
from django.contrib import messages
import logging

urlpatterns = [
    
    path('', views.OriginHome.as_view(),name='origin_home'),
    path('extra/', views.Extras.as_view(),name='origin_extra'),
    path('login/', views.Login.as_view(),name='origin_login'),
    path('weekly-analysis/', views.Reports.as_view(),name='origin_weekly_analysis'),
    path('signup/', views.Signup.as_view(),name='origin_signup'),
    path('password-reset/', views.OriginHome.as_view(),name='origin_password_reset'),
    path('onboarding/', views.OriginHome.as_view(),name='origin_onboarding'),
    path('dashboard/', views.OriginHome.as_view(), name = 'origin_dashboard_anonymous'),
    path('dashboard/<str:username>/', views.OriginHome.as_view(), name = 'origin_dashboard'),
    path('dashboard/<str:username>/', views.OriginHome.as_view(), name = 'origin_settings'),
    
]




logger = logging.getLogger(__name__)
def handler500(request, *args, **kwargs):
    """Custom 500 error page."""
    messages.info(request,message='Try again in few seconds, if error persist, Please Contact Customer Suppport ')
    messages.warning(request, message=f"If you are seeing this\nPlease copy and send this message to our customer support -{request}")
    logger.error(f"here is a complete issue of request, can be messy though -ope : {request}")
    return render(request, 'error/500.html')

def handler404(request, *args, **kwargs):
    """Custom 404 error page."""
    messages.info(request,message='it seem the page you are trying to access does not exist')
    logger.error(f"here is a complete issue of request, can be messy though -ope : {request}")
    return render(request, 'error/404.html')
