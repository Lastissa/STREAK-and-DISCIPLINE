from django.shortcuts import render, resolve_url, redirect, reverse
from django.http import JsonResponse, Http404
from django.views import View
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.core.cache import cache
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.core.validators import validate_email
from resend.exceptions import ResendError
from origin.models import PasswordResetToken


from origin.models import Profile,Commitment, Entries, Friendship, ChoicesValidatorInModels

import json, random, uuid
from utility.config import *
from utility.email_sending import send_password_reset_email, send_password_reset_successful_email
import logging

logger = logging.getLogger(__name__)

class RedirectHandler(View):
    """handling redirect from one page to another"""
    def post(self, request, raw_url):
        if request.GET.get('login_account'):
            """Proceed to login user and create session"""
            try:
                user_exist = get_user_model().objects.filter(email__iexact = request.POST["email"]).first() is not None
                user_istance = authenticate(request=request, email = request.POST["email"], password = request.POST["password"])
                logger.info(msg= user_istance)
                if user_istance or user_exist:
                    #set a key in cache to rate limit after 3 attempt
                    rate_limit = cache.get(f"attemp_login_{request.POST["email"]}") if cache.get(f"attemp_login_{request.POST["email"]}") is not None else ""
                    if len(rate_limit)  <3:
                        messages.info( request=request,message= f"Incorrect password or Email.")
                        cache.set(f"attemp_login_{request.POST["email"]}", rate_limit+"x", timeout=120)
                    elif len(rate_limit) == 3:
                        messages.warn( request=request,message= f"Incorrect password or Email., one more fail attempt will lock you out. ")
                        cache.set(f"attemp_login_{request.POST["email"]}", rate_limit+"x", timeout=120)
                    else:
                        messages.info( request=request,message=f"Too many attempts. Please wait 2 minutes before trying again. If you try again before the time is up, the wait period will reset.---{rate_limit}")
                        cache.set(f"attemp_login_{request.POST["email"]}", "banned", timeout=120)
                        return redirect('origin_login')
                    
                    #user found but user password is wrong
                    if not user_istance:
                        logout(request)
                        return redirect('origin_login') 
                        
                    #user found, create a session and direct onboarding to handle wether it should direct user to dashboard or stay
                    login(request=request, user=user_istance, backend='django.contrib.auth.backends.ModelBackend')  #i currently have three login style set up, hence why i need to specify which i wan to use
                    return redirect('origin_onboarding')
                else:
                    logger.warning(msg=f"userexist : {user_exist} is false and also user_istance {user_istance} is false")
                    #no valid credentials, logout any existing session and return back to login
                    logout(request)
                    messages.info(request=request, message= "No account found, Create account to get onboard...")
                    return redirect('origin_signup')            
            except Exception as e:
                return JsonResponse(
                    {"message" : "Redirect failed. Refresh the page. If it persists, copy the error_text and send it to any of our customer support .",
                 'error_text' : f'email = {request.POST.get('email')} \nUsername = {request.POST.get('username')}\nPassword1 = {request.POST.get('password1')} \ndomain = {request.build_absolute_uri()} \nqueryParams = {request.GET.keys()}',
                 "status" : "error",
                 "statcktrace": str(e)},status = 502)
        
        if request.GET.get("create_account"):
            """proceed to create account"""
            try:
                user = get_user_model().objects.create_user(
                    username= request.POST['username'],
                    email = request.POST['email'],
                    password= request.POST['password1']
                    )
                logger.warning(msg="Account created succesfully, redirecting user to the target with post request")
                return render(request, 'reusables/redirect_url.html', {
                    'redirect_path': reverse(raw_url),
                    'username' : request.POST['username'],
                    'email' : request.POST['email'] ,
                    'password1' : request.POST['password1']
                    })
            
            except IntegrityError as e:
                """create user fail, switch to login istead"""
                logger.warning(msg="integrgtity error; user with this account exist")
                return render(request, 'reusables/redirect_url.html', {
                    'redirect_path': reverse(raw_url),
                    'username' : 'integrity_error' ,
                    'email' : 'integrity_error' ,
                    'password1' : 'integrity_error'
                    })
            
            except Exception as e :return JsonResponse(
                {"message" : "Redirect failed. Refresh the page. If it persists, copy the error_text and send it to any of our customer support .",
                 'error_text' : f'email = {request.POST.get('email')} \nUsername = {request.POST.get('username')}\nPassword1 = {request.POST.get('password1')} \ndomain = {request.build_absolute_uri()} \nqueryParams = {request.GET.keys()}',
                 "status" : "error",
                 "statcktrace": str(e)},
                status = 502)
    
    def get(self, request, raw_url):
        """return user to that same url they want to go and if the url is invalid; raise error"""
        try:return redirect(raw_url)
        except:raise Http404

class OriginHome(View):
    def get(self, request):
        messages.info(request, message=intro_word()[0])
        # messages.info(request, message= intro_word()[1])
        return render(request, 'html/landing_page.html', {
            'consistency' : get_consistency_Value(),
            'journal_created': get_journal_created_value(),
            'year': get_copyright_year()
        })

#this handle save user data during onboarding 
class DbSave(LoginRequiredMixin,View):
    def post(self, request):
        data = json.loads(request.body)
        #first create a unique user id using customeUser username + pk
        user_id = f"{request.user.username}{request.user.id:02d}" 
        #clean data format
        public_searchable_username = user_id
        #commitment
        commitment_data = data['commitment']
        commitment_what = commitment_data['what']                                       #name of the commitment
        commitment_category = commitment_data['category']                               #category to which commitment belong
        commitment_why = commitment_data.get('why')                                     #why user want to make this commitment
        commitment_goal_days = commitment_data['goal_days']                             #total duration to which this commitment can last for ; 0 is forver
        commitment_minimum = commitment_data['minimum']                                 #this is used for analytics to compare user down days, up and normals days
        #time concious
        schedule_data = data['schedule']
        schedule_checkin_time = schedule_data['checkin_time']                           #time user is expected to check in
        schedule_reminder_time = schedule_data['reminder_time']                         #time user schedules to be reminded for checking
        reminder_method = schedule_data['reminder_method']                              #mode of reminder, push , email or whatsapp
        whatsapp_number = schedule_data.get('whatsapp_number')              #incase user choose whatsapp, the number to which we will send reminder
        #evaluating partner prefrences 
        social_data = data['social']
        social_mode_settings = social_data['mode']                                               #Wether user want to share their streak count with others or go solo; the streak core include commitment name(what) and their current streak in that commitment
        social_friend_user_id = social_data.get('friend_uuid', '').strip()                          #incase user choose partner else this should be ''
        leaderboard_opt_in = social_data.get('leaderboard_optin')                       #Wethet user show in weekly dashboard or not (if yes, only user_id and their zeal_score shows and maybe profile pic if they have)
        #user prefrence
        preferences_data = data['preferences']
        preferences_theme = preferences_data.get('theme', 'dark').lower().strip()           #to make sure user is alwasy in a particular mode when they login (little details matter)
        allow_preferences_allow_ai_insight = preferences_data.get('ai_insights')            #wether to allow us sened their data anonymously to AI to generate insight for their report prepartion
        allow_preferences_occasional_email = preferences_data['newsletter']                 #wether user want to receive occasional New features , tips, discipline contents

        customVal = ChoicesValidatorInModels()
    
        #first; The profile model validation
        if preferences_theme not in customVal.theme: return JsonResponse({'message': f'theme : {preferences_theme} not in available options'}, status = 404)
        elif social_mode_settings not in customVal.social_mode: return JsonResponse({'message': f'social mode : {social_mode_settings} not in available options'}, status = 404)
       
        #second; the Commitment model validation
        if commitment_category not in customVal.commitment_category: return JsonResponse({'message': f'commitment_category : \'{commitment_category}\' not in available options'}, status = 404)
        elif reminder_method not in customVal.report_delivery_mode: return JsonResponse({'message': f'reminder_method : {reminder_method} not in available options'}, status = 404) 
        elif reminder_method.lower().strip() == "whatsapp" and len(whatsapp_number) == 0: return JsonResponse({'message' : 'whatsapp selected as reminder but whatsapp number was not provided.'}, status = 404)
        elif reminder_method.lower().strip() == "whatsapp"  and str(whatsapp_number[1:]).isdigit() == False:  return JsonResponse({'message' : f'whatsapp number({whatsapp_number}) is not a valid mobile number'}, status = 404)
        
        #third; the Friendship -- i need to verify tbat user exist, that is if they are PARTNER mode
        if social_mode_settings.strip().lower() == customVal.social_mode[1]:
            from_user_istance = request.user
            to_user_istance = Profile.objects.filter(public_searchable_username__iexact = social_friend_user_id).first()
            print(f'{to_user_istance}')
            if to_user_istance is None: return JsonResponse({'message' : f"user id:'{social_friend_user_id}' does not exist hence your request will be revoked, kindly recheck the userid or switch to solo"}, status = 404)

        #if we get here and no issues; all data is valid , create
        with transaction.atomic():
            profile_istance = Profile.objects.create(
                user = request.user,
                public_searchable_username = public_searchable_username,
                leaderboard_optin = leaderboard_opt_in,
                ai_insight_active = allow_preferences_allow_ai_insight,
                receive_newsletter = allow_preferences_occasional_email,
                theme = preferences_theme,
                social_mode = social_mode_settings
            )
            
            commitment_istance = Commitment.objects.create(
                user = request.user,
                checkin_time = schedule_checkin_time,
                category = commitment_category,
                what = commitment_what,
                why = commitment_why,
                minimum_effort = commitment_minimum,
                goal_days = commitment_goal_days,
                mode_of_delivery = reminder_method,
                whatsapp_number = whatsapp_number,
                user_selected_reminder_time = schedule_reminder_time,
                
            )
            if social_mode_settings.strip().lower() == "partner":
                helper = helper_with_friendship_request_answer(request=request, to_user=social_friend_user_id.strip())
                #so the issue can be returned succesdully
                if helper is not None: return helper_with_friendship_request_answer
                
        return JsonResponse({'message' : 'success'}, status = 200)

def helper_with_friendship_request_answer(request, to_user : str):
    """Since this code have to be repeated in both add friend and dbsaver, to avoid duplicate, i created this file which i will use in both class"""
    from_user = request.user
    to_user = Profile.objects.filter(public_searchable_username__iexact = to_user.upper().strip()).first()
    
    if to_user is None:return JsonResponse({'message': f"potential partner '{social_friend_user_id}' does nt exist , please ask the user to share you their current username as they might have updated it." })
                    
    #check if user is trying to send request to theirself
    if to_user.user.email == request.user.email: return JsonResponse({'message': 'request to oneself is not allowed'}, status = 403)
    
    #check their status, if its pending -- request already sent at TIME, accepted -- you are already friends with this user since TIME
    relationship = Friendship.objects.filter(from_user = from_user, to_user = to_user.user).first()
    if relationship is None:
        #send request --brb send email to notify to user also
        istance = Friendship.objects.create(
            from_user = from_user,
            to_user = to_user.user,
            status = ChoicesValidatorInModels().friendship_status[0], #pending
        )
    elif relationship.status == ChoicesValidatorInModels().friendship_status[0]: return JsonResponse({'message' : f'request already sent since {custom_date_formatter(datetime_data = relationship.updated_at)} --pending'}, status = 200)
    elif relationship.status == ChoicesValidatorInModels().friendship_status[1]: return JsonResponse({'message' : f'you are already friend with this person since {custom_date_formatter(datetime_data = relationship.updated_at)}'}, status = 200)
    else:
        # status was 'rejected' — allow resending
        relationship.status = 'pending'
        relationship.save()
        return None
    

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
        print(email, username, password)
        #check if the username and email is 'integrity_error' meaning user already have another an account
        if username == 'integrity_error' or email == 'integrity_error':
            messages.info(request=request, message= 'Existing account found with your email and you have been redirected to login istead')
            return redirect('origin_login')
        #else, just create account with the provided data, check for validity first
        user_is_not_new = authenticate(request=request, email = email, password = password)
        if user_is_not_new:
            #user is not new, redirect them to login page
            messages.info(request=request, message="Account Created, Login.")
            return redirect('origin_login')
        else:
            #user is new, create their account and redirect them to on login
            get_user_model().objects.create_user(email=email, username=username, password=password)
            messages.info(message="Accoutn Creation success, Login to access your onbaording.")
            return redirect('origin_login')
        #fallback almost impossible to reach
        return JsonResponse({'user' : str(request.user), **request.POST}, safe=False)

    
class Login(View):
    """login dashbaord"""
    def get(self, request): return render(request, 'html/login.html', {'url_for_form' : reverse('origin_redirect_handler', kwargs={'raw_url' : 'origin_login'})})
    
    def post(self,request): return JsonResponse({'user_email' : str(request.user)}, safe=False)

class Reports(View):
    def get(self, request): return render(request, 'html/demo_weekly_report.html')

class Dashboard(LoginRequiredMixin, View):
    login_url = '/v1/login/'
    def get(self, request):
        #COMMITMENT_LIST CLAUDE NEEDS
        # {
        # "id": 1,
        # "url": "/commitment/1/",
        # "what": "Read 20 pages",
        # "category": "study",
        # "streak_count": 14,
        # "goal_days": 90,
        # "days_since_start": 21,
        # "checked_in_today": false,
        # "last_check_in": "2025-07-26T21:00:00Z",
        # "checkin_time": "21:00",
        # "reminder_active": true,
        # "is_active": true,
        # "mood_last": "motivated"
        # }
        
        
        data = {
            'commitment_list' :[{'name' : '', 'due_today': bool, 'streak' : int}],#list of commitment name and wether they are due
            'tier' : '',                                                                 #Hold usr current tier
            'Upcoming_milestone': int
        }
#         profile_istance = Profile.objects.filter(user = request.user).first()
#         Commitment_istance = Commitment.objects.filter(user = request.user).all()
#         partner_request_received = Friendship.objects.filter(to_user = request.user).all()
#         friend_request_sent = Friendship.objects.filter(from_user = request.user).all()
#         if partner_request_received is None: partner_list_received = []
#         else: partner_list_received = [{
#                             'from_user': f.from_user.email,
#                             'to_user': f.to_user.email,
#                             'status': f.status,
#                             'created_at': f.created_at.isoformat(),
#                             'updated_at' : f.updated_at.isoformat()
#                         }
#                         for f in partner_request_received] 
#         if friend_request_sent is None: partner_list_sent = []
#         else: partner_list_sent = [{
#                                     'from_user': f.from_user.email,
#                                     'to_user': f.to_user.email,
#                                     'status': f.status,
#                                     'created_at': f.created_at.isoformat(),
#                                     'updated_at' : f.updated_at.isoformat()
#                                 }
#                                 for f in friend_request_sent] 
        
#         return JsonResponse({
#             'username' : request.user.username,
#             'email' : request.user.email,
#             'last_login' : request.user.last_login,
#             'join_date' : request.user.date_joined,
#             'user_id' : profile_istance.public_searchable_username,
#             'profile_istance' : {
#                         'tier': profile_istance.tier,
#                         'public_searchable_username': profile_istance.public_searchable_username,
#                         'leaderboard_optin': profile_istance.leaderboard_optin,
#                         'streak_count_is_public_visible': profile_istance.streak_count_is_public_visible,
#                         'ai_insight_active': profile_istance.ai_insight_active,
#                         'receive_newsletter': profile_istance.receive_newsletter,
#                         'theme': profile_istance.theme,
#                         'weekly_report_email_active': profile_istance.weekly_report_email_active,
#                         'custom_report_email_active': profile_istance.custom_report_email_active,
#                         'social_mode': profile_istance.social_mode,
#                         'zeal_score': profile_istance.zeal_score,
# },
#             'commitment' : [{
#                             'what': c.what,
#                             'category': c.category,
#                             'why': c.why,
#                             'goal_days': c.goal_days,
#                             'streak_count': c.streak_count,
#                             } for c in Commitment_istance],
#             'friend_request_received' : partner_list_received,
#             'friend_request_sent' : partner_list_sent
#             }, safe=False)

class Onboarding(LoginRequiredMixin, View):
    login_url = '/v1/login/'
    def get(self, request):
        #check user tier, if it does not exist, redirect user to onboarding
        user_profile = Profile.objects.filter(user = request.user).first()
        print(user_profile)
        if user_profile is None: return render(request,'html/onboarding.html')
        else: return redirect('origin_dashboard')

class SearchFriend(LoginRequiredMixin,View):#This one is specifically only for logged in user
    login_url = '/v1/login/'
    def get(self, request): return self.post(request)
    def post(self, request):
        data = request.POST['uuid']
        friend_search = Profile.objects.filter(public_searchable_username__iexact = data).last()
        if friend_search:
            userid = friend_search.public_searchable_username
            username = friend_search.user.username
            profile_image = ''# friend_search.profile_img_url
            status_code = 200
        else:
            userid, username, profile_image = None, None, ''
            status_code = 404
        return JsonResponse({
            'userid' : userid,                        #use username + dabatase pk to make it unique
            'username' : username,
            'profile_image' : profile_image,
        }, status = status_code)
        
class AddFriend(LoginRequiredMixin, View):
    login_url = '/v1/login'
    def get(self, request):return self.post(request)
    def post(self, request):
        incoming_user_id = request.POST['userid']
        print(incoming_user_id)
        req = helper_with_friendship_request_answer(request=request, to_user = incoming_user_id.strip())
        print(req)
        if req is None: return JsonResponse({'message': 'success, requst resend successfuly'}, status = 200)
        else: return req


class TestSearch(View):
    def get(self, request):return render(request, 'html/test_friend_search.html')
    
class InProgress(View):
    def get(self, request):return render(request, 'reusables/still_in_progress.html')


class PasswordReset(View):
    def post(self, request):
        """To send a jsonresponse for the password reset pageback saying, email have been set and on any error, send maybe status 500"""
        try:
            #create a ticket for user if user exist
            fetched_email = request.POST["email"]
            validate_email(fetched_email)
            user_email = get_user_model().objects.filter(email__iexact = fetched_email).first()
            if user_email:
                """Valid user, prepare token"""
                token = "".join(random.sample("123456789abcdefghijklmnopqrsuvwxyzABCDEFGHIJKLMNOPRSTUVWXYZ", Static.token_lenght()))
                save_token_to_db = PasswordResetToken.objects.create(user = user_email, token  = token)
                save_token_to_db.save()
                send_password_reset_email(
                    to_email=fetched_email,
                    endpoint=reverse('origin_password_reset_validate',
                    kwargs={'email' : user_email, 'token': token}),
                    expiry=Static.token_expiry_time(),
                    username=user_email)  
                    
                return JsonResponse({'message': 'Request received, If email exist in our database you will receive a reset link within the next few seconds, refresh page to resend get a new link - old user'}, status = 200)
            #no user found
            return JsonResponse({'message': 'Request received, If email exist in our database you will receive a reset link -new user'})
        except ResendError as e:
            logger.error(msg=f"Error happened while trying to send user their password reset email , error is {e}")
            return JsonResponse({'message': 'Oops, you dont seem to have internet connection, please try again when you are connected.-Refresh page to resend link'})
        except ValidationError as e: return JsonResponse({"message" : "Invalid Email, Refresh page to try again"})
        except Exception as e:
            logger.error(msg=f"user {fetched_email} tried to reset password and eperience error  : {e}")
            return JsonResponse({"message" : "Please refresh page and retry again but if message persiste, contact customer support as we might be experiencing internal issue"})
       
    """To show user the password reset link """     
    def get(self, view): return render(self.request, 'html/password_reset.html')

class PasswordValidate(View):
    """after the user have click the link and input their new password and confirm the email on their account , password will be reset here"""
    def get(self, request, email, token):
        """Check if the url is valid."""
        token_still_valid_in_db = PasswordResetToken.objects.filter(user__email__iexact = email, token = token).first()
        #validate token still exist
        if token_still_valid_in_db is None:
            messages.error(request, message="This URL is INVALID. This might happen if the url have been used before OR your account does not exist.")
            return render(request, 'html/full_screen_message.html')
        #check if it has expired
        token_have_not_expired = (timezone.now() - token_still_valid_in_db.date_created).seconds < Static.token_expiry_time()
        if token_have_not_expired is False:
            messages.info(request, message=f"The Link have Expired as the {int(Static.token_expiry_time()/60)} minutes timeout have been reached.")
            return render(request, 'html/full_screen_message.html')
        #return normal page for reset since token still exist.
        return render(request, 'html/final_step_of_password_reset.html', {'expiry_seconds': Static.token_expiry_time})
    
    def post(self, request, email, token):
        #check if the data still exist in the db
        token_still_valid_in_db = PasswordResetToken.objects.filter(user__email__iexact = email, token = token).first()
        #validate token still exist
        if token_still_valid_in_db is None:
            messages.error(request, message="This URL is INVALID. This might happen if the url have been used before OR your account does not exist.")
            return render(request, 'html/full_screen_message.html')
        
        #token is still in the db, check if it have expired
        token_have_not_expired = (timezone.now() - token_still_valid_in_db.date_created).seconds < Static.token_expiry_time()
        if token_have_not_expired is False:
            messages.info(request, message=f"The Link have Expired as the {int(Static.token_expiry_time()/60)} minutes timeout have been reached.")
            return render(request, 'html/full_screen_message.html')
        
        #over here, The link is still valid, update password and invalidate token and then redirect to login page
        if token_still_valid_in_db:
            get_istance = get_user_model().objects.filter(email__iexact = email).first()
            get_istance.set_password(request.POST['password1'])
            get_istance.save()
            PasswordResetToken.objects.filter(user__email__iexact = email).delete()
            send_password_reset_successful_email(to_email=email, username=f"{get_istance.username}")
            messages.info(request, message="Password Reset Successfully")
            return redirect('origin_login')

        return JsonResponse({'user': email, 'token' : token, 'still_valid' : token_still_valid_in_db is not None, 'token_have_not_expired': token_have_not_expired, 'password1' : request.POST['password1']}, safe=False)
        
"""debugging purpose"""
class Logout(View):
    def get(self, request): return self.post(request)
    def post(self, request):
        logout(request)
        return JsonResponse({'message' : 'All active members  have been logged out on this device'}, status = 200)
    
"""user inteface when user logout from their account"""
class LogoutUI(View):
    def get(self, request):
        try: 
            logout(request)
            messages.info('logout success')
        except: return messages.error(request=request, message="Unable to logout , please go back and try again. If error persist, please contact customer support")
        return render('html/full_screen_message.html')
    
    
    
    
#PURE JSON
