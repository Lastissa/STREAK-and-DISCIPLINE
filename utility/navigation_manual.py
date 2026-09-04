"""
SITE GUIDE - the content behind the in-app "Site Guide" page (navigation.html).

This is a hand-curated list written for END USERS, not a developer-facing map of
every route in the app. Each entry below becomes one card with a short, plain-
language description and one or more real buttons the person can click to go
there. There is deliberately NO auto-discovery of origin.urls.urlpatterns here
(there used to be) - that approach meant every route in the entire app, including
staff tools, cron endpoints, debug routes, and the "delete my account" danger-zone
endpoint, got listed with its literal URL on a page any visitor could open. This
file is the opposite: only pages a regular user should be pointed toward, described
by what they do, with a real link - never a raw path string.

TO ADD A CARD: append a dict to GUIDE below.
  - 'key'         : short unique id (used for anchors/highlighting)
  - 'title'       : plain-language name shown as the card heading
  - 'icon'        : Font Awesome class (no "fas", just the icon name, e.g. 'fa-house')
  - 'description' : one or two plain sentences - what this is for, not how it's built
  - 'links'       : list of {'label': <button text>, 'url_name': <name= from urls.py>}
                     Every url_name MUST resolve with no required arguments (this
                     page never shows routes that need a dynamic id/key, since there's
                     nothing sensible to link a generic guide button to).

Staff-only cards additionally set 'staff_only': True and are simply left out of the
context entirely for non-staff visitors (see NavigationGuide in
origin/views/normal_view.py) - so even the description/title of a staff card is
never sent to a regular user's browser, not just hidden with CSS.
"""

GUIDE = [
    {
        'key': 'get-started',
        'title': 'Getting Started',
        'icon': 'fa-door-open',
        'description': 'New here? Create a free account or sign back in to pick up where you left off.',
        'links': [
            {'label': 'Sign Up', 'url_name': 'origin_signup'},
            {'label': 'Log In', 'url_name': 'origin_login'},
            {'label': 'Forgot Password', 'url_name': 'origin_password_reset'},
        ],
    },
    {
        'key': 'dashboard',
        'title': 'Your Dashboard',
        'icon': 'fa-gauge-high',
        'description': "Your home base after logging in - today's check-ins and streaks at a glance.",
        'links': [
            {'label': 'Go to Dashboard', 'url_name': 'origin_dashboard'},
        ],
    },
    {
        'key': 'commitments',
        'title': 'Commitments & Check-ins',
        'icon': 'fa-fire-flame-curved',
        'description': 'Create a commitment, check in daily, and watch your streak grow. This is the core of the app.',
        'links': [
            {'label': 'View My Commitments', 'url_name': 'origin_commitments'},
        ],
    },
    {
        'key': 'reports',
        'title': 'Reports & Weekly Analysis',
        'icon': 'fa-chart-line',
        'description': 'An honest weekly breakdown of your consistency, plus deeper analytics over time.',
        'links': [
            {'label': 'My Reports', 'url_name': 'origin_reports'},
            {'label': 'Weekly Analysis', 'url_name': 'origin_weekly_analysis'},
        ],
    },
    {
        'key': 'social',
        'title': 'Partners & Leaderboard',
        'icon': 'fa-people-arrows',
        'description': 'Pair up with an accountability partner, or opt into the public leaderboard for a bit of friendly competition.',
        'links': [
            {'label': 'Accountability Partners', 'url_name': 'origin_relationship'},
            {'label': 'Leaderboard', 'url_name': 'origin_leaderboard'},
        ],
    },
    {
        'key': 'profile',
        'title': 'Profile & Settings',
        'icon': 'fa-user-gear',
        'description': 'Manage your username, picture, theme, notification preferences, and account.',
        'links': [
            {'label': 'Profile & Settings', 'url_name': 'origin_profile'},
        ],
    },
    {
        'key': 'blog',
        'title': 'Blog & Updates',
        'icon': 'fa-newspaper',
        'description': 'Product updates, discipline tips, and stories from other users building their streak.',
        'links': [
            {'label': 'Read the Blog', 'url_name': 'origin_blog'},
        ],
    },
    {
        'key': 'help',
        'title': 'Help, Privacy & Terms',
        'icon': 'fa-circle-question',
        'description': 'Support, frequently asked questions, and our privacy policy & terms of service.',
        'links': [
            {'label': 'Help & Legal', 'url_name': 'origin_extra'},
        ],
    },
    {
        'key': 'staff',
        'title': 'Staff Hub',
        'icon': 'fa-user-shield',
        'description': 'Internal tools for managing users and publishing site content.',
        'links': [
            {'label': 'Open Staff Hub', 'url_name': 'origin_staff_home'},
        ],
        'staff_only': True,
    },
]
