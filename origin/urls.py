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
    path('dashboard/account_inactive/<str:days_left>/<str:email>/', views.AccountDeactivated.as_view(), name = 'origin_deactivated'),

    #leaderboard ui and json
    path('leaderboard/', views.Leaderboard.as_view(), name= "origin_leaderboard"),
    path('leaderboard/get_weekly_data/', views.GetLeaderBoardData.as_view(), name= "origin_get_weekly_leaderboard_json"),
    
    #Dashboard
    path('dashboard/', views.Dashboard.as_view(), name = 'origin_dashboard'),
    path('dashboard/json/', views.DashboardJson.as_view(), name = 'origin_dashboard_json'),
    path('dashboard/settings/', views.Dashboard.as_view(), name = 'origin_settings'),
    path('dashboard/commitment/', views.DashboardCommitmentView.as_view(), name = 'origin_commitments'),
    path('dashboard/commitment/<str:commitment_key>/', views.EachCommitmentView.as_view(), name = 'origin_each_commitment_view'),
    path('dashboard/commitment/<str:commitment_key>/settings/', views.EachCommitmentViewSettings.as_view(), name = 'origin_each_commitment_view_settings'),
    path('dashboard/commitment/<str:commitment_key>/needed_data/', views.EachCommitementHeatMap.as_view(), name = 'origin_each_commitment_entries_needed_data'),
    path('dashboard/commitment/<str:commitment_key>/save_entry/', views.EachCommitementEntries.as_view(), name = 'origin_each_commitment_entries_save_entry'),
    path('dashboard/commitment/<str:id>/archive/', views.EachCommitmentArchive.as_view(), name = 'origin_commitment_archive'), #DELETE (soft) a commitment - kept the "archive" url name so we don't break any existing bookmarks/JS calling it, but the behaviour + button label are "Delete" now (see EachCommitmentArchive docstring)
    path('dashboard/commitment/<str:id>/reactivate/', views.ReactivateCommitment.as_view(), name = 'origin_commitment_reactivate'), #undo a Delete within its 24h recovery window - used on the profile page
    path('dashboard/profile/', views.ProfileSettings.as_view(), name = 'origin_profile'),
    path('dashboard/relationship/', views.Relationship.as_view(), name = 'origin_relationship'),
    path('dashboard/relationship/partner/<str:userid>/', views.PartnerAcceptedDashboard.as_view(), name = 'origin_relationship_partner'),
    path('dashboard/reports/', views.DashbaordAnalytics.as_view(), name = 'origin_reports'),
    
    
    #public accesible
    path('blog/', views.BlogView.as_view(), name= "origin_blog"),
    path('blog/story/create/', views.CreateUserStory.as_view(), name= "origin_create_user_story"), #public "share your story" form -> always tag='story', gold-only banner enforced server-side (see CreateUserStory docstring)
    path('blog/<int:pk>/', views.BlogViewExpanded.as_view(), name= "origin_blog_detail"),
    path('extra/', views.Extras.as_view(),name='origin_extra'),
    path('navigation/', views.NavigationGuide.as_view(),name='origin_navigation'),
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
    path('user_profile_picture_delete/', views.ProfilePictureRemove.as_view(), name = 'origin_delete_user_picture'),
    path('user_partner_widget/', views.PartnerWidget.as_view(), name = "origin_parner_widget"),                         # for dashboard loading partner for partner mode users
    path('user_heat_map/', views.HeatMap.as_view(), name = "origin_user_HeatMap"),                                      # Also for dashboard
    path('user_commitment_data/create_commitment/', views.CreateCommitment.as_view(), name = "origin_commitment_create_json"),     # Create another commitment for user
    path('user_commitment_data/quick_checkin/<str:commitment_key>/', views.CommitmentQuickCheckin.as_view(), name= 'quick_commitment_check_in'),    #This is for when user just want  a quick check in on their minimum day, it skips the write entrie and just log in user minimum words from their commitment
    path('relationship/sent/<str:status>/', views.RelationshipSent.as_view(), name = 'origin_relationship_sent'),         # Handles dashboard relationship friend / partner request sent
    path('relationship/received/<str:status>/', views.RelationshipReceived.as_view(), name = 'origin_relationship_received'),         # Handles dashboard relationship friend / partner request sent
    path('relationship/unpartner/', views.RelationshipUnpair.as_view(), name = 'origin_relationship_unpair'),                            #This handle user that have the accepetd in their relationship status to remove it and delete it
    path('relationship/accept_partner/', views.RelationshipAcccept.as_view(), name = 'origin_relationship_accept_partner'),           #handle updating from request receved to you are now partners
    path('relationship/decline_partner/', views.RelationshipDecline.as_view(), name = 'origin_relationship_decline_partner'),           #handle updating from request receved to you are NOT partners
    path('profile_data/update_username/', views.ProfileUpdateUsernameORUserid.as_view(), name = 'origin_profile_update_first_part'),     #return the needed json file to the profile page dashboardpage uspdate username, userid 
    path('profile_data/update_profile/', views.ProfileUpdateToggles.as_view(), name = 'origin_profile_update_second_part'),     #return the needed json file to the profile page dashboardpage leaderboard optn in, show zeal score etc
    path('profile_data/update_theme/', views.ProfileUpdateTheme.as_view(), name = 'origin_profile_update_theme'),     #return the needed json file to the profile page dashboardpage uspdate username, userid 
    path('profile_export_data/', views.DataExport.as_view(), name = 'origin_export_data'),
    path('delete_all_commitments/', views.BulkDeleteCommitments.as_view(), name = 'origin_delete_all_commitments'),
    path('clear_entries/', views.ClearAllEntries.as_view(), name = 'origin_clear_entries'),
    path('reset_streaks/', views.ResetAllStreaks.as_view(), name = 'origin_reset_streaks'),
    path('reports_data/', views.ReportsData.as_view(), name = 'origin_reports_data'),     #return the needed json for the user reports page, this is the one that will be used to load the report data in the reports page

    path('staff/signup/', views.StaffSignup.as_view(), name ="origin_staff_signup"),
    path('staff/get_token/', views.StaffMakeTokenRequest.as_view(), name ="origin_get_staff_token"),
    path('staff/verify_token/', views.VerifyStaffTokenAndCreateAccount.as_view(), name ="origin_verify_staff_token"),
    path('staff/get_token/', views.StaffMakeTokenRequest.as_view(), name ="origin_get_staff_token"),
    path('staff/home/', views.AccountWithStaffStatus.as_view(), name ="origin_staff_home"),
    path('staff/create_blog/', views.CreateBlog.as_view(), name ="origin_staff_publish_news"),
    path('staff/news/<int:pk>/edit/', views.EditBlog.as_view(), name ="origin_staff_edit_news"),
    path('staff/news/<int:pk>/banner/', views.ChangeBlogBanner.as_view(), name ="origin_staff_change_news_banner"),
    path('staff/news/<int:pk>/delete/', views.DeleteBlog.as_view(), name ="origin_staff_delete_news"),
    path('staff/users/', views.StaffUsersPage.as_view(), name ="origin_staff_users"),
    path('staff/users/search/', views.StaffUserSearch.as_view(), name ="origin_staff_users_search"),
    path('staff/users/<int:user_id>/manage/', views.StaffUserManage.as_view(), name ="origin_staff_users_manage"),
    path('staff/sessions/', views.StaffActiveSessions.as_view(), name ="origin_staff_sessions"),
    
    
    # Cron job THAT I RUN MANUALLy WITH HTTP USING CRONJOB.ORG AND UPTIMEROBOT
    path('push/vapid_public_key/', views.GetVapidPublicKey.as_view(), name = 'origin_push_vapid_public_key'),
    path('push/subscribe/', views.SavePushSubscription.as_view(), name = 'origin_push_subscribe'),
    path('push/unsubscribe/', views.RemovePushSubscription.as_view(), name = 'origin_push_unsubscribe'),
    path('cron/send-checkin-reminders/<str:secret>/', views.CreateHitCheckinReminders.as_view(), name = 'origin_cron_checkin_reminders'),

]






logger = logging.getLogger(__name__)

def _error_context(request, status_code, *args, **kwargs):
    return {
        "status_code": status_code,
        "method": request.method,
        "path": request.path,
        # "get_params": request.GET.dict(),
        # "post_keys": list(request.POST.keys()),
        # "body_preview": request.body[:500].decode(errors="replace") if request.body else "",
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
    """Custom 404 page (error/404.html) - a genuine dead-end/mistyped-url page. This is
    DELIBERATELY DIFFERENT from reusables/still_in_progress.html (used by the explicit
    /in-progress/ route for features that exist as a link but aren't built yet): a 404
    means "this never existed / was moved", so it only offers one way out (back to the
    landing page), while the in-progress screen is upbeat and offers a few things to do
    while the user waits. Previously both cases rendered the SAME template, which made
    real 404s look identical to "coming soon" pages - that's now fixed."""
    context = _error_context(request, 404, *args, **kwargs)

    logger.warning(
        "Page not found (404): %s %s",
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
    messages.error(request, message="THIS DOMAIN MIGHT NOT BE OUR OFFICIAL DOMAIN, PLEASE REPORT TO CUSTOMER CARE ALONGSIDE THE URL SO WE CAN KEEP OUR SITE CLEAN OR CONFIRM IF IT WAS A GLITCH")
    return redirect('origin_onboarding')