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
logger = logging.getLogger(__name__)


class OriginHome(View):
    def get(self, request):
        messages.info(request, message=intro_word()[0])
        # messages.info(request, message= intro_word()[1])
        return render(request, 'html/landing_page.html', {
            'consistency' : get_consistency_Value(),
            'journal_created': get_journal_created_value(),
            'year': get_copyright_year()
        })


class Extras(View):
    """for privacy policy, term of use etc"""
    def get(self, request): return render(request, 'html/privacy_etc.html')
    
class Signup(View):
    """signup page"""
    def get(self, request): 
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
        #try to check if user is signed in
        if request.user.is_authenticated:
                return redirect('origin_onboarding')
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
        except: 
            messages.error(request=request, message="Unable to logout. Were You log in before? please go back and try again. If error persist, please contact customer support. Quick Fix")
        return render(request, 'html/full_screen_message.html')


class Leaderboard(View):
    """Return html for leaderboard to use"""
    def get(self, request): return render(request, 'html/leaderboard.html')

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
        if data.count() < 1 : return render(request, 'html/blog_and_update.html', {})
        post = [
            {
                'tag' : i.tag,
                'title': i.title,
                'excerpt': i.excerpt,
                'date': custom_date_formatter(datetime_data=i.date),
                'read_time'  :i.read_time,
                'url': reverse('origin_blog') + f"/{i.pk}",
                'image_url': i.banner,
                'featured': i.featuered
            }
            for i in data
        ]
        for i in data:
                post.append(
                    {
                        'tag' : i.tag,
                        'title': i.title,
                        'excerpt': i.excerpt,
                        'date': custom_date_formatter(datetime_data=i.date),
                        'read_time'  :i.read_time,
                        'url': reverse('origin_blog') + f"/{i.pk}",
                        'image_url': i.banner,
                        'featured': i.featuered
                    })
                posts = [
                    {
                        'tag': 'update',
                        'title': 'New Feature: Weekly Leaderboard is Live',
                        'excerpt': 'See how you rank against other disciplined minds every Sunday. Opt in from your profile settings to appear on the board.',
                        'date': 'Jul 28, 2026',
                        'read_time': '2 min read',
                        'url': reverse('origin_blog') + f"/{request.user.pk}",
                        'image_url': '',  # leave empty if no image
                        'featured': True,  # this one spans full width
                    },
                    {
                        'tag': 'tip',
                        'title': 'The 2-Minute Rule: How to Never Miss a Check-In',
                        'excerpt': 'On your worst days, your minimum effort is your secret weapon. Here is how to set one that actually works.',
                        'date': 'Jul 25, 2026',
                        'read_time': '3 min read',
                        'image_url': '',
                        'featured': False,
                    },
                    {
                        'tag': 'guide',
                        'title': 'Why Your Streak Reset Is a Gift, Not a Failure',
                        'excerpt': 'The number does not define you. How you respond to the reset does. A different way to think about breaking the chain.',
                        'date': 'Jul 20, 2026',
                        'read_time': '4 min read',
                        'url': '/v1/blog/streak-reset-gift/',
                        'image_url': '',
                        'featured': False,
                    },
                    {
                        'tag': 'story',
                        'title': 'How Opeyemi Went From Zero to 217 Days',
                        'excerpt': 'A community member shares how one honest sentence a day rebuilt their confidence and changed their mornings.',
                        'date': 'Jul 15, 2026',
                        'read_time': '5 min read',
                        'url': '/v1/blog/opeyemi-217-days/',
                        'image_url': '',
                        'featured': False,
                    },
                    {
                        'tag': 'update',
                        'title': 'Accountability Partners Are Here',
                        'excerpt': 'You can now invite someone to see your consistency score. Not your entries — just your commitment to showing up.',
                        'date': 'Jul 10, 2026',
                        'read_time': '2 min read',
                        'url': '/v1/blog/accountability-partners/',
                        'image_url': '',
                        'featured': False,
                    },
                    {
                        'tag': 'tip',
                        'title': 'Morning vs Evening Check-Ins: What the Data Says',
                        'excerpt': 'Our analytics show morning check-ins average 52 words. Evening ones? 24. What your timing reveals about your mindset.',
                        'date': 'Jul 5, 2026',
                        'read_time': '3 min read',
                        'url': '/v1/blog/morning-vs-evening/',
                        'image_url': '',
                        'featured': False,
                    },
                    
                    #to show image
                    {
                        'tag': 'update',
                        'title': 'New Feature: Weekly Leaderboard is Live',
                        'excerpt': '...',
                        'date': 'Jul 28, 2026',
                        'read_time': '2 min read',
                        'url': '/v1/blog/weekly-leaderboard-launch/',
                        'image_url': Static.logo_url(),
                        'featured': True,
                    },
                ]
        
        context = {
            'tier': 'gold',
            'posts': posts,
             'categories': ['Update', 'TIP', 'Guide', 'Story'],  # unique tags
        }

        return render(request, 'html/blog_and_update.html', context)
    
class BlogViewExpanded(View):
    def get(self, request):
        """When usr click on that blog and they want to see the content, colect the blog id from user as extra sub endpoint"""
    

#Json ONly response
class GetLeaderBoardData(View):
    def get(self, request):
        if 'last_week' in request.GET: #last week leaderboards
            rank_list = []
            for i in range(1,11):
                rank_list.append({
                    'rank': i ,'public_id': 'unavailable', 'total_streak': None, 'private': False
                })
            return JsonResponse({'entries': rank_list, 'total_participants': None, "most_active_day": None, "your_rank": None, "your_total_streak": None,}, status = 200)
        
        #the current week
        return JsonResponse({
    "message": "ok",
    "week_label": "Jul 21 – Jul 27, 2026",
    "week_number": 30,
    "entries": [
        {"rank": 1, "public_id": "chidi007", "total_streak": 142, "private": False},
        {"rank": 2, "public_id": "opeyemi01", "total_streak": None, "private": True},
        {"rank": 3, "public_id": "david_n", "total_streak": 98, "private": False},
        {"rank": 4, "public_id": "sarah_k", "total_streak": 87, "private": False},
        {"rank": 5, "public_id": "ademide_m", "total_streak": None, "private": True},
        {"rank": 6, "public_id": "success_a", "total_streak": 76, "private": False},
        {"rank": 7, "public_id": "tunde_b", "total_streak": 64, "private": False},
        {"rank": 8, "public_id": "nkechi_o", "total_streak": None, "private": True},
        {"rank": 9, "public_id": "emeka_i", "total_streak": 51, "private": False},
        {"rank": 10, "public_id": "fatima_u", "total_streak": 43, "private": False},
        ],
        "total_participants": 47,
        "most_active_day": "Monday",
        "your_rank": 3,
        "your_total_streak": 89,
        })
        
        
