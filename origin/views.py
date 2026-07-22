from django.shortcuts import render, resolve_url, redirect, reverse
from django.http import HttpResponse, JsonResponse, Http404
from django.views import View
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError

from utility.config import *

import logging
logger = logging.getLogger(__name__)

class OriginHome(View):
    def get(self, request):
        messages.info(request, message=intro_word()[0])
        messages.info(request, message= intro_word()[1])
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
    def get(self, request):
        return render(request, 'html/login.html', {'url_for_form' : reverse('origin_redirect_handler', kwargs={'raw_url' : 'origin_login'})})
    
    def post(self,request):
        return JsonResponse({'user_email' : str(request.user), **request.POST}, safe=False)

class Reports(View):
    def get(self, request):
        return render(request, 'html/demo_weekly_report.html')

class Dashboard(LoginRequiredMixin, View):
    pass


class Onboarding(LoginRequiredMixin, View):
    login_url = '/v1/login/'
    def get(self, request):
        return render(request, 'html/onboarding.html', {'where_to_go_full_url' : reverse('origin_dashboard', kwargs={"username" : request.user.username})})
    
class SearchFriend(View):
    def get(self, request):pass
    def get(self, request): 
        uuid = request.POST.get('uuid', None) #user id to look up - look up for user once this is seen
        
class AddFriend(View):
    def get(self, request):pass
    def get(self, request): 
        uuid = request.POST.get('uuid', None) #user id to look up - look up for user once this is seen
        
        
        
class RedirectHandler(View):
    def post(self, request, raw_url):
        if request.GET.get('login_account'):
            """Proceed to login user and create session"""
            try:
                user_istance = authenticate(request=request, email = request.POST["email"], password = request.POST["password"])
                logger.info(msg= user_istance)
                if user_istance:
                    #user found, create a session and direct onboarding if last_login is null
                    login(request=request, user=user_istance, backend='django.contrib.auth.backends.ModelBackend')  #i currently have three login style set up, hence why i need to specify which i wan to use
                    if user_istance.last_login: return redirect('origin_onboarding')
                    else: return redirect('origin_dashboard', username = user_istance.username)
                    
                else:
                    #no valid credentials, logout any existing session and return back to login
                    logout(request)
                    messages.info( request=request,message="Invalid credentials")
                    return redirect('origin_login')
                
                return JsonResponse({"d": str(user_istance), "password": request.POST["password"]}) 
            
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
        try:return redirect(raw_url)
        except:raise Http404 
        

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
        except:
            return {
                'user type' : 'anonymous'
            }