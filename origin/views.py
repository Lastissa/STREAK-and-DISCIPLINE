from django.shortcuts import render, resolve_url, redirect, reverse
from django.http import JsonResponse, Http404
from django.views import View
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.core.validators import validate_email
from resend.exceptions import ResendError
from origin.models import PasswordResetToken

import json, random, uuid
from utility.config import *
from utility.email_sending import send_light_email
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
                        messages.info( request=request,message= f"Invalid credentials")
                        cache.set(f"attemp_login_{request.POST["email"]}", rate_limit+"x", timeout=120)
                    elif len(rate_limit) == 3:
                        messages.warn( request=request,message= f"invalid credentials, one more fail attempt will lock you out. ")
                        cache.set(f"attemp_login_{request.POST["email"]}", rate_limit+"x", timeout=120)
                    else:
                        messages.info( request=request,message=f"Too many attempts. Please wait 2 minutes before trying again. If you try again before the time is up, the wait period will reset.---{rate_limit}")
                        cache.set(f"attemp_login_{request.POST["email"]}", "banned", timeout=120)
                        return redirect('origin_login')
                    
                    #user found but user password is wrong
                    if not user_istance:
                        logout(request)
                        return redirect('origin_login') 
                        
                    #user found, create a session and direct onboarding if last_login is null
                    login(request=request, user=user_istance, backend='django.contrib.auth.backends.ModelBackend')  #i currently have three login style set up, hence why i need to specify which i wan to use
                    if user_istance.last_login: return redirect('origin_onboarding')
                    else: return redirect('origin_onboarding', username = user_istance.username)
                else:
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
        messages.info(request, message= intro_word()[1])
        return render(request, 'html/landing_page.html', {
            'consistency' : get_consistency_Value(),
            'journal_created': get_journal_created_value(),
            'year': get_copyright_year()
        })

class DbSave(LoginRequiredMixin,View):
    def post(self, request):
        data = json.loads(request.body)
        print(data)
        print("DDD")
        return JsonResponse({**data})

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
            redirect('origin_login')
        #fallback almost impossible to reach
        return JsonResponse({'user' : str(request.user), **request.POST}, safe=False)

    
class Login(View):
    """login dashbaord"""
    def get(self, request): return render(request, 'html/login.html', {'url_for_form' : reverse('origin_redirect_handler', kwargs={'raw_url' : 'origin_login'})})
    
    def post(self,request): return JsonResponse({'user_email' : str(request.user), **request.POST}, safe=False)

class Reports(View):
    def get(self, request): return render(request, 'html/demo_weekly_report.html')

class Dashboard(LoginRequiredMixin, View):
    pass

class Onboarding(LoginRequiredMixin, View):
    login_url = '/v1/login/'
    def get(self, request):
        print(request.user.username)
        return render(request, 'html/onboarding.html', {'where_to_go_full_url' : reverse('origin_onboarding')})
    
class SearchFriend(View):
    def get(self, request):pass
    def get(self, request): 
        uuid = request.POST.get('uuid', None) #user id to look up - look up for user once this is seen
        
class AddFriend(View):
    def get(self, request):pass
    def get(self, request): 
        uuid = request.POST.get('uuid', None) #user id to look up - look up for user once this is seen
        

class InProgress(View):
    def get(self, request):
        return render(request, 'reusables/still_in_progress.html')


class PasswordReset(View):
    def post(self, request):
        """To send a jsonresponse back saying, email have been set and on any error, send maybe status 500"""
        try:
            #create a ticket for user if user exist
            fetched_email = request.POST["email"]
            validate_email(fetched_email)
            user_email = get_user_model().objects.filter(email__iexact = fetched_email).first()
            if user_email:
                """Valid user, prepae token"""
                token = "".join(random.sample("123456789abcdefghijklmnopqrsuvwxyzABCDEFGHIJKLMNOPRSTUVWXYZ", Static.token_lenght()))
                save_token_to_sb = PasswordResetToken.objects.create(user = user_email, token  = token)
                save_token_to_sb.save()
                send_light_email(
                    to_email=fetched_email,
                    endpoint=reverse('origin_password_reset_validate',
                    kwargs={'email' : user_email, 'token': token}),
                    expiry=Static.token_expiry_time(),
                    username=user_email)      
                return JsonResponse({'message': 'Request received, If email exist in our database you will receive a reset link within the next few seconds, refresh page to resend get a new link - old user'}, status = 200)
            #no user found
            return JsonResponse({'message': 'Request received, If email exist in our database you will receive a reset link -new user'})
        except ResendError:return JsonResponse({'message': 'Oops, you dont seem to have internet connection, please try again when you are connected. -Refresh page to resend link'})
        except ValidationError as e: return JsonResponse({"message" : "Invalid Email, Refresh page to try again"})
        except Exception as e:
            logger.error(msg=f"user {fetched_email} tried to reset password and eperience error  : {e}")
            return JsonResponse({"message" : "Please refresh page and retry again but if message persiste, contact customer support as we might be experiencing internal issue"})
            
    def get(self, view):
        """To show user the password reset link """
        return render(self.request, 'html/password_reset.html')

class PasswordValidate(View):
    """after the user have click the link and input their new password and confirm the email on their account , password will be reset here"""
    def get(self, request, email, token):
        return render(request, 'html/final_step_of_password_reset.html', {'expiry_seconds': Static.token_expiry_time})
    
    def post(self, request, email, token):
        #check if the data still exist in the db
        token_still_valid_in_db = PasswordResetToken.objects.filter(user__email__iexact = email, token = token).first()
        #validate token still exist
        if token_still_valid_in_db is None:
            messages.error(request, message="This token have been invalidated. This might happen if the url have been used before OR your account does not exist.")
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
            messages.info(request, message="Password Reset Successfully")
            return redirect('origin_login')

        return JsonResponse({'user': email, 'token' : token, 'still_valid' : token_still_valid_in_db is not None, 'token_have_not_expired': token_have_not_expired, 'password1' : request.POST['password1']}, safe=False)

class UserDashBoard(LoginRequiredMixin, View):
    login_url = "/v1/login/"
    def get(self, request, username):
        try:
            username_on_user = request.user.username
            return JsonResponse({
                'username on account'  :username_on_user,
                'username from url' : username,
                'user_type' : str(request.user)
            })
        except: return {'user type' : 'anonymous'}