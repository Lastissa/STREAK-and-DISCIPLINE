"""THIS VIEW HANDLES ANYTHING AUTHENTICATION AND SECURITY"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.db import transaction
from ..models import Profile, Commitment, ChoicesValidatorInModels, PasswordResetToken
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as V_Error
from django.shortcuts import redirect, render
from resend.exceptions import ResendError, ValidationError
from django.http import JsonResponse
from django.utils import timezone

from utility.email_sending import send_password_reset_email, send_password_reset_successful_email
from utility.config import Static
from .utility_view import helper_with_friendship_request_answer
import json, random, logging

logger= logging.getLogger(__name__)




#this handle save user""" data during onboarding
class DbSave(LoginRequiredMixin,View):
    """WHERE ONBOARDING PAGE SEND ITS DATA TO FOR VERIFICATION"""
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
                helper = helper_with_friendship_request_answer(request=request, to_user_id =social_friend_user_id.strip())
                #so the issue can be returned succesdully
                if helper is not None: return helper
                
        return JsonResponse({'message' : 'success'}, status = 200)

class PasswordReset(View):
    def post(self, request):
        """To send a jsonresponse for the password reset pageback saying, email have been sentbut if user is inactive, tell them account is active and ask them to reactivate accountt first and on any error, send maybe status 500"""
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
            logger.error(msg=f"user tried to reset password and eperience error  : {e}")
            return JsonResponse({"message" : "Please refresh page and retry again but if message persiste, contact customer support as we might be experiencing internal issue"}, status = 500)
       
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
        

class AccountDeactivated(View):
    def get(self, request, email, days_left):
        return render(request, 'html/reactivate_page.html', {
                'email': email,
                'days_left': int(days_left),
                'days_until_deletion': 7- int(days_left)
            })
        
class ReactivateAccountJson(View):
    """Handle the reactivation pf user isactive is false account by sending json back and that json determine wherre teh user is refirected to"""
    def post(self, request):
        try:
            #first check if the account is truly deactivated or exist
            data = json.loads(request.body).get('email', None)
            validate_email(data)
            if data is None : return JsonResponse({'message'}, status = 500)
            istance = get_user_model().objects.filter(email__iexact = data).first()
            if istance is None:
                return JsonResponse({'message': 'Invalid credentials'}, status = 400)   #watch for the s
            if istance.is_active != False:
                return JsonResponse({'message': 'Invalid credential'}, status =  400)
            
            #if user is truly deactivated, update
            istance.is_active = True
            istance.last_is_active_false_date = None
            istance.save()
        except V_Error as e: return JsonResponse({'message': 'please go to our official website'}, status = 404)
        except Exception as e: return JsonResponse({'message': 'error'}, status = 404)
        
        return JsonResponse({'message': 'success'}, status = 200)
        