from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as V_Error
from django.contrib import messages
from django.shortcuts import redirect, render
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin

from ..models import StaffTempToken, News
from utility.config import Static
from utility.email_sending import send_staff_access_code_email
from utility.file_upload import upload_news_banner

import json, random, logging

logger = logging.getLogger(__name__)


class StaffSignup(View):
    def get(self, request):
        messages.info(request=request, message="Staff accounts require an access code from an admin before you can sign up.")
        return render(request, 'html/staff_signup.html')


class StaffMakeTokenRequest(View):
    """INCHARGE OF SENDING EMAIL TO THE OFFICIAL GMAIL WITH TOKEN FOR STAFF TO VERIFY THEM BEFORE ACCOUNT CREATION CAN START"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            email = (data.get('email') or '').strip()
            username = (data.get('username') or '').strip()

            validate_email(email)
            if not username:
                return JsonResponse({'message': 'Please choose a username before requesting a code.'}, status=400)

            # block requesting a code for an email that already has an account and is a staff
            if get_user_model().objects.filter(email__iexact=email, is_staff = True).exists():
                return JsonResponse({'message': 'You are not allowed to create account staff, contact admin for necessary actions -old user '}, status=409)

            # simple rate limit so one person can't spam the official inbox with requests
            rate_key = f"staff_token_request_{email.upper()}"
            if cache.get(rate_key):
                return JsonResponse({'message': 'A code was already requested for this email a moment ago. Please wait a minute and try again.'}, status=429)
            cache.set(rate_key, True, timeout=60)

            # build a fresh token, always prefixed 'st-' for staff (admin tokens, if ever
            # issued directly in the db/admin, use 'ad-' — see StaffTempToken.type)
            raw_token = "".join(random.sample("123456789abcdefghijklmnopqrsuvwxyzABCDEFGHIJKLMNOPRSTUVWXYZ", Static.token_lenght()))
            token = f"st-{raw_token}"

            # any previous unclaimed request for this exact email is now stale, replace it
            StaffTempToken.objects.filter(email__iexact=email, type='staff').delete()
            StaffTempToken.objects.create(email=email, token=token, type='staff')

            # synchronous on purpose: if this fails we want to tell the requester right away
            # rather than have them wait on a code that never arrived
            send_staff_access_code_email(token=token, requester_email=email)

            return JsonResponse({
                'message': f"Request received. An access code has been sent to our official inbox — an admin will share it with you personally. Codes expire after {int(Static.token_expiry_time() / 60)} minutes."
            }, status=200)

        except V_Error:
            return JsonResponse({'message': 'Please enter a valid email address.'}, status=400)
        except Exception as e:
            logger.error(msg=f"staff token request failed: {e}")
            return JsonResponse({'message': 'Something went wrong requesting your access code. Please refresh and try again.'}, status=500)


class VerifyStaffTokenAndCreateAccount(View):
    """INCHARGE OF VERIFYING THE TOKEN STAFF BOUGHT AND VERIFY IT AGAINT BOTH THEIR STAFF TYPE AND TABLE"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            email = (data.get('email') or '').strip()
            username = (data.get('username') or '').strip()
            password1 = data.get('password1') or ''
            password2 = data.get('password2') or ''
            token = (data.get('token') or '').strip()

            validate_email(email)
            if not username:
                return JsonResponse({'message': 'Username is required.'}, status=400)
            if not token:
                return JsonResponse({'message': 'Please enter the access code an admin gave you.'}, status=400)
            if len(password1) < 8:
                return JsonResponse({'message': 'Password must be at least 8 characters.'}, status=400)
            if password1 != password2:
                return JsonResponse({'message': 'Passwords do not match.'}, status=400)

            # if get_user_model().objects.filter(email__iexact=email).exists():
            #     return JsonResponse({'message': 'An account with this email already exists. Please login instead.'}, status=409)

            token_istance = StaffTempToken.objects.filter(email__iexact=email, token=token, type='staff').first()
            if token_istance is None:
                return JsonResponse({'message': 'Invalid access code. Please recheck the code with an admin or request a new one.'}, status=400)

            token_expired = (timezone.now() - token_istance.time_sent).total_seconds() >= Static.token_expiry_time()
            if token_expired:
                token_istance.delete()
                return JsonResponse({'message': f"This access code has expired ({int(Static.token_expiry_time() / 60)} minute limit). Please request a new one."}, status=400)

            with transaction.atomic():
                # CustomManager.create_user() intentionally skips the initial save() when
                # 'is_staff' is passed in, the same way create_superuser() does — so we save
                # it ourselves right after.
                user = get_user_model().objects.create_user(email=email, username=username, password=password1, is_staff=True)
                user.save()
                token_istance.delete()

            logger.warning(msg=f"staff account created for {email}")
            messages.info(request, message = "Staff Account Created, You Have Been Redirected To Login.")
            return JsonResponse({'message': 'success'}, status=200)

        except V_Error:
            return JsonResponse({'message': 'Please enter a valid email address.'}, status=400)
        except Exception as e:
            logger.error(msg=f"staff account verification failed: {e}")
            return JsonResponse({'message': 'Something went wrong creating your account. Please try again.'}, status=500)


class AccountWithStaffStatus(View):
    """ON REGULAR LOGIN , THIS WILL TRY TO DECTECT THE STATUS OF THE USER , IF STAFF OR SUPERUSER DECTECTED? BEFORE GOING TO ONBOARDING OR DASHBOARD, THIS ONE IS LIKE THE MIDDLEMAN THAT DECTECS IF USER IS STAFF AND TRY TO REDIRECT THEM TO admin colsole BUT IT ASK FIRST? YOU ARE A STAFF MEMBER? DO YOU WANT TO CONTINUE HERE OR WANT TO BEREDIRETED TO THE ADMIN CONSOLE?"""
    def get(self, request):
        STAFF_TOOLS = [
            {
                'title': 'Blog & News',
                'description': 'Publish, edit and manage the News posts shown on the public Blog & Updates page.',
                'icon': 'fa-newspaper',
                'url_name': 'origin_blog',
                'status': 'live',
            },
            # ---------------------------------------------------------------
            # ADD FUTURE STAFF TOOLS HERE, following the exact shape above.
            # Leave 'status': 'soon' and 'url_name': None until the tool's
            # view + url actually exist, then flip it to 'live' and add the
            # real url_name once it's ready to use.
            #
            # Example:
            # {
            #     'title': 'User Management',
            #     'description': 'Search, deactivate or reset staff and user accounts.',
            #     'icon': 'fa-users-gear',
            #     'url_name': None,
            #     'status': 'soon',
            # },
            # ---------------------------------------------------------------
        ]
        if not (request.user.is_staff or request.user.is_superuser):
                    return redirect('origin_dashboard')
        
        tools = []
        for tool in STAFF_TOOLS:
            entry = dict(tool)
            entry['url'] = reverse(tool['url_name']) if entry.get('status') == 'live' and tool.get('url_name') else None
            tools.append(entry)
        
        print(request.COOKIES.get('sd-theme', ''))
        if request.user.is_staff: return render(request, 'html/staff_hub.html', {'staff_tools': tools, 'page_theme': request.COOKIES.get('sd-theme', '')})
        messages.error(request, message="YOU ARE NEVER SUPPOSE TO  SEE THIS BUT IF SEEN , AN ALSO BIG MAX REDIRECT ERROR WAS ABOUT TO HAPPE BUT I CAUGJHT IT HERE")
        return render(request, 'html/full_error_message.html')


class CreateBlog(View):
    """For staff to create news, i can still use the admin but who knows , i might grow and need more hand"""
    def post(self, request):
        data = request.POST
        image = request.FILES
        banner = request.FILES.get('banner')
        if not request.user.is_staff: return JsonResponse({'message': 'Permission Denied'}, status = 403)
        
        # print([i for i in image.keys()], [i for i in data.keys()])
        try:
            with transaction.atomic():
                news_ist = News.objects.create(
                    title = data['title'],
                    tag = data['tag'],
                    excerpt = data['excerpt'],
                    read_time = data['read_time'],
                    featured = data['featured'].upper() == "True",
                    actual_content = data['actual_content']
                )
                
                if banner:
                    
                    output = upload_news_banner(uploaded_file= banner, id = news_ist.id)
                    news_ist.banner = output['url']
                    news_ist.full_clean()
                    news_ist.save()
                    return JsonResponse({'message': 'Uplaod sucess with banner'}, status = 200)
                else:
                    news_ist.banner = None
                    news_ist.full_clean()
                    news_ist.save()
                    return JsonResponse({'message': 'Uplaod sucess without banner'}, status = 200)
                    
        except Exception as e: 
            logger.error(msg=f"Staff news uplaoad failed with STACKTRACE: {e}")
            print(str(e))
            return JsonResponse({'message': 'Server Error'}, status = 503)
        
        return JsonResponse({'message': 'er'}, status = 500)
    
    
class StaffView(LoginRequiredMixin, View):
    pass