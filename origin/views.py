from django.shortcuts import render
from django.http import HttpResponse
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from utility.config import *

import logging
logger = logging.getLogger(__name__)

class OriginHome(View):
    def get(self, request):
        messages.info(request, message='"He who conquers himself conquers all" - Opeyemi')
        messages.info(request, message= "if 'He' can do it, you can do it too")
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
        messages.info(request, message="NB: Its important to agree to term and policy before create account button will be active, kindly go through before checking button")
        return render(request, 'html/signup.html')

    
class Login(View):
    """login dashbaord"""
    def get(self, request):
        return render(request, 'html/login.html')

class Reports(View):
    def get(self, request):
        return render(request, 'html/demo_weekly_report.html')

class Dashboard(View):
    pass
