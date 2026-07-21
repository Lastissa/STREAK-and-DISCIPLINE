from django.shortcuts import render, resolve_url, redirect
from django.http import HttpResponse, JsonResponse, Http404
from django.views import View
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse

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
        return JsonResponse({'user' : str(request.user), **request.POST}, safe=False)

    
class Login(View):
    """login dashbaord"""
    def get(self, request):
        return render(request, 'html/login.html')
    
    def post(self,request):
        return JsonResponse({'user_email' : str(request.user), **request.POST}, safe=False)

class Reports(View):
    def get(self, request):
        return render(request, 'html/demo_weekly_report.html')

class Dashboard(View, LoginRequiredMixin):
    pass

class Onboarding(View):
    def get(self, request):
        return render(request, 'html/onboarding.html') 
    
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
        create_account = request.GET.get("create_account", "default")
        if create_account:
            """proceed to create account"""
            user = get_user_model().objects.create_user(
                username= request.POST.get('username').upper(),
                email = request.POST.get('email').upper(),
                password= request.POST.get('password1').upper()
            )
            print(user)
        try:return render(request, 'reusables/redirect_url.html', {'redirect_path': reverse(raw_url)})
        except:return JsonResponse(
            {"message" : reverse(raw_url), "status" : "error"},
            status = 404        )
    
    def get(self, request, raw_url):
        try:return redirect(raw_url)
        except:raise Http404 
        
