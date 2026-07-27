from django.urls import path
from origin import views
from django.shortcuts import render, redirect, resolve_url
from django.contrib import messages
import logging


urlpatterns = [
    path('', views.OriginHome.as_view(),name='origin_home'),
    
    path('db_save', views.DbSave.as_view(), name = "origin_database"),
    path('redirect_url/<str:raw_url>/', views.RedirectHandler.as_view(), name='origin_redirect_handler'),
    path('in-progress/', views.InProgress.as_view(), name = 'in_progess'),
    
    path('onboarding/', views.Onboarding.as_view(),name='origin_onboarding'),
    path('dashboard/', views.Dashboard.as_view(), name = 'origin_dashboard'),
    path('dashboard/settings/', views.Dashboard.as_view(), name = 'origin_settings'),
    path('dashboard/settings/', views.Dashboard.as_view(), name = 'origin_personal_data'),
        
    path('extra/', views.Extras.as_view(),name='origin_extra'),
    path('weekly-analysis/', views.Reports.as_view(),name='origin_weekly_analysis'),
    path('login/', views.Login.as_view(),name='origin_login'),
    path('signup/', views.Signup.as_view(),name='origin_signup'),
    path('password-reset/', views.PasswordReset.as_view(),name='origin_password_reset'),
    path('password/<str:email>/<str:token>/',views.PasswordValidate.as_view(), name = 'origin_password_reset_validate' ),

    path('search_friend/', views.SearchFriend.as_view(), name = 'origin_search_friend'),
    path('add_friend/', views.AddFriend.as_view(), name = 'origin_add_friend'),
   
    path('message/', views.LogoutUI.as_view(), name = 'origin_logout'),
    
    path('debug/test-search/', views.TestSearch.as_view(), name='test_search'),
    path('debug/logout/', views.Logout.as_view(), name = 'origin_logout_active_user'),
    
    path('user_commitment_data/', views.CommitmentData.as_view(), name = "origin_commitmnet_data"),
    path('user_picture_data/', views.UserPicture.as_view(), name = "origin_user_picture"),
    path('user_partner_widget/', views.PartnerWidget.as_view(), name = "origin_parner_widget"),
    path('user_heat_map/', views.HeatMap.as_view(), name = "origin_user_HeatMap"),
    path('user_commitment_data/', views.CommitmentData.as_view(), name = "get_commitment_data"),



]




logger = logging.getLogger(__name__)
def handler500(request, *args, **kwargs):
    """Custom 500 error page."""
    messages.info(request,message='Try again in few seconds, if error persist, Please Contact Customer Suppport ')
    messages.warning(request, message=f"""If you are seeing this\nPlease copy and send this message to our customer support -
    Method: {request.method}
    status code: 500
    GET params:  {[(i, request.GET[i]) for i in request.GET]}
    POST data: {[i for i in request.POST]}
    Body: {request.body[:500]}
    User: {request.user}
    IP: {request.META.get('REMOTE_ADDR')}"""
        )
    logger.error(f"""Method: {request.method}
status code: 500
GET params: {[(i + " : " + request.GET[i], ) for i in request.GET]}
POST data: {[i for i in request.POST]}
Body: {request.body[:500]}
User: {request.user}
IP: {request.META.get('REMOTE_ADDR')}
ARGS: {args}
KWARGS: {kwargs}
""")
    return render(request, 'error/500.html')

def handler404(request, *args, **kwargs):
    """Custom 404 error page."""
    messages.info(request,message='it seem the page you are trying to access does not exist')
    logger.warning(f"""Method: {request.method}
status code: 404
GET params: {[(i + " : " + request.GET[i], ) for i in request.GET]}
POST data: {[i for i in request.POST]}
Body: {request.body[:500]}
User: {request.user}
IP: {request.META.get('REMOTE_ADDR')}
ARGS: {args}
""")
    return render(request, 'error/404.html')

def handler400(request, *args, **kwargs):
    """Custom 400 error page."""
    # messages.info(request,message='Deau user, if this page is consistent, it mean we are undergoing mantainance, bear with us please')
    logger.warning(f"""Method: {request.method}
status code: 400
GET params: {[(i + " : " + request.GET[i], ) for i in request.GET]}
POST data: {[i for i in request.POST]}
Body: {request.body[:500]}
User: {request.user}
IP: {request.META.get('REMOTE_ADDR')}
ARGS: {args}
""")
    return render(request, 'error/400.html')


#normally, it should have been to login page but if user is logged in asking them to login again is not ideal on error they know nothing about, so i assign it to onboarding as that one can tell if user is login, if not it return login straight and if user is logged in but last login is not null, it return dashboard
def csrf_failure(request, *args, **kwargs):
    return redirect('origin_onboarding')