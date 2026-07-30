"""THIS VIEW HANDLES OTHER VIEW THAT DONT REALLY HAVE A FUNCITON BUT TO BE A MIDDLE MAN LIKE THE REDIRECT VIEW"""

from django.views import View
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.core.cache import cache
from django.contrib import messages
from django.shortcuts import redirect
from django.shortcuts import render, reverse
from django.http import JsonResponse
from django.db import IntegrityError

from ..models import ChoicesValidatorInModels

import logging
logger = logging.getLogger(__name__)

class RedirectHandler(View):
    """handling redirect from one page to another"""
    def post(self, request, raw_url):
        if request.GET.get('login_account'):
            """Proceed to login user and create session"""
            try:
                user_exist = get_user_model().objects.filter(email__iexact = request.POST["email"]).first() is not None
                user_istance = authenticate(request=request, email = request.POST["email"].upper(), password = request.POST["password"])
                logger.info(msg= user_istance)
                if user_istance or user_exist:
                    #set a key in cache to rate limit after 3 attempt
                    the_key = f"attemp_login_{request.POST["email"]}".upper()
                    rate_limit = cache.get(the_key) if cache.get(the_key) is not None else ""
                    if len(rate_limit)  <2:
                        messages.info( request=request,message= f"Incorrect password or Email.")
                        cache.set(the_key, rate_limit+"x", timeout=120)
                    elif len(rate_limit) == 2:
                        messages.warning( request=request,message= f"Incorrect password or Email., one more fail attempt will lock you out. ")
                        cache.set(the_key, rate_limit+"x", timeout=120)
                    else:
                        messages.error( request=request,message=f"Too many attempts. Please wait 2 minutes before trying again. If you try again before the time is up, the wait period will reset.---{rate_limit}")
                        cache.set(the_key, "banned", timeout=120)
                        return redirect('origin_login')
                    
                    #user found but user password is wrong
                    if not user_istance:
                        logout(request)
                        return redirect('origin_login') 
                        
                    #user found, create a session and direct onboarding to handle wether it should direct user to dashboard or stay
                    login(request=request, user=user_istance, backend='django.contrib.auth.backends.ModelBackend')  #i currently have three login style set up, hence why i need to specify which i wan to use
                    request.session.save() #i had a race condtioning issue bcos the next page(onboarding uses the seesion as soon as it comes) and the redirect url was not havig enough time to store the db and BOOM , site crash ----This fix cos it mean the request must be saved before user is allowto go
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
                """create user fail, switch to login istead,"""
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
    