"""
NAVIGATION MANUAL - the "hand-authored" half of navigation.html's "3D living manual".

This file ONLY contains human-written descriptions and groupings - it does NOT list
every individual URL by hand. The view that renders navigation.html
(origin/views/normal_view.py::NavigationGuide) walks origin.urls.urlpatterns itself
(auto-generation) and buckets every named route into whichever section below claims
it (by url_name prefix match). Anything that doesn't match a section falls into the
catch-all "Other / internal" bucket automatically - so this file can never silently
go stale and hide a page; worst case a new route just shows up undescribed under
"Other" until someone adds a proper section/prefix for it here.

TO ADD A NEW SECTION: just append a dict to SECTIONS below. `url_name_prefixes` is
checked with str.startswith() against each route's `name=`, first match wins, so put
more specific prefixes before broader ones if you ever need to.
"""

SECTIONS = [
    {
        'key': 'public',
        'title': 'Public & Marketing',
        'icon': 'fa-house',
        'description': 'The pages anyone can see before signing in - homepage, blog, leaderboard, legal.',
        'url_name_prefixes': ('origin_home', 'origin_blog', 'origin_leaderboard', 'origin_extra', 'origin_navigation', 'true_base_dir', 'llms_txt'),
    },
    {
        'key': 'auth',
        'title': 'Sign Up, Log In & Account Recovery',
        'icon': 'fa-key',
        'description': 'Everything about getting into (or back into) an account - signup, login, password reset, reactivation.',
        'url_name_prefixes': ('origin_signup', 'origin_login', 'origin_logout', 'origin_password_reset',
                               'origin_deactivated', 'origin_reactivate_account', 'origin_delete_account',
                               'origin_redirect_handler'),
    },
    {
        'key': 'onboarding',
        'title': 'Onboarding',
        'icon': 'fa-flag-checkered',
        'description': 'The first-run flow a brand new user goes through right after signup.',
        'url_name_prefixes': ('origin_onboarding',),
    },
    {
        'key': 'commitments',
        'title': 'Commitments & Check-ins',
        'icon': 'fa-fire-flame-curved',
        'description': 'The core loop of the whole product: create a commitment, check in daily, watch your streak grow.',
        'url_name_prefixes': ('origin_commitments', 'origin_each_commitment', 'origin_commitment_archive',
                               'origin_commitment_reactivate', 'origin_commitment_create_json',
                               'origin_commitment_data', 'quick_commitment_check_in', 'origin_user_HeatMap',
                               'origin_delete_all_commitments', 'origin_clear_entries', 'origin_reset_streaks'),
    },
    {
        'key': 'dashboard',
        'title': 'Dashboard',
        'icon': 'fa-gauge-high',
        'description': "The user's home base after logging in - today's check-ins, streaks at a glance, quick stats.",
        'url_name_prefixes': ('origin_dashboard',),
    },
    {
        'key': 'social',
        'title': 'Accountability Partners',
        'icon': 'fa-people-arrows',
        'description': 'Pairing up with another user for mutual accountability - find, invite, accept/decline, unpair.',
        'url_name_prefixes': ('origin_relationship', 'origin_search_friend', 'origin_add_friend', 'origin_parner_widget'),
    },
    {
        'key': 'reports',
        'title': 'Reports & Analytics',
        'icon': 'fa-chart-line',
        'description': 'Weekly truth reports and deeper analytics on consistency over time.',
        'url_name_prefixes': ('origin_reports', 'origin_weekly_analysis', 'origin_export_data'),
    },
    {
        'key': 'profile',
        'title': 'Profile & Settings',
        'icon': 'fa-user-gear',
        'description': "Account settings, tier/subscription info, theme, notification preferences, and the recently-deleted commitments recovery list.",
        'url_name_prefixes': ('origin_profile', 'origin_settings', 'origin_user_picture', 'origin_delete_user_picture'),
    },
    {
        'key': 'notifications',
        'title': 'Push Notifications',
        'icon': 'fa-bell',
        'description': 'Web push subscription endpoints used by the browser, not meant to be visited directly.',
        'url_name_prefixes': ('origin_push',),
    },
    {
        'key': 'staff',
        'title': 'Staff Hub',
        'icon': 'fa-user-shield',
        'description': 'Internal tools for staff: publishing news/blog posts, managing users, session review. Not accessible to regular users.',
        'url_name_prefixes': ('origin_staff',),
    },
    {
        'key': 'system',
        'title': 'System & Cron',
        'icon': 'fa-gears',
        'description': 'Background maintenance jobs (streak resets, check-in reminders) and internal/testing endpoints - never meant to be visited by a person.',
        'url_name_prefixes': ('origin_cron', 'origin_database', 'test_search', 'in_progess'),
    },
]

CATCH_ALL_SECTION = {
    'key': 'other',
    'title': 'Other / Internal',
    'icon': 'fa-ellipsis',
    'description': "Routes that exist but haven't been sorted into a section yet - if something you expect is here, it just needs a home in utility/navigation_manual.py.",
    'url_name_prefixes': (),
}
