from django.urls import path
from origin import views
from django.shortcuts import render, redirect, resolve_url
from django.contrib import messages
import logging



urlpatterns = [
    path('', views.OriginHome.as_view(),name='origin_home'),
    
    #danger!!!! follow by antitiode
    path('delete_account/', views.DeleteUserEntireAccount.as_view(), name = "origin_delete_account"),
    path('reactivate_account/', views.ReactivateAccountJson.as_view(), name = "origin_reactivate_account"),   #Handles the final account reactivation
    
    
    path('db_save', views.DbSave.as_view(), name = "origin_database"),
    path('redirect_url/<str:raw_url>/', views.RedirectHandler.as_view(), name='origin_redirect_handler'),
    path('in-progress/', views.InProgress.as_view(), name = 'in_progess'),
    path('onboarding/', views.Onboarding.as_view(),name='origin_onboarding'),
    path('dashboard/<str:days_left>/<str:email>/', views.AccountDeactivated.as_view(), name = 'origin_deactivated'),

    #leaderboard ui and json
    path('leaderboard/', views.Leaderboard.as_view(), name= "origin_leaderboard"),
    path('leaderboard/get_weekly_data/', views.GetLeaderBoardData.as_view(), name= "origin_get_weekly_leaderboard_json"),
    
    #Dashboard
    path('dashboard/', views.Dashboard.as_view(), name = 'origin_dashboard'),
    path('dashboard/json/', views.DashboardJson.as_view(), name = 'origin_dashboard_json'),
    path('dashboard/settings/', views.Dashboard.as_view(), name = 'origin_settings'),
    path('dashboard/commitment/', views.DashboardCommitmentView.as_view(), name = 'origin_commitments'),
    path('dashboard/commitment/<str:commitment_key>/', views.EachCommitmentView.as_view(), name = 'origin_each_commitment_view'),
    path('dashboard/profile/', views.ProfileSettings.as_view(), name = 'origin_profile'),
    path('dashboard/relationship/', views.Relationship.as_view(), name = 'origin_relationship'),
    
    
    #public accesible
    path('blog/', views.BlogView.as_view(), name= "origin_blog"),
    path('extra/', views.Extras.as_view(),name='origin_extra'),
    path('navigation/', views.Extras.as_view(),name='origin_navigation'),
    path('weekly-analysis/', views.Reports.as_view(),name='origin_weekly_analysis'),
    path('search_friend/', views.SearchFriend.as_view(), name = 'origin_search_friend'),
    path('add_friend/', views.AddFriend.as_view(), name = 'origin_add_friend'),
    path('message/', views.LogoutUI.as_view(), name = 'origin_logout'),
    
    #auth
    path('login/', views.Login.as_view(),name='origin_login'),
    path('signup/', views.Signup.as_view(),name='origin_signup'),
    path('password-reset/', views.PasswordReset.as_view(),name='origin_password_reset'),
    path('password/<str:email>/<str:token>/',views.PasswordValidate.as_view(), name = 'origin_password_reset_validate' ),
    
    #debug
    path('debug/test-search/', views.TestSearch.as_view(), name='test_search'),
    path('debug/logout/', views.Logout.as_view(), name = 'origin_logout_active_user'),
    
    
    #json only
    path('user_commitment_data/', views.CommitmentData.as_view(), name = "origin_commitment_data"),                     # Handles dashboard.html commitment summary
    path('user_picture_data/', views.ProfilePicture.as_view(), name = "origin_user_picture"),                           # Load Picture if user have one(GLOBAL JSON)
    path('user_partner_widget/', views.PartnerWidget.as_view(), name = "origin_parner_widget"),                         # for dashboard loading partner for partner mode users
    path('user_heat_map/', views.HeatMap.as_view(), name = "origin_user_HeatMap"),                                      # Also for dashboard
    path('user_commitment_data/create_commitment/', views.CreateCommitment.as_view(), name = "origin_commitment_create_json"),     # Create another commitment for user
    path('user_commitment_data/quick_checkin/<str:commitment_key>/', views.CommitmentQuickCheckin.as_view(), name= 'quick_commitment_check_in'),    #This is for when user just want  a quick check in on their minimum day, it skips the write entrie and just log in user minimum words from their commitment
    path('relationship/sent/<str:status>/', views.RelationshipSent.as_view(), name = 'origin_relationship_sent'),         # Handles dashboard relationship friend / partner request sent
    path('relationship/received/<str:status>/', views.RelationshipReceived.as_view(), name = 'origin_relationship_received'),         # Handles dashboard relationship friend / partner request sent
    path('relationship/unpartner/', views.RelationshipUnpair.as_view(), name = 'origin_relationship_unpair'),                            #This handle user that have the accepetd in their relationship status to remove it and delete it
    path('relationship/accept_partner/', views.RelationshipAcccept.as_view(), name = 'origin_relationship_accept_partner'),           #handle updating from request receved to you are now partners                         #This handle user that have the accepetd in their relationship status to remove it and delete it
    path('relationship/decline_partner/', views.RelationshipDecline.as_view(), name = 'origin_relationship_decline_partner')           #handle updating from request receved to you are NOT partners                         #This handle user that have the accepetd in their relationship status to remove it and delete it
    # path('profile_data/', views.xxx.as_view(), name = 'origin_profile_data')                            #rent the needed json file to the profile page dashboard
    

    
    
    



]



logger = logging.getLogger(__name__)

def _error_context(request, status_code, *args, **kwargs):
    return {
        "status_code": status_code,
        "method": request.method,
        "path": request.path,
        "get_params": request.GET.dict(),
        # Never log raw POST values; they may contain passwords or tokens.
        "post_keys": list(request.POST.keys()),
        "body_preview": request.body[:500].decode(errors="replace") if request.body else "",
        "request_user": str(request.user) if hasattr(request, "user") else "anonymous",
        "client_ip": request.META.get("REMOTE_ADDR"),
        "user_agent": request.META.get("HTTP_USER_AGENT"),
        "referer": request.META.get("HTTP_REFERER"),
        "view_args": args,
        "view_kwargs": kwargs,
    }


def handler500(request, *args, **kwargs):
    """Custom 500 error page."""
    context = _error_context(request, 500, *args, **kwargs)

    messages.info(
        request,
        message="Try again in a few seconds. If the error persists, please contact customer support.",
    )
    messages.warning(
        request,
        message=(
            "If you keep seeing this, please copy and send this message to our customer support -\n"
            f"Method: {context['method']} | Path: {context['path']} | Status: 500\n"
            f"User: {context['request_user']} | IP: {context['client_ip']}"
        ),
    )

    logger.error(
        "Unhandled server error on %s %s",
        context["method"],
        context["path"],
        exc_info=True,
        extra=context,
    )

    return render(request, "error/500.html", status=500)


def handler404(request, *args, **kwargs):
    """Custom 404 error page."""
    context = _error_context(request, 404, *args, **kwargs)

    messages.info(
        request,
        message="It seems the page you are trying to access does not exist.",
    )

    logger.warning(
        "Page not found: %s %s",
        context["method"],
        context["path"],
        extra=context,
    )

    return render(request, "error/404.html", status=404)


def handler400(request, *args, **kwargs):
    """Custom 400 error page."""
    context = _error_context(request, 400, *args, **kwargs)

    messages.warning(
        request,
        message="Sorry, that request could not be processed. If this keeps happening, please contact support.",
    )

    logger.warning(
        "Bad request (400) on %s %s",
        context["method"],
        context["path"],
        exc_info=True,
        extra=context,
    )

    return render(request, "error/400.html", status=400)



def csrf_failure(request, *args, **kwargs):
    messages.error(request, message="THIS DOMAIN IS NOT OUR OFFICIAL DOMAIN, PLEASE REPORT TO CUSTOMER CARE ALONGSIDE THE URL SO WE CAN KEEP OUR SITE CLEAN")
    return redirect('origin_onboarding')