from django.urls import path
from origin import views

urlpatterns = [
    path('', views.OriginHome.as_view(),name='origin_home'),
    path('onboarding/', views.OriginHome.as_view(),name='origin_onboarding'),

]