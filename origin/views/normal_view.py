"""VIEW THAT RETURN USER INTERFACE"""

from django.shortcuts import render, redirect, reverse
from django.http import JsonResponse, Http404
from django.views import View
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.core.cache import cache
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models, transaction
from django.core.validators import EmailValidator
from origin.models import Profile,Commitment, Entries, Friendship, ChoicesValidatorInModels
from ..models import News

import json
from utility.config import *
from utility.email_sending import send_password_reset_email, send_password_reset_successful_email

from .utility_view import helper_with_friendship_request_answer

import logging
from datetime import timedelta
from django.utils import timezone
logger = logging.getLogger(__name__)


class OriginHome(View):
    def get(self, request):
        if (send_user_to_dashboard := try_send_user_to_dashboard(request)) is not None: return send_user_to_dashboard
        messages.info(request, message=intro_word()[0])
        # messages.info(request, message= intro_word()[1])
        return render(request, 'html/landing_page.html', {
            'consistency' : get_consistency_Value(),
            'journal_created': get_journal_created_value(),
            'year': get_copyright_year()
        })

def try_send_user_to_dashboard(request: object):
    """Collect the same request every method collects in django view And try to redirect the useer to the dashboard if they are logged in, i did this to avoid code repetition"""
    if request.user.is_authenticated:   return redirect('origin_onboarding')

    
class Extras(View):
    """for privacy policy, term of use etc"""
    def get(self, request): return render(request, 'html/privacy_etc.html')


class NavigationGuide(View):
    """The "3D living manual" for the whole project (navigation.html) - a page that maps
    every named route in the app.

    It's a MIX of auto-generation and hand-authored content, exactly as requested:
      - AUTO: this view walks origin.urls.urlpatterns itself at request time (see
        _discover_routes below) and pulls out every route's url `name=` and raw path
        pattern - so a newly added `path(..., name='...')` shows up here automatically,
        nothing to remember to update.
      - HAND-AUTHORED: utility/navigation_manual.py -> SECTIONS groups those raw routes
        into human-friendly sections with a title/icon/description written by a person.
        Editing that file is how you (re)organise or redescribe things; you never have
        to touch this view or duplicate the URL list anywhere.

    The template renders this as a 3D card layout (CSS perspective/transform, no
    WebGL dependency) with a toggle to load a heavier "advanced" stylesheet on
    demand - see navigation.html for that toggle and static/css/navigation_advanced.css.
    """

    def _discover_routes(self):
        """Walk origin.urls.urlpatterns and return {url_name: raw_pattern_string} for
        every named route. Read-only introspection - never touches the DB, never
        instantiates a view, so it's cheap and safe to run on every request."""
        from origin import urls as origin_urls

        discovered = {}
        for entry in origin_urls.urlpatterns:
            name = getattr(entry, 'name', None)
            pattern = getattr(entry, 'pattern', None)
            if not name or pattern is None:
                continue
            discovered[name] = '/v1/' + str(pattern)
        return discovered

    def get(self, request):
        from utility.navigation_manual import SECTIONS as NAVIGATION_SECTIONS, CATCH_ALL_SECTION as NAVIGATION_CATCH_ALL

        routes = self._discover_routes()
        assigned_names = set()

        sections = []
        for section in NAVIGATION_SECTIONS:
            matched = []
            for name, path in routes.items():
                if name in assigned_names:
                    continue
                if name.startswith(section['url_name_prefixes']):
                    matched.append({'name': name, 'path': path})
                    assigned_names.add(name)
            matched.sort(key=lambda r: r['name'])
            sections.append({**section, 'routes': matched, 'route_count': len(matched)})

        leftover = [{'name': n, 'path': p} for n, p in routes.items() if n not in assigned_names]
        leftover.sort(key=lambda r: r['name'])
        if leftover:
            sections.append({**NAVIGATION_CATCH_ALL, 'routes': leftover, 'route_count': len(leftover)})

        #the "advanced 3D view" toggle (heavier CSS: ambient rotation, deeper shadows,
        #floating-particle backdrop) is opt-in and remembered via a plain cookie set by
        #static/js/navigation.js when the button is clicked. Reading it here (rather than
        #only in JS) means the extra <link> tag is only ever emitted server-side when the
        #user actually asked for it - no flash of unstyled/understyled content on refresh.
        advanced_requested = request.COOKIES.get('sd-nav-advanced') == '1'

        return render(request, 'html/navigation.html', {
            'nav_sections': sections,
            'total_routes': len(routes),
            'advanced_requested': advanced_requested,
        })

class Signup(View):
    """signup page"""
    def get(self, request): 
        if (send_user_to_dashboard := try_send_user_to_dashboard(request)) is not None: return send_user_to_dashboard
        messages.info(request=request, message="Please, Read term and services before you continue")
        return render(request, 'html/signup.html', {'url_for_form' : reverse('origin_redirect_handler', kwargs={'raw_url' : 'origin_signup'})})
    
    def post(self, request):
        email, username, password = [request.POST.get('email'), request.POST.get('username'), request.POST.get('password1')]
        #check if the username and email is 'integrity_error' meaning user already have another an account
        if username == 'integrity_error' or email == 'integrity_error':
            messages.info(request=request, message= 'Existing account found with your email and you have been redirected to login istead')
            return redirect('origin_login')
        #else, just create account with the provided data, ----- check for validity first
        user_is_not_new = authenticate(request=request, email = email.upper(), password = password)
        if user_is_not_new:
            #user is not new, redirect them to login page
            messages.info(request=request, message="Account Created, Login.")
            return redirect('origin_login')
        else:
            logger.error(msg="If you see this , omo, we are cooked bro!!! cos its not suposed to run, check the authenticate, issue is nost likelty come from there, worst case, comot this else")
            #user is new, create their account and redirect them to on login --rare to un
            get_user_model().objects.create_user(email=email, username=username, password=password)
            messages.info(message="Accoutn Creation success, Login to access your onbaording.")
            return redirect('origin_login')


    
class Login(View):
    """login dashbaord"""
    def get(self, request): 
        if (send_user_to_dashboard := try_send_user_to_dashboard(request)) is not None: return send_user_to_dashboard
        #user is not signed in , redirect them to the login page
        return render(request, 'html/login.html', {'url_for_form': reverse('origin_redirect_handler', kwargs={'raw_url': 'origin_login'})})
    
    def post(self,request): return JsonResponse({'user_email' : str(request.user)}, safe=False)

class Reports(View):
    def get(self, request): return render(request, 'html/demo_weekly_report.html')





class TestSearch(View):
    def get(self, request):return render(request, 'html/test_friend_search.html')
    
class InProgress(View):
    """Shown for any page that isn't built yet. Always sends the "Back" button to
    wherever the user actually came from (an explicit ?next=, else HTTP_REFERER),
    never a hardcoded redirect to the landing page."""
    def get(self, request):
        back_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or '/'
        return render(request, 'reusables/still_in_progress.html', {'back_url': back_url})



"""user inteface when user logout from their account"""
class LogoutUI(View):
    def post(self, request):return self.get(request)
    def get(self, request):
        try: 
            logout(request)
            # messages.info(request,'Logout successfully done.')
            return redirect('origin_home')
        except: messages.error(request=request, message="Unable to logout. Were You log in before? please go back and try again. If error persist, please contact customer support. Quick Fix")
        return render(request, 'html/full_screen_message.html')


class Leaderboard(View):
    """Return html for leaderboard to use"""
    def get(self, request): return render(request, 'html/leaderboard.html', {
        'user_istance': request.user
    })

#PURE JSON
#NOTE: PartnerWidget used to be duplicated here AND in json_only_view.py. Because
#origin/views/__init__.py does "from .normal_view import *" AFTER "from .json_only_view
#import *", THIS copy was silently winning and shadowing every fix made to the one in
#json_only_view.py - that's the actual root cause of the partner dashboard card being
#broken (crashing on e.commitment.user_id, and showing a raw list instead of a number
#for streak_count). There is now exactly one PartnerWidget, in json_only_view.py.
        

class BlogView(View):
    """The one in charge of showing the general blog page"""
    login_url = '/v1/login/'
    
    def get(self, request):
        post = []
        data = News.objects.order_by('-date').all() #use Pgination later #brb
        
        # posts = [
        #         {
        #             'tag': 'update',
        #             'title': 'New Feature: Weekly Leaderboard is Live',
        #             'excerpt': 'See how you rank against other disciplined minds every Sunday. Opt in from your profile settings to appear on the board.',
        #             'date': 'Jul 28, 2026',
        #             'read_time': '2 min read',
        #             'url': reverse('origin_blog') + f"/{request.user.pk}",
        #             'image_url': '',  # leave empty if no image
        #             'featured': True,  # this one spans full width
        #         },
        #         {
        #             'tag': 'tip',
        #             'title': 'The 2-Minute Rule: How to Never Miss a Check-In',
        #             'excerpt': 'On your worst days, your minimum effort is your secret weapon. Here is how to set one that actually works.',
        #             'date': 'Jul 25, 2026',
        #             'read_time': '3 min read',
        #             'image_url': '',
        #             'featured': False,
        #         },
        #         {
        #             'tag': 'guide',
        #             'title': 'Why Your Streak Reset Is a Gift, Not a Failure',
        #             'excerpt': 'The number does not define you. How you respond to the reset does. A different way to think about breaking the chain.',
        #             'date': 'Jul 20, 2026',
        #             'read_time': '4 min read',
        #             'url': '/v1/blog/streak-reset-gift/',
        #             'image_url': '',
        #             'featured': False,
        #         },
        #         {
        #             'tag': 'story',
        #             'title': 'How Opeyemi Went From Zero to 217 Days',
        #             'excerpt': 'A community member shares how one honest sentence a day rebuilt their confidence and changed their mornings.',
        #             'date': 'Jul 15, 2026',
        #             'read_time': '5 min read',
        #             'url': '/v1/blog/opeyemi-217-days/',
        #             'image_url': '',
        #             'featured': False,
        #         },
        #         {
        #             'tag': 'update',
        #             'title': 'Accountability Partners Are Here',
        #             'excerpt': 'You can now invite someone to see your consistency score. Not your entries — just your commitment to showing up.',
        #             'date': 'Jul 10, 2026',
        #             'read_time': '2 min read',
        #             'url': '/v1/blog/accountability-partners/',
        #             'image_url': '',
        #             'featured': False,
        #         },
        #         {
        #             'tag': 'tip',
        #             'title': 'Morning vs Evening Check-Ins: What the Data Says',
        #             'excerpt': 'Our analytics show morning check-ins average 52 words. Evening ones? 24. What your timing reveals about your mindset.',
        #             'date': 'Jul 5, 2026',
        #             'read_time': '3 min read',
        #             'url': '/v1/blog/morning-vs-evening/',
        #             'image_url': '',
        #             'featured': False,
        #         },
                
        #         #to show image
        #         {
        #             'tag': 'update',
        #             'title': 'New Feature: Weekly Leaderboard is Live',
        #             'excerpt': '...',
        #             'date': 'Jul 28, 2026',
        #             'read_time': '2 min read',
        #             'url': '/v1/blog/weekly-leaderboard-launch/',
        #             'image_url': Static.logo_url(),
        #             'featured': True,
        #         },
        #     ]
        news_choices = ChoicesValidatorInModels().news_category
        #this used to be a hardcoded 'tier': 'gold' placeholder regardless of who was
        #looking at the page - meant EVERY visitor's "share your story" form thought
        #they had gold-tier banner access. Now it reflects the real signed-in user
        #(and 'free' for a logged-out visitor, who can't submit a story at all).
        viewer_profile = Profile.objects.filter(user=request.user).first() if request.user.is_authenticated else None
        context = {
            'tier': viewer_profile.tier if viewer_profile else 'free',
            'posts': post,
            'categories': list(news_choices),   # unique tags, sourced from the same list staff picks from - was previously a stale hardcoded ['Update','TIP','Guide','Story'] that didn't match what staff could actually publish
            'news_tags': list(news_choices),     #for the is_staff form
        }
        
        if data.count() < 1 : return render(request, 'html/blog_and_update.html', {"page_mode": request.COOKIES.get('sd-theme', ''),**context})
        post = [
            {
                'id': i.pk,
                'tag' : i.tag,
                'title': i.title,
                'excerpt': i.excerpt,
                'date': i.date,
                'read_time'  :i.read_time,
                'url': reverse('origin_blog_detail', kwargs={'pk': i.pk}),
                'image_url': i.banner,
                'featured': i.featured,
                #author badge shown on the card - staff-authored posts read "Staff", user
                #submissions read "Community" (or "Anonymous" if the submitter chose that) -
                #see News.is_staff_authored() in models.py
                'is_staff_authored': i.is_staff_authored(),
                'author_label': 'Anonymous' if i.is_anonymous else (i.submitted_by.username if i.submitted_by_id else None),
            }
            for i in data
        ]
        context['posts'] = post

        return render(request, 'html/blog_and_update.html', {"page_mode": request.COOKIES.get('sd-theme', ''),**context})
    
class BlogViewExpanded(View):
    """The full article page a user lands on after clicking a post from the Blog &
    Updates list. 404s (via Http404, which our custom handler404 now renders as the
    friendly "Still in Progress" screen rather than a dead end) if the news id doesn't
    exist - covers both a bad/old link and a post a staff member has since removed."""
    def get(self, request, pk):
        post = News.objects.filter(pk=pk).first()
        if post is None:
            raise Http404
        #a few more recent posts to keep people reading, excluding the one they're already on
        more_posts = News.objects.exclude(pk=pk).order_by('-date')[:3]
        return render(request, 'html/news_detail.html', {
            'page_mode': request.COOKIES.get('sd-theme', ''),
            'post': post,
            'more_posts': more_posts,
        })


class CreateUserStory(LoginRequiredMixin, View):
    """Lets an ordinary (non-staff) user publish their own accountability story to the
    blog - the public "share your story" form on blog_and_update.html posts here.
    Always forced into tag='story' (users can't publish under 'update'/'tip'/etc,
    that's staff-only via CreateBlog in staff.py) and always stamps submitted_by so
    News.is_staff_authored() correctly shows a "Community"/"user typed" badge instead
    of the "Staff" one.

    GOLD-ONLY BANNER, ENFORCED HERE (not just hidden in the UI): the frontend already
    hides the banner upload field unless tier=='gold' (see blog_and_update.html), but
    that's just UX - a non-gold user could still POST a banner file directly to this
    endpoint, so we re-check request.user's actual Profile.tier server-side and
    silently drop any banner file that arrives from a non-gold account rather than
    trusting whatever the browser sent.
    """
    login_url = '/v1/login/'

    def post(self, request):
        data = request.POST
        banner = request.FILES.get('banner')

        required_fields = ['title', 'excerpt', 'actual_content']
        missing = [f for f in required_fields if f not in data or str(data.get(f)).strip() == '']
        if missing:
            return JsonResponse({'message': f"Please fill in: {', '.join(missing)}."}, status=400)

        MAX_LENGTHS = {'title': 220, 'excerpt': 1000}
        for field, limit in MAX_LENGTHS.items():
            if len(str(data[field])) > limit:
                return JsonResponse({'message': f"'{field}' is {len(str(data[field]))} characters, but only {limit} are allowed. Trim it and try again."}, status=400)

        try:
            read_time = max(1, round(len(str(data['actual_content']).split()) / 200)) #~200 wpm estimate, same idea as staff's manual read_time field but users aren't asked to guess their own
        except Exception:
            read_time = 3

        profile = Profile.objects.filter(user=request.user).first()
        is_gold = bool(profile and profile.tier == ChoicesValidatorInModels().tier[2]) #tier[2] == 'gold' - see models.py ChoicesValidatorInModels

        if banner and not is_gold:
            #backend re-check, independent of whatever the frontend allowed through - see docstring
            banner = None

        try:
            with transaction.atomic():
                story = News.objects.create(
                    title=data['title'],
                    tag='story',
                    excerpt=data['excerpt'],
                    read_time=read_time,
                    featured=False,
                    actual_content=data['actual_content'],
                    submitted_by=request.user,
                    is_anonymous=str(data.get('is_anonymous', 'false')).strip().lower() in ('true', '1', 'on'),
                )
                if banner:
                    from utility.file_upload import upload_news_banner
                    output = upload_news_banner(uploaded_file=banner, id=story.id)
                    story.banner = output['url']
                story.full_clean()
                story.save()
        except models.IntegrityError:
            return JsonResponse({'message': f"A post with the title \"{data['title']}\" already exists. Please choose a different title."}, status=400)
        except Exception as e:
            logger.error("User story submission failed for user %s: %s", request.user.pk, e, exc_info=True)
            return JsonResponse({'message': "Something went wrong publishing your story. Please try again in a moment."}, status=500)

        return JsonResponse({'message': 'Your story is live on the blog - thank you for sharing!', 'url': reverse('origin_blog_detail', kwargs={'pk': story.pk})}, status=200)

#Json ONly response
class GetLeaderBoardData(View):
    def get(self, request):
        if 'last_week' in request.GET: #last week leaderboards
            #There is no model that snapshots a past week's ranking (no
            #WeeklyLeaderboardSnapshot-type table exists), so there is no
            #real data to serve here. Rather than faking 10 "unavailable"
            #rows like before (which LIES to the frontend by claiming success),
            #we return an honest empty/failed response so the UI can show
            #its real error state instead of a fake board.
            return JsonResponse({
                'message': 'Last week\'s leaderboard is not available yet - historical snapshots are not stored.',
                'entries': [],
                'total_participants': None,
                'most_active_day': None,
                'your_rank': None,
                'your_total_streak': None,
                'week_label': None,
                'week_number': None,
            }, status=200)

        #the current week

        #Monday->Sunday boundaries for "this week", used for the week
        #label/number shown in the hero, and to scope "most active day"
        #to entries actually logged during the current week.
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())   #this week's Monday
        week_end = week_start + timedelta(days=6)               #this week's Sunday

        #Every opted-in profile, ranked by zeal_score (already the same
        #"combined discipline" figure shown on the dashboard). Ordered
        #query, not sliced yet, because we need every opted-in user's
        #position to answer "your_rank" correctly even if the requester
        #is ranked outside the visible top 10.
        ranked_profiles = list(
            Profile.objects.filter(leaderboard_optin=True)
            .select_related('user')
            .order_by('-zeal_score', 'user_id')   #user_id as tiebreaker so ties don't reshuffle order between requests
        )

        entries = []
        your_rank = None
        your_total_streak = None

        for idx, profile in enumerate(ranked_profiles, start=1):
            #streak_count_is_public_visible hides just the NUMBER, not the
            #whole row - the user still occupies their rank slot.
            score_is_public = profile.streak_count_is_public_visible

            if idx <= 10:   #card UI only ever renders 10 slots
                entries.append({
                    'rank': idx,
                    'public_id': profile.public_searchable_username or 'unavailable',
                    'total_streak': profile.zeal_score if score_is_public else None,
                    'private': not score_is_public,
                    'user_profile_pic': profile.profile_img_url or '',
                })

            if request.user.is_authenticated and profile.user_id == request.user.id:
                your_rank = idx
                #"Your Position" is a private-to-you section (never shown
                #to others per the UI copy), so it always shows the real
                #score regardless of the public-visibility toggle.
                your_total_streak = profile.zeal_score

        #Most active day this week, based on journal entries actually
        #logged in week_start..week_end (Entries.commit_at is a plain
        #DateField set on creation).
        day_counts = {}
        for commit_at in Entries.objects.filter(commit_at__range=(week_start, week_end)).values_list('commit_at', flat=True):
            day_name = commit_at.strftime('%A')
            day_counts[day_name] = day_counts.get(day_name, 0) + 1
        most_active_day = max(day_counts, key=day_counts.get) if day_counts else None

        return JsonResponse({
            "message": "ok",
            "week_label": f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}",
            "week_number": week_start.isocalendar()[1],
            "entries": entries,
            "total_participants": len(ranked_profiles),
            "most_active_day": most_active_day,
            "your_rank": your_rank,
            "your_total_streak": your_total_streak,
        })
