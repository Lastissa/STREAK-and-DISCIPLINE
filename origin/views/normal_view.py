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
    def get(self, request):return render(request, 'reusables/still_in_progress.html')



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


class PartnerWidget(LoginRequiredMixin, View):
    """#this handles a situation where a user wan to call up his friends and view them  --ONLY WORK IF USER social_mode IS PARTNER NOT SOLO       
"""
    def get(self, request):
        # Check social mode
        profile_istance = Profile.objects.filter(user=request.user).first()
        if profile_istance.social_mode == ChoicesValidatorInModels().social_mode[0]:
            return JsonResponse({
                'message': 'You are currently in solo mode. Only partner mode users can access this.',
            }, status=403)

        # Get accepted partnerships where user is the receiver
        partner_istance = Friendship.objects.filter(
            to_user=request.user,
            status='accepted'
        ).select_related('from_user').all()

        #Collect all partner user IDs
        partner_users = []
        for f in partner_istance:
            partner_users.append(f.from_user_id)

        #Get all active commitments for ALL partners in one query
        all_commitments = Commitment.objects.filter(
            user_id__in=partner_users,
            is_active=True
        ).all()

        #Get all entries for ALL partners in one query
        all_entries = Entries.objects.filter(
            commitment_key__user_id__in=partner_users
        ).order_by('commit_at').all()

        #Group commitments by user
        commitments_by_user = {}
        for c in all_commitments:
            uid = c.user_id
            if uid in commitments_by_user:
                commitments_by_user[uid].append(c.streak_count)
            else:
                commitments_by_user[uid] = [c.streak_count]

        #Group last active by user
        last_active_by_user = {}
        for e in all_entries:
            uid = e.commitment.user_id
            if uid not in last_active_by_user:
                last_active_by_user[uid] = e.commit_at

        #Build the partner list
        partners = []
        for f in partner_istance:
            partner_uid = f.from_user_id
            partner_profile = Profile.objects.filter(user_id=partner_uid).first()
            public_id = partner_profile.public_searchable_username if partner_profile else 'unknown'

            partners.append({
                'public_id': public_id,
                'streak_count': commitments_by_user.get(partner_uid, []),
                'last_active': str(last_active_by_user.get(partner_uid, '')),
            })

        return JsonResponse({
            'message': 'success',
            'partners': partners,
        })
        

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
        context = {
            'tier': 'gold',
            'posts': post,
            'categories': ['Update', 'TIP', 'Guide', 'Story'],  # unique tags
            'news_tags': ['Update', 'TIP', 'Guide', 'Story'],   #for the is_staff own
        }
        
        if data.count() < 1 : return render(request, 'html/blog_and_update.html', {"page_mode": request.COOKIES.get('sd-theme', ''),**context})
        post = [
            {
                'tag' : i.tag,
                'title': i.title,
                'excerpt': i.excerpt,
                'date': i.date,
                'read_time'  :i.read_time,
                'url': reverse('origin_blog') + f"/{i.pk}",
                'image_url': i.banner,
                'featured': i.featured
            }
            for i in data
        ]
        context['posts'] = post

        return render(request, 'html/blog_and_update.html', {"page_mode": request.COOKIES.get('sd-theme', ''),**context})
    
class BlogViewExpanded(View):
    def get(self, request):
        """When usr click on that blog and they want to see the content, colect the blog id from user as extra sub endpoint"""
    

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
