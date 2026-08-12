#THIS VIEW RETURNS ONLY JSON AND IT INCLUDE OPERATION WNHERE ONLY JSON IS REQUIRED

from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache

from django.db import IntegrityError, transaction
from origin.views.utility_view import helper_with_friendship_request_answer
from utility.config import Static
from ..models import Commitment, Entries, Profile, ChoicesValidatorInModels, Friendship
from django.shortcuts import reverse
from django.http import JsonResponse, request
from django.utils import timezone


from django.db import models
import json
import logging

from utility.file_upload import *
from utility.email_sending import send_partner_request_accepted_email

logger = logging.getLogger(__name__)

class CommitmentData(LoginRequiredMixin, View):
    """RETURNS DATA FOR THE DASHBOARD HOME AND THE DASHBOARD COMMITMENT PAGE USE TO DISPLAY A QUICK VIEW OF USER COMMITMENTS WITH THE LINK THAT REDIRECT USER TO VIEW ACTUAL FULL DATA"""
    def get(self, request):
        commitment_istance = Commitment.objects.filter(user = request.user, is_active=True).all() #is_active=True only - deleted/completed commitments must never surface back to the user, see EachCommitmentArchive
        if not commitment_istance.exists(): 
            data = []
            stats = {'consistency_pct': 0}
        else:
            data = [
            {
                'id' : i.pk,
                'url' : reverse('origin_each_commitment_view', kwargs={'commitment_key' : i.pk}),
                "what": i.what,
                "category": i.category,
                "streak_count": i.streak_count,
                "goal_days": i.goal_days,
                "days_since_start": (timezone.now().date() - i.created_at.date()).days,
                "checkin_time": i.checkin_time,
                'is_active': i.is_active,
                "checked_in_today": (i.last_check_in is not None and i.last_check_in.date().day == timezone.now().date().day),                
            }
            for i in commitment_istance 
            ]
            consistency_pct = [0 for i in commitment_istance if i.streak_count > 0]    #Find the amount of streak score > 0 / total commitment (i use the tenchique of all ocnsistncy must have a streak score but are they all greater than zero?) ; that give the consistency_cpt
            c_pct = (consistency_pct.count(0)/len(commitment_istance))*100
            stats = {'consistency_pct': c_pct}      #commitment page inside the dashboard commitment need this
        return JsonResponse({'commitments' : data, 'stats': stats}, status = 200)


class HeatMap(LoginRequiredMixin, View):
    """RETURNS DATA THAT THE DASHBOARD HOME USES TO GIVE USER LAST 30 DAYS OVERALL VISUAL HEAT MAP"""
    # WHAT THE UI EXPECTS
    #     {
    #   "message": "ok",
    #   "cells": [
    #     { "date": "2025-06-28", "count": 0 },
    #     { "date": "2025-06-29", "count": 1 },
    #     { "date": "2025-06-30", "count": 2 },
    #     { "date": "2025-07-01", "count": 3 }
    #   ],
    #   "checked_in_today": 2,
    #   "total_active": 3
# }
    def get(self, request):
        today = timezone.now().date()
        start_date = today - timezone.timedelta(days=29)  # 30 days including today
         # Get all entries for the user's commitments in the last 30 days
        entries = Entries.objects.filter(
                    commitment_key__user=request.user,
                    commit_at__gte=start_date,
                    commit_at__lte=today
                    ).order_by('commit_at')
        
        #check if the entries is empty
        if not entries.exists(): return JsonResponse({
            'message' : 'YOU dont have any entries, create commitment and check in to view entries last 30 days grid summary'.upper(),
            'cells' : []},status = 403)
        #if entries are NOT empty
        total_active = Commitment.objects.filter(user=request.user, is_active=True).count()     #total amount of active commitments
        checked_in_today = 0                                                                    #This keep track of totak check in today
        cells_ui_need = []                                                                      #My current daskboard need this
        
        for entry in entries:
            cells_ui_need.append({
                'date': str(entry.commit_at),
                'count': 1,  # one entry = one cell
            })
            if entry.commit_at == today:
                checked_in_today += 1
        # Pad cells to always be 30
        padded_cells = []
        for i in range(30):
            day = start_date + timezone.timedelta(days=i)
            # Check if we have an entry for this day
            count = 0
            for cell in cells_ui_need:
                if cell['date'] == str(day):
                    count += 1
            padded_cells.append({
                'date': str(day),
                'count': count,
            })
        return JsonResponse({
            'message' : 'success',
            'cells' : padded_cells,
            'total_active': total_active,
            'checked_in_today' : checked_in_today,
            })



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

        # Get all active commitments for ALL partners in one query
        all_commitments = Commitment.objects.filter(
            user_id__in=partner_users,
            is_active=True
        ).all()

        # Get the most recent entry per partner (one query, ordered newest first)
        all_entries = Entries.objects.filter(
            commitment_key__user_id__in=partner_users
        ).select_related('commitment_key').order_by('-commit_at').all()

        # Group commitments by user - keep both the raw streak numbers AND the best
        # (max) streak, since the dashboard card shows a single "X days" number per
        # partner but we still want the per-commitment detail available if needed later
        commitments_by_user = {}
        for i in all_commitments:
            uid = i.user_id
            commitments_by_user.setdefault(uid, []).append({'what': i.what, 'streak_count': i.streak_count})

        # Group last active by user - entries are ordered newest-first above, so the
        # first entry we see per user IS their most recent check-in (this used to be
        # ordered oldest-first, which meant "last active" was actually showing the
        # OLDEST entry - fixed here)
        last_active_by_user = {}
        for e in all_entries:
            uid = e.commitment_key.user_id  # was e.commitment.user_id (Entries has no "commitment" field, only "commitment_key") - crashed this entire endpoint any time a partner had logged entries
            if uid not in last_active_by_user:
                last_active_by_user[uid] = e.commit_at

        #Build the partner list
        partners = []
        for f in partner_istance:
            partner_uid = f.from_user_id
            partner_profile = Profile.objects.filter(user_id=partner_uid).first()
            public_id = partner_profile.public_searchable_username if partner_profile else 'unknown'
            partner_commitments = commitments_by_user.get(partner_uid, [])
            best_streak = max((c['streak_count'] for c in partner_commitments), default=0)

            partners.append({
                'public_id': public_id,
                'streak_count': best_streak,             # single number - what the dashboard card renders as "X days" (was previously a raw list, e.g. "1,4,7 days")
                'commitments': partner_commitments,       # full per-commitment breakdown, for anywhere that wants more detail than the headline number
                'last_active': last_active_by_user.get(partner_uid).isoformat() if partner_uid in last_active_by_user else None,
            })

        return JsonResponse({
            'message': 'success',
            'partners': partners,
        })
    
    
class DashboardJson(LoginRequiredMixin, View):
    login_url = '/v1/login/'
    """RETURN THE JSON FORMAT OF USER DATA BY JUST DOING /JSON ON THEIR DASHBOARD"""
    def get(self, request):
        profile_istance = Profile.objects.filter(user = request.user).first()
        Commitment_istance = Commitment.objects.filter(user = request.user).all()
        all_friendships = Friendship.objects.filter(
            models.Q(from_user=request.user) | models.Q(to_user=request.user)  # Q handles OR
        ).select_related('from_user', 'to_user').all()                         #JOIN handles eager loading(selected from), istead for loop that lead to N+1q
        
        partner_request_received = [i for i in all_friendships if i.to_user == request.user]
        friend_request_sent = [i for i in all_friendships if i.from_user == request.user]
        
        if partner_request_received is None: partner_list_received = []
        else: partner_list_received = [{
                            'from_user': f.from_user.email,
                            'to_user': f.to_user.email,
                            'status': f.status,
                            'created_at': f.created_at.isoformat(),
                            'updated_at' : f.updated_at.isoformat()
                        }
                        for f in partner_request_received] 
        if friend_request_sent is None: partner_list_sent = []
        else: partner_list_sent = [{
                                    'from_user': f.from_user.email,
                                    'to_user': f.to_user.email,
                                    'status': f.status,
                                    'created_at': f.created_at.isoformat(),
                                    'updated_at' : f.updated_at.isoformat()
                                }
                                for f in friend_request_sent] 
        
        return JsonResponse({
            'username' : request.user.username,
            'email' : request.user.email,
            'last_login' : request.user.last_login,
            'join_date' : request.user.date_joined,
            'user_id' : profile_istance.public_searchable_username,
            'profile_istance' : {
                        'tier': profile_istance.tier,
                        'public_searchable_username': profile_istance.public_searchable_username,
                        'leaderboard_optin': profile_istance.leaderboard_optin,
                        'streak_count_is_public_visible': profile_istance.streak_count_is_public_visible,
                        'ai_insight_active': profile_istance.ai_insight_active,
                        'receive_newsletter': profile_istance.receive_newsletter,
                        'theme': profile_istance.theme,
                        'weekly_report_email_active': profile_istance.weekly_report_email_active,
                        'custom_report_email_active': profile_istance.custom_report_email_active,
                        'social_mode': profile_istance.social_mode,
                        'zeal_score': profile_istance.zeal_score,
},
            'commitment' : [{
                            'what': c.what,
                            'category': c.category,
                            'why': c.why,
                            'goal_days': c.goal_days,
                            'streak_count': c.streak_count,
                            } for c in Commitment_istance],
            'friend_request_received' : partner_list_received,
            'friend_request_sent' : partner_list_sent
            }, safe=False)



class SearchFriend(LoginRequiredMixin,View):
    #This one is specifically only for logged in user
    login_url = '/v1/login/'
    def get(self, request): return self.post(request)
    def post(self, request):
        data = request.POST['uuid']
        friend_search = Profile.objects.filter(public_searchable_username__iexact = data).first()
        if friend_search:
            userid = friend_search.public_searchable_username
            username = friend_search.user.username
            profile_image = str(friend_search.profile_img_url)
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
    """This is for sending a freidn request to the user, maybe i will extend the code to make it hanlde accepting and rejectig and unresending with query params but by default it will send a fresh request"""
    login_url = '/v1/login'
    def get(self, request):return self.post(request)
    def post(self, request):
        incoming_user_id = request.POST['userid']
        req = helper_with_friendship_request_answer(request=request, to_user_id = incoming_user_id.strip())
        if req is None: return JsonResponse({'message': 'success, requst resend successfuly'}, status = 200)
        else: return req
        
        
    

class RelationshipSent(LoginRequiredMixin, View):
    """FOr getting user SENT friend / partner request to others with status like pending, accepted and rejected"""
    login_url = '/v1/login/'
    def get(self, request, status):
        options = ChoicesValidatorInModels().friendship_status
        #incase the status is not pending, accepted or rejected
        if status not in options: return JsonResponse({'message': 'Unknown request, please contact customer support'}, status= 404)
        
        limit = int(float(request.GET.get('limit', '10')))
        after_id = int(float(request.GET.get('after_id', '0'))) #if its null, it simply mean the user is on the first request
        start_fetch = limit*(after_id)                          #The begining of the pagination
        end_fetch = limit*(after_id+1)                          #the end of the pagination
        
        if limit>20: limit  = 20  #max should be 20 to avoid spammers issue
        # logger.info(msg= f"Pagination in relationship for SENT with start = {start_fetch} and end  = {end_fetch}")
        friend_istance = Friendship.objects.filter(from_user = request.user, status__iexact= status).select_related('to_user')[start_fetch: end_fetch]
        
        results = [
            {
                'userid': Profile.objects.filter(user = i.to_user).first().public_searchable_username if Profile.objects.filter(user = i.to_user).first() else "NONE",
                'username': i.to_user.username,
                'profile_image': '',
                'updated_at': i.updated_at
            }
            for i in friend_istance
        ]
        return JsonResponse({
            'results': results,             #the output per wach pagination
            'next_id': after_id+1           #Increasing the pagination number for the client side
            }, status = 200)


class RelationshipReceived(LoginRequiredMixin, View):
    """FOr getting user RECEIVED friend / partner request FROM others with status like pending, accepted and rejected"""
    login_url = '/v1/login/'
    def get(self, request, status):
        options = ChoicesValidatorInModels().friendship_status
        #incase the status is not pending, accepted or rejected
        if status not in options: return JsonResponse({'message': 'Unknown request, please write am properly'}, status= 404)
        
        limit = int(float(request.GET.get('limit', '10')))
        after_id = int(float(request.GET.get('after_id', '0'))) #if its null, it simply mean the user is on the first request
        start_fetch = limit*(after_id)                          #The begining of the pagination
        end_fetch = limit*(after_id+1)                          #the end of the pagination
        
        if limit>20: limit  = 20  #max should be 20 to avoid spammers issue
        logger.info(msg= f"Pagination in relationship for RECEIVED with start = {start_fetch} and end  = {end_fetch}")
        friend_istance = Friendship.objects.filter(to_user = request.user, status__iexact= status).select_related('to_user')[start_fetch: end_fetch]
        #i dont want to make another call for each friend_istance to get reciever profile so i wil just recreate the formula again which is username + CustomUser pk
        results = [
            {
                'userid': Profile.objects.filter(user = i.from_user).first().public_searchable_username if Profile.objects.filter(user = i.from_user).first() else "NONE",
                'username': i.from_user.username,
                'profile_image': '',
                'updated_at': i.updated_at
            }
            for i in friend_istance
        ]
        return JsonResponse({
            'results': results,             #the output per wach pagination
            'next_id': after_id+1           #Increasing the pagination number for the client side
            }, status = 200)

class RelationshipUnpair(LoginRequiredMixin, View):
    """Remove a partner from accepted list of current usr friends"""
    def curb_repetition(self, request, user_to_unpair):
        """GET and POST have the same code so i use this to curb it"""
        if not user_to_unpair:  return JsonResponse({'message': 'No user specified.'}, status=400)
        # Find the partner's profile
        partner_profile = Profile.objects.filter(public_searchable_username__iexact=user_to_unpair).first()
        if not partner_profile:return JsonResponse({'message': 'User not found.'}, status=400)
        
        partner_user = partner_profile.user
        
        # Find the accepted friendship between these two users
        friendship = Friendship.objects.filter(
            models.Q(from_user=request.user, to_user=partner_user) |
            models.Q(from_user=partner_user, to_user=request.user),
            status='accepted'
        ).first()
        
        if not friendship:return JsonResponse({'message': 'No active partnership found with this user.'}, status=404)
        
        # Update status to rejected
        friendship.status = 'rejected'
        friendship.save() 
        
        return JsonResponse({
            'message': f'Successfully unpaired with @{user_to_unpair}. Refresh to view changes',
        }, status=200)
        
        
    def get(self, request):
        user_to_unpair = request.GET.get('userid', '').strip()
        return self.curb_repetition(request, user_to_unpair)
        
    def post(self, request):
        user_to_unpair = json.loads(request.body).get('userid', '').strip()
        return self.curb_repetition(request, user_to_unpair)
        


class RelationshipAcccept(LoginRequiredMixin, View):
    """This handle accepting partner request SENT to user if user want to accept"""
    def get(self, request):
            user_to_pair = request.GET.get('userid', '').strip()
            
            if not user_to_pair:
                return JsonResponse({'message': 'No user specified.'}, status=400)
            
            
            # Find the partner's profile
            partner_profile = Profile.objects.filter(
                public_searchable_username__iexact=user_to_pair
            ).first()
            
            if not partner_profile:
                return JsonResponse({'message': 'User not found.'}, status=404)
            
            partner_user = partner_profile.user
            
            # make sure the current state is pending
            friendship = Friendship.objects.filter(
                models.Q(from_user=partner_user, to_user=request.user),
                status='pending'
            ).first()
            
            if not friendship:
                return JsonResponse({'message': 'No active friend request from this user.'}, status=404)
            
            #send notification email
            send_partner_request_accepted_email(to_email=partner_user.email, sender_username=partner_user.username, accepter_userid= Profile.objects.get(user = request.user).public_searchable_username, accepter_username=request.user.username)
            # Update status to accepted as per there was an active friend request
            friendship.status = 'accepted'
            friendship.save()
            #notifier the sender that their request have been accepted
            # print(
            #     {'to_email': partner_user.email,
            #      'sender_username': partner_user.username,
            #      'accepter_userid': Profile.objects.get(user = request.user).public_searchable_username
            #      }
            # )
            return JsonResponse({
                'message': f'Successfully accepetd the friend request',
            }, status=200)
        

class RelationshipDecline(LoginRequiredMixin, View):
    """This handle DECLINING partner request SENT to user if user want to decline"""
    def get(self, request):
            user_to_unpair = request.GET.get('userid', '').strip()
            
            if not user_to_unpair:
                return JsonResponse({'message': 'No user specified.'}, status=400)
            
            
            # Find the partner's profile
            partner_profile = Profile.objects.filter(
                public_searchable_username__iexact=user_to_unpair
            ).first()
            
            if not partner_profile:
                return JsonResponse({'message': 'User not found.'}, status=404)
            
            partner_user = partner_profile.user
            
            # make sure the current state is pending
            friendship = Friendship.objects.filter(
                models.Q(from_user=request.user, to_user=partner_user) |
                models.Q(from_user=partner_user, to_user=request.user),
                status='pending'
            ).first()
            
            if not friendship:
                return JsonResponse({'message': 'No active friend request from this user.'}, status=404)
            
            # Update status to accepted as per there was na active friend request
            friendship.status = 'rejected'
            friendship.save()
            
            return JsonResponse({
                'message': f'Successfully accepetd the friend request',
            }, status=200)
                


class CreateCommitment(LoginRequiredMixin, View):
    """THIS CREATE COMMITMENT BY COLLECTING JSON DATA AND ATTACHING IT TO THE REQUEST.USER IDENTITY"""
    login_url = '/v1/login/'
    def get(self, request): return self.post(request)
    def post(self, request):
        try:
            data = json.loads(request.body)

        except json.JSONDecodeError:return JsonResponse({'message': 'Invalid JSON.'}, status=400)
        # Extract fields
        what = data.get('what', '').strip()
        category = data.get('category', 'other').strip().lower()
        why = data.get('why', '').strip()
        minimum = data.get('minimum', '').strip()
        goal_days = data.get('goal_days', 365)
        checkin_time = data.get('checkin_time', '21:00')
        reminder_enabled = data.get('reminder_enabled', True)
        reminder_time = data.get('reminder_time', '20:30')
        reminder_method = data.get('reminder_method', 'email').strip().lower()
        whatsapp_number = data.get('whatsapp_number', '').strip()
        
        # Validate required fields
        if not what: return JsonResponse({'message': 'Please describe your commitment.'}, status=400)
        if not why:return JsonResponse({'message': 'Please write your reason.'}, status=400)
        
        # Validate reminder_time is provided when reminder is enabled
        if reminder_enabled and not reminder_time: return JsonResponse({'message': 'Reminder time is required when reminders are enabled.'}, status=400)
        
        # Validate whatsapp_number is provided when method is whatsapp
        if reminder_method == 'whatsapp' and not whatsapp_number: return JsonResponse({'message': 'WhatsApp number is required when WhatsApp reminders are selected.'}, status=400)
        
        # Validate category
        validator = ChoicesValidatorInModels()
        if category not in validator.commitment_category:category = 'other'
        
        # Validate reminder method
        if reminder_method not in validator.report_delivery_mode: reminder_method = 'email'
        
        # Clean WhatsApp number — only store if method is whatsapp
        if reminder_method != 'whatsapp': whatsapp_number = ''
        else:
            # Strip spaces, dashes, parentheses
            whatsapp_number = whatsapp_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not whatsapp_number.startswith('+'):
                return JsonResponse({'message': 'invalid watsappp number; +xxxxx.. where x are number are the only allowed'})
                
                
                
        #check if existing commitment exist with the same what for the user
        existing_commitment = Commitment.objects.filter(user=request.user, what__iexact=what).first()
        if existing_commitment:
            return JsonResponse({'message': 'You already have a commitment with the same description. Please choose a different one.'}, status=400)
        
        # Create the commitment
        try:
            commitment = Commitment.objects.create(
                user=request.user,
                what=what,
                category=category,
                why=why,
                minimum_effort=minimum,
                goal_days=goal_days,
                checkin_time=checkin_time,
                reminder_active=reminder_enabled,
                user_selected_reminder_time=reminder_time,
                mode_of_delivery=reminder_method,
                whatsapp_number=whatsapp_number,
            )
            return JsonResponse({
                'message': 'Commitment created successfully!',
                'commitment_id': commitment.pk,
            }, status=201)
            
        except Profile.DoesNotExist:
            return JsonResponse({'message': 'Profile not found. Please complete onboarding first.'}, status=400)
        except Exception as e:
            return JsonResponse({'message': f'Error creating commitment. Please try again.'}, status=500)
        
class CommitmentQuickCheckin(LoginRequiredMixin, View):
    """On days when user is tired but still have to checkin, they jsut press the "Quick checkin" on their account commitment page and the user minimum words is logged"""
    def post(self, request, commitment_key):
        current_commitment_istance = Commitment.objects.filter(user = request.user, pk = commitment_key).first()
        if not current_commitment_istance: return JsonResponse({'message': 'No commitment found with this details'}, status = 400)
        
        #commitment exist, proceed to check and update datas along entries
        last_entry = Entries.objects.filter(commitment_key = commitment_key).last()
        #updating the streak count
        if not last_entry:
            #user have not written anything before so this is their first entry
            streak = 1                         #Set the commitment streak to one as day 1
        elif (timezone.now().date()  - last_entry.commit_at).days == 1:
            # a day at max diff mean the streak should increase
            streak = current_commitment_istance.streak_count + 1
        elif  (timezone.now().date()  - last_entry.commit_at).days == 0:
            #same day? break the code istantly and tell them they have commit
            streak = current_commitment_istance.streak_count
            return JsonResponse({'message': 'You have checked in today'}, status = 400)
        else:
            #the diff between last entry and current entry is more than more day so RESET
            streak = 1
            
        current_commitment_istance.streak_count = streak
        #also update the last check in
        current_commitment_istance.last_check_in = timezone.now()
        current_commitment_istance.save()
        
            

        #user have not checked in today, Create a new entry for them with the mimium data since this is a quick entry not the long one
        content = current_commitment_istance.minimum_effort
        content_count = len(content)
        Entries.objects.create(
            commitment_key = current_commitment_istance,
            content = content,
            word_count = content_count
        )
        return JsonResponse({'message': 'weldone, onto the next one'}, status = 200)
            


class ProfilePicture(LoginRequiredMixin, View):
    """INCHARGE OF ALWAYS BRINNGIN BACK THE URL FOR USER PICTIRE(get) OR UPDATING THE PROFILE PICTURE (post) IN THE DB"""
    def get(self, request):
        """find url from db and return it to clien"""
        istance = Profile.objects.filter(user = request.user).first()
        return JsonResponse({'message': "success", 'url' :str(istance.profile_img_url)}, status = 200)
    
    def post(self, request):
        data = request.FILES
        key = data.get('profile_picture', None)
        if key is None: return JsonResponse({'message': 'please select a picture'}, status= 500)
         #key exist, grab it.
        #check the filesize in bytes
        if key.size >= 5 * 1024 *1024: return JsonResponse({'message': 'Error, file too large'}, status = 400)
        try:    result = upload_profile_picture(user_email=request.user.email, uploaded_file= key.read())
        except Exception as e: 
            return JsonResponse({'message': 'Server Error, Our partner are slow today.'}, status = 500)
        #everyting went successfuly, update the user profile link and done
        istance = Profile.objects.get(user = request.user)
        #check if user is a premium user
        if istance.tier == 'free': return JsonResponse({'message': 'permission denied'}, status = 403)
        istance.profile_img_url = result['url']
        istance.save()
        
        return JsonResponse({'message': 'success'})
        
        
        
        
        
        
        return JsonResponse({'message': f'{key.read()}'}, status = 500)
 
class ProfilePictureRemove(LoginRequiredMixin, View):
    """REMOVE USER PROFILE PICTURE BY DELETING THE DATA FROM CLOUDINARY AND SETTING PROFILE URLFEILD TO EMPTY"""
    def post(self, request):
        try: delete_profile_picture(user_email=request.user.email)
        except Exception as e:
            logger.error(f"user encountered enrror while removing picture : {e}")
            return JsonResponse({'message': 'Error but Not Our Fault'}, status = 500)
        
        #delete was successful, update profile
        istance = Profile.objects.get(user = request.user)
        istance.profile_img_url = ''
        istance.save()
        return JsonResponse({'message': 'deleted successfully'}, status = 200)
    
    
        
class ProfileUpdateUsernameORUserid(LoginRequiredMixin, View):
    """Handles the UPDATE OF THE USER USERNAME, USER_ID VIA JSON POST"""
    def post(self, request):
        data = json.loads(request.body)
        field = data.get('field', None)
        value = data.get('value', None)
        
        #make sure none of the value is none
        if field is None or value is None: return JsonResponse({'message':'invalid request'}, status = 400) 
        
        #Verify that the value is just number and letter or underscore
        if value.strip().isalnum() == False: return JsonResponse({'message': f'invalid {field}. Number AND/OR Letter Only'}, status = 400)
        
        istance = Profile.objects.filter(user = request.user).select_related('user').first()
        try:
            #check if user is sending too much request at once
            cached_key = 'last username or userid update for ' + request.META.get("REMOTE_ADDR")
            if cache.get(cached_key) is not None:
                #reset the cache since user is too frequent
                cache.set(key=cached_key, value="i dey here", timeout=60)
                return JsonResponse({'message': 'Request to frequent, please wait 30 seconds, NB; retry before wait period will reset the wait period'}, status = 403)
                    
            #username or user_id is valid number and letter, now update
            #Lowercase as that will be the standard aside email that will be upper
            if field == 'username':
                istance.user.username = value.lower()                     
                istance.user.save()
            elif field == 'user_id':
                if value.lower().strip() == istance.user.username.lower():return JsonResponse({'message': 'For Your Account Security, UserId and Username cannot be the same.'}, status = 400)
                istance.public_searchable_username = value.lower()
                istance.save()
            
            cache.set(key=cached_key, value="i dey here", timeout=60)       #set a cache to rate limit user from too many request
            return JsonResponse({'message': 'success'}, status = 201)
        except IntegrityError:return JsonResponse({'message': 'ERROR. user with this ID exists'}, status = 403)
    
        
        
       
class ProfileUpdateToggles(LoginRequiredMixin, View):
    """HANDLE UPDATING PROFILE SETTING THAT THE ProfileUpdateUsernameORUserid HAVE NT HANDLED"""
    def post(self, request):
           data = json.loads(request.body)
           value = data.get('value')
           field = data.get('field')
           # HANDLE ERROR AND CLEANING
           if field is None or value is None: return JsonResponse({'message': 'invalid'}, status = 400)
           
           #CLEAN DATA - OMO BUT I AM TAKING A RISK, I AM ONLY DEPENDING ON BOOLEAN VALUE AND NT ACTUALLY CHECKING THE VALUE E.G IF USER SNED TRUE, I JSUT SAVE FALSE, I DONT CHECK IF ITS TRUE
           istance = Profile.objects.filter(user = request.user).first()
           #HANDLE LEADEROARD OPT IN
           if field == 'leaderboard_optin':
               istance.leaderboard_optin = not istance.leaderboard_optin
               istance.save()
               return JsonResponse({'message': 'success'}, status = 200)
           elif field == 'streak_count_is_public_visible':
               istance.streak_count_is_public_visible = not istance.streak_count_is_public_visible
               istance.save()
               return JsonResponse({'message': 'success'}, status = 200)
           elif field == 'ai_insight_active':
                istance.ai_insight_active = not istance.ai_insight_active
                istance.save()
                return JsonResponse({'message': 'success'}, status = 200)
           elif field == 'social_mode':
               if value == 'partner':
                   istance.social_mode = 'partner'
               elif value == 'solo':
                   istance.social_mode = 'solo'
               istance.save()
               return JsonResponse({'message': 'success'}, status = 200)
           elif field == 'weekly_report_email_active':
                istance.weekly_report_email_active = not istance.weekly_report_email_active
                istance.save()
                return JsonResponse({'message': 'success'}, status = 200)
           elif field == 'custom_report_email_active':
                #istance.custom_report_email_active = not istance.custom_report_email_active
                #istance.save()
                return JsonResponse({'message': 'COMING SOON...'}, status = 404)
           elif field == 'receive_newsletter':
                istance.receive_newsletter = not istance.receive_newsletter
                istance.save()
                return JsonResponse({'message': 'success'}, status = 200)
           elif field == 'ai_coach_active':
                return JsonResponse({'message': 'COMING SOON...'}, status = 404)
            
            
           #IF COMMAND IS NOT KNOWN
           else:    return JsonResponse({'message': 'unknown'}, status = 500)
           
class ProfileUpdateTheme(LoginRequiredMixin, View):
    """HANDLE UPDATING PROFILE THEME - i have scope of extending th theme from just black and white to more themes in the future"""
    def post(self, request):
        data = json.loads(request.body)
        value = data.get('value')
        field = data.get('field')
        logger.info(f"User {request.user} is trying to update theme with field: {field} and value: {value}")
        
        # HANDLE ERROR AND CLEANING
        if field is None or value is None: return JsonResponse({'message': 'invalid'}, status = 400)
        
        #CLEAN DATA - OMO BUT I AM TAKING A RISK, I AM ONLY DEPENDING ON BOOLEAN VALUE AND NT ACTUALLY CHECKING THE VALUE E.G IF USER SNED TRUE, I JSUT SAVE FALSE, I DONT CHECK IF ITS TRUE
        istance = Profile.objects.filter(user = request.user).first()
        #HANDLE LEADEROARD OPT IN
        if field == 'theme':
            istance.theme = not istance.theme
            istance.save()
            return JsonResponse({'message': 'success'}, status = 200)
        
        #raise issue
        return JsonResponse({'message': 'unknown theme'}, status = 500)


class EachCommitmentViewSettings(LoginRequiredMixin, View):
    """THIS HANDLE UpDATE IN EACH COMMITMENT SETTINGS, LIKE REMINDER TIME, REMINDER METHOD, CHECKIN TIME, And is active"""
    def patch(self, request, commitment_key):
        key = "updated mode of delivery for " + request.META.get("REMOTE_ADDR")
        if cache.get(key=key):  # Check if the user has made a recent request within 10 sec
            cache.set(key=key, value="i dey here", timeout=1)  # Reset the cache to extend the wait time
            return JsonResponse({'message': 'You are making requests too frequently. wait for 10 seconds.'}, status=429)

        data = json.loads(request.body)
        mode_of_delivery = data['mode_of_delivery']                         #email or whatsapp
        checkin_time = data['user_selected_reminder_time']                  #time to update xx:xx
        whatsapp_number = data.get('whatsapp_number')                       #only if mode_of_delivery is whatsapp
        reminder_active = data.get('reminder_active')                       #Check if the user want to stop receviing reminders
        # Validate mode_of_delivery
        if mode_of_delivery not in ChoicesValidatorInModels().report_delivery_mode: return JsonResponse({'message': 'Invalid mode of delivery.'}, status=400)
       
        #input valid, Now update the data
        db_istance = Commitment.objects.filter(user=request.user, pk=commitment_key).first()
        
        #cleaning whatsap number if mode_of_delivery is whatsapp, make sure it starts with + and is a valid number
        if mode_of_delivery == 'whatsapp':
            #verify that whatsap number is valid
            if (mode_of_delivery == 'whatsapp' and not whatsapp_number):    return JsonResponse({'message': 'WhatsApp number is required when WhatsApp reminders are selected.'}, status=400)
            elif (mode_of_delivery == 'whatsapp' and whatsapp_number[0] != '+'): return JsonResponse({'message': 'Invalid WhatsApp number. It should start with + followed by the country code and number.'}, status=400)
              
         #saving data
        db_istance.mode_of_delivery = mode_of_delivery.strip().lower()
        db_istance.whatsapp_number = whatsapp_number if mode_of_delivery == 'whatsapp' else ''
        db_istance.user_selected_reminder_time = checkin_time
        db_istance.reminder_active = reminder_active
        db_istance.save()
        
        #rate limit user for 60 seconds to avoid endpoint abuse 
        
        cache.set(key=key, value="i dey here", timeout=60)
        return JsonResponse({'message': 'update successful.'}, status=200)     
    
class EachCommitmentArchive(LoginRequiredMixin, View):
    """DELETE A COMMITMENT. There is no archive/restore state in this product - pressing
    delete flips is_active to False right away (so it instantly disappears from the
    user's own commitment list / dashboard / heat map / everywhere else that already
    filters on is_active=True) and that's it from the user's side. The actual DB row
    (and its Entries) get permanently removed the NEXT time the cron job ticks - see
    utility/maintenance_engine.purge_deleted_commitments(). The url/view name kept the
    word "archive" only to avoid touching urls.py; nothing about the behavior archives
    anything."""
    def post(self, request, id):
        istance = Commitment.objects.filter(user=request.user, pk=id).first()
        if istance is None:
            return JsonResponse({'message': 'No commitment found with this details'}, status=404)
        if istance.is_active is False:
            return JsonResponse({'message': 'This commitment has already been deleted'}, status=400)
        istance.is_active = False
        istance.pending_notice = ''
        istance.save(update_fields=['is_active', 'pending_notice'])
        return JsonResponse({'message': 'Commitment deleted successfully'}, status=200)
    
class EachCommitementHeatMap(LoginRequiredMixin, View):
    """Return heat map for a simgle commitment most likely in the entry page to show the user how they have been doing in the past 7 entries"""
    def get(self, request, commitment_key):
        entries_istance = Entries.objects.filter(commitment_key__pk=commitment_key).select_related('commitment_key').order_by('commit_at')[:7]  # Limit to the last 7 entries
        if entries_istance is None: return JsonResponse({'message': 'No Entries found.'}, status=403)
        
        #entries exist with the said user, return needed data
        heatmap_data = [
            {
                "date": i.commit_at.isoformat(),
                "checked_in": True,
                "word_count": i.word_count,
                "mood": i.mood
            }
            for i in entries_istance
        ]
        if len(heatmap_data) < 7:
            # Pad the list with empty entries if there are fewer than 7
            for _ in range(7 - len(heatmap_data)):
                heatmap_data.insert(0, {
                    "date": None,
                    "checked_in": False,
                    "word_count": 0,
                    "mood": None
                })
        
        
        return JsonResponse({
            'message': 'success',
            'days': heatmap_data
        }, status=200)

class EachCommitementEntries(LoginRequiredMixin, View):
    """SAVE TODAY ENTRIES , INCHARGE OF THE LONG ONE, the actual entry point not the quick one in the commitment page even though both are can be used to save entries"""
    def post(self, request, commitment_key):
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        mood = data.get('mood', 'minimum').strip()
        
        if not content: return JsonResponse({'message': 'Content cannot be empty.'}, status=400)
        
        # Fetch the commitment instance
        commitment_instance = Commitment.objects.filter(user=request.user, pk=commitment_key).first()
        if not commitment_instance: return JsonResponse({'message': 'Commitment not found.'}, status=404)
        
        #check if user have already checked in today, if yes, return error
        last_entry = Entries.objects.filter(commitment_key=commitment_key).order_by('-commit_at').first()
        if last_entry and last_entry.commit_at.isoformat() == timezone.now().date().isoformat(): #yyyy-mm-dd
            return JsonResponse({'message': 'You have already checked in today.'}, status=400)
        
        # Create a new entry since commitment dey and user have not made entry today
        with transaction.atomic():
            entry = Entries.objects.create(
                commitment_key=commitment_instance,
                content=content,
                word_count=len(content.split()),
                mood=mood
                )
            
            # Update streak count and last check-in
            last_entry = Entries.objects.filter(commitment_key=commitment_key).order_by('-commit_at').first()   #The - tells it to sort by newest first
            if last_entry and (timezone.now().date() - last_entry.commit_at).days == 1:
                commitment_instance.streak_count += 1   #Streak count increase by 1 if last entry was yesterday
            else:
                commitment_instance.streak_count = 1 # Reset streak count to 1 if last entry was not yesterday
            
            commitment_instance.last_check_in = timezone.now()
            commitment_instance.save()
            
            
        
        return JsonResponse({'message': 'Entry saved successfully.', 'entry_id': entry.pk}, status=201)

class ReportsData(LoginRequiredMixin, View):
    """THIS IS THE JSON DATA THAT WILL BE USED TO RENDER THE REPORTS PAGE.

    Was previously 100% hardcoded fixture data (fake numbers regardless of who was
    logged in) - now computed from the user's real Commitment/Entries rows for the
    requested week (?week=YYYY-MM-DD, any date inside the target week; defaults to
    the current week). Every key the frontend (reports.html) reads is still present
    with the same shape, just populated from the database instead of made up.

    If the user genuinely doesn't have enough history yet (no entries at all, or the
    account is brand new), `not_enough_data` is set and `generated_note` carries an
    honest "check back later" message instead of a shaped-but-empty report.

    `?commitment=<id>` (optional) scopes every number in the report to that one
    commitment; omitted, empty, or invalid/foreign values default to (and safely
    fall back to) ALL of the user's active commitments combined, which is the
    correct default behaviour."""
    login_url = '/v1/login/'

    def get(self, request):
        from datetime import timedelta
        import re
        from collections import Counter

        week_param = request.GET.get('week')
        if week_param:
            try:
                anchor = timezone.datetime.strptime(week_param, '%Y-%m-%d').date()
            except ValueError:
                anchor = timezone.localdate()
        else:
            anchor = timezone.localdate()

        week_start = anchor - timedelta(days=anchor.weekday() + 1 if anchor.weekday() != 6 else 0)
        #Sunday -> Saturday week, matching the "days" contract below (Sun first)
        week_start = anchor - timedelta(days=(anchor.weekday() + 1) % 7)
        week_end = week_start + timedelta(days=6)
        today = timezone.localdate()

        #---- COMMITMENT FILTER ----
        # `?commitment=<id>` scopes the ENTIRE report to a single commitment; anything
        # missing/invalid/not-owned-by-this-user/inactive silently falls back to "all"
        # so a stale link or tampered param can never leak another user's data or 500.
        # Defaulting to "all" is the point of this fix: every active commitment feeds
        # the report unless the person explicitly narrows it down.
        user_commitments = list(Commitment.objects.filter(user=request.user, is_active=True).order_by('what'))

        commitment_param = request.GET.get('commitment', 'all')
        selected_commitment_id = None
        if commitment_param and commitment_param != 'all':
            try:
                candidate_id = int(commitment_param)
            except (TypeError, ValueError):
                candidate_id = None
            if candidate_id is not None and any(c.id == candidate_id for c in user_commitments):
                selected_commitment_id = candidate_id
            #else: invalid/foreign/inactive id -> stays None -> falls back to "all" below

        all_commitments = (
            [c for c in user_commitments if c.id == selected_commitment_id]
            if selected_commitment_id is not None else user_commitments
        )

        base_entries = Entries.objects.filter(commitment_key__user=request.user)
        all_entries_ever = (
            base_entries.filter(commitment_key_id=selected_commitment_id)
            if selected_commitment_id is not None else base_entries
        )
        total_entries_ever = all_entries_ever.count()

        #"not enough data" if the account genuinely has nothing meaningful to report on yet
        #(scoped to the filter above, so picking a brand-new commitment correctly says so
        # even if the account overall has plenty of history on OTHER commitments)
        not_enough_data = total_entries_ever < 3 or not all_commitments

        week_entries = list(
            all_entries_ever.filter(commit_at__range=(week_start, week_end))
            .select_related('commitment_key')
            .order_by('commit_at')
        )

        #---- STAT OVERVIEW ----
        days_with_entry = {e.commit_at for e in week_entries}
        entries_this_week = len(days_with_entry)
        possible_slots = max(len(all_commitments) * 7, 1)
        entries_logged = len(week_entries)
        consistency_pct = round((entries_logged / possible_slots) * 100) if all_commitments else 0
        consistency_pct = min(consistency_pct, 100)

        current_streak = max((c.streak_count for c in all_commitments), default=0)
        longest_streak = current_streak  #no historical "peak streak" field exists on the model - this is the best honest proxy we have right now

        avg_words = round(sum(e.word_count for e in week_entries) / len(week_entries)) if week_entries else 0

        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_start - timedelta(days=1)
        prev_week_entries_count = all_entries_ever.filter(commit_at__range=(prev_week_start, prev_week_end)).count()
        prev_consistency_pct = round((prev_week_entries_count / possible_slots) * 100) if all_commitments else 0
        diff = consistency_pct - prev_consistency_pct
        if prev_week_entries_count == 0 and entries_this_week == 0:
            consistency_note = "No check-ins logged yet this week."
        elif diff > 0:
            consistency_note = f"Up {diff} point{'s' if abs(diff) != 1 else ''} from last week"
        elif diff < 0:
            consistency_note = f"Down {abs(diff)} point{'s' if abs(diff) != 1 else ''} from last week"
        else:
            consistency_note = "Same as last week"

        missed_this_week = 7 - entries_this_week if entries_this_week < 7 else 0
        entries_note = f"Missed {missed_this_week} day{'s' if missed_this_week != 1 else ''}" if missed_this_week else "Perfect week"
        avg_words_note = "Keep writing a little more each time" if avg_words < 20 else "Solid, detailed check-ins"

        #---- DAYS (Sun -> Sat) ----
        emoji_map = Static.emoji_translator()
        entries_by_date = {}
        for e in week_entries:
            entries_by_date.setdefault(e.commit_at, []).append(e)

        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        days = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            todays_entries = entries_by_date.get(d, [])
            missed = len(todays_entries) == 0 and d <= today
            total_words = sum(e.word_count for e in todays_entries)
            top_entry = max(todays_entries, key=lambda e: e.word_count, default=None)
            mood = top_entry.mood if top_entry else None
            strength = 'strong' if len(todays_entries) >= max(1, len(all_commitments)) else ('mid' if todays_entries else 'missed')
            days.append({
                "day_short": day_names[i][:3],
                "day_name": day_names[i],
                "date_label": d.strftime('%b %d'),
                "missed": missed and d <= today,
                "status": "good" if todays_entries else ("missed" if d <= today else "ok"),
                "strength": strength,
                "mood_color": "#22c55e" if todays_entries else "#334155",
                "mood_emoji": emoji_map.get(mood, '—') if mood else '—',
                "mood_label": mood.replace('_', ' ').title() if mood else "No entry",
                "time_label": (f"Checked in" if todays_entries else ("Day hasn't happened yet" if d > today else "No check-in")),
                "word_count": total_words,
                "note": (top_entry.content[:180] if top_entry and top_entry.content else ("Nothing logged for this day." if d <= today else "")),
            })

        #---- REFLECTIONS: top 3 longest entries this week, own words only ----
        reflections = [
            {"text": e.content[:220], "day": day_names[(e.commit_at - week_start).days % 7]}
            for e in sorted(week_entries, key=lambda e: e.word_count, reverse=True)[:3]
            if e.content
        ]

        #---- TREND: this week vs last week, per day + last 8 weeks sparkline ----
        prev_week_entries = list(all_entries_ever.filter(commit_at__range=(prev_week_start, prev_week_end)))
        prev_entries_by_date = {}
        for e in prev_week_entries:
            prev_entries_by_date.setdefault(e.commit_at, 0)
            prev_entries_by_date[e.commit_at] += 1
        compare = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            pd = prev_week_start + timedelta(days=i)
            now_pct = round((len(entries_by_date.get(d, [])) / max(len(all_commitments), 1)) * 100)
            last_pct = round((prev_entries_by_date.get(pd, 0) / max(len(all_commitments), 1)) * 100)
            compare.append({"day_short": day_names[i][:3], "last_pct": min(last_pct, 100), "now_pct": min(now_pct, 100)})

        sparkline = []
        for w in range(7, -1, -1):
            ws = week_start - timedelta(days=7 * w)
            we = ws + timedelta(days=6)
            cnt = all_entries_ever.filter(commit_at__range=(ws, we)).count()
            pct = round((cnt / possible_slots) * 100) if all_commitments else 0
            sparkline.append(min(pct, 100))
        sparkline_note = "Keep logging to build up your trend line." if total_entries_ever < 14 else (
            f"You've moved {sparkline[-1] - sparkline[0]:+d} points over the last 8 weeks." if len(sparkline) >= 2 else ""
        )

        #---- HIGHLIGHTS ----
        best_day = max(days, key=lambda d: d['word_count'], default=None)
        worst_candidates = [d for d in days if d['missed']]
        highlights = {
            "best": {"day_name": best_day['day_name'], "note": f"{best_day['word_count']} words logged."} if best_day and best_day['word_count'] > 0 else {"day_name": "—", "note": "No standout day yet this week."},
            "toughest": {"day_name": worst_candidates[0]['day_name'], "note": "No entry logged this day."} if worst_candidates else {"day_name": "—", "note": "No missed days this week - well done."},
        }

        #---- COMMITMENTS ----
        commitments_out = []
        for c in all_commitments:
            c_entries_this_week = [e for e in week_entries if e.commitment_key_id == c.id]
            frac_n = len(c_entries_this_week)
            pct = round((frac_n / 7) * 100)
            commitments_out.append({"what": c.what, "icon": "circle-check", "pct": pct, "frac": f"{frac_n}/7"})

        #---- MOOD DISTRIBUTION ----
        mood_counter = Counter(e.mood for e in week_entries if e.mood)
        moods_out = []
        for mood, count in mood_counter.most_common(8):
            moods_out.append({
                "emoji": emoji_map.get(mood, '🙂'),
                "label": mood.replace('_', ' ').title(),
                "pct": round((count / len(week_entries)) * 100) if week_entries else 0,
                "count": count,
            })

        #---- INSIGHTS: a couple of genuinely-derived observations, not filler ----
        insights = []
        if commitments_out:
            top_commitment = max(commitments_out, key=lambda c: c['pct'])
            if top_commitment['pct'] > 0:
                insights.append({"icon": "star", "title": "Strongest commitment", "text": f"\"{top_commitment['what']}\" had your best consistency this week at {top_commitment['pct']}%."})
        if mood_counter:
            top_mood = mood_counter.most_common(1)[0][0]
            insights.append({"icon": "face-smile", "title": "Most common mood", "text": f"You logged \"{top_mood.replace('_', ' ')}\" more than any other mood this week."})
        if not insights:
            insights.append({"icon": "lightbulb", "title": "Not enough data yet", "text": "Keep checking in - insights show up once we have a few days of entries to compare."})

        #---- WORD CLOUD: real word frequency from this week's own entries ----
        STOPWORDS = {'the','a','an','and','or','but','to','of','in','on','for','is','it','my','i','was','with','at','this','that','so','be','me','im','not','just','as','are','have','had','has'}
        word_counts = Counter()
        for e in week_entries:
            for w in re.findall(r"[a-zA-Z']+", (e.content or '').lower()):
                if len(w) > 2 and w not in STOPWORDS:
                    word_counts[w] += 1
        max_count = max(word_counts.values(), default=1)
        word_cloud = [
            {"word": w, "weight": max(1, round((c / max_count) * 10))}
            for w, c in word_counts.most_common(15)
        ]

        #---- PULSE: last 20 days of activity, normalized 0-100 ----
        bar_heights = []
        for i in range(19, -1, -1):
            d = today - timedelta(days=i)
            cnt = all_entries_ever.filter(commit_at=d).count()
            pct = round((cnt / max(len(all_commitments), 1)) * 100)
            bar_heights.append(min(max(pct, 0), 100))
        active_days_recent = len([h for h in bar_heights if h > 0])
        readout_text = f"{round((active_days_recent/20)*100)}% signal strength over the last 20 days" if not not_enough_data else "Not enough history yet to read your pulse."

        #---- GROUP COMPARE: only meaningful for partner-mode users ----
        profile = Profile.objects.filter(user=request.user).first()
        group_compare = []
        group_name = None
        if profile and profile.social_mode == 'partner':
            group_name = "Your Partners"
            you_pct = consistency_pct
            group_compare.append({"name": "You", "initials": (request.user.username[:2] or 'YO').upper(), "pct": you_pct, "is_you": True})
            partner_links = Friendship.objects.filter(to_user=request.user, status='accepted').select_related('from_user')
            for f in partner_links:
                p_profile = Profile.objects.filter(user=f.from_user).first()
                if not p_profile:
                    continue
                p_commitments = Commitment.objects.filter(user=f.from_user, is_active=True)
                p_possible = max(p_commitments.count() * 7, 1)
                p_entries = Entries.objects.filter(commitment_key__user=f.from_user, commit_at__range=(week_start, week_end)).count()
                p_pct = min(round((p_entries / p_possible) * 100), 100) if p_commitments.exists() else 0
                group_compare.append({
                    "name": p_profile.public_searchable_username or f.from_user.username,
                    "initials": (f.from_user.username[:2] or 'PA').upper(),
                    "pct": p_pct,
                    "is_you": False,
                })
            group_compare.sort(key=lambda r: r['pct'], reverse=True)

        if not_enough_data:
            generated_note = "Not enough data yet — check back after a few more check-ins."
        else:
            generated_note = f"Generated from {entries_this_week} of 7 check-ins."

        data = {
            "not_enough_data": not_enough_data,
            #---- COMMITMENT FILTER (drives the picker in the UI) ----
            "selected_commitment": selected_commitment_id if selected_commitment_id is not None else "all",
            "available_commitments": (
                [{"id": "all", "what": "All Commitments"}] +
                [{"id": c.id, "what": c.what} for c in user_commitments]
            ),
            "week_range_label": f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}",
            "week_number_label": f"Week {week_start.isocalendar()[1]}",
            "generated_note": generated_note,
            "current_week_iso": week_start.isoformat(),
            "prev_week_iso": prev_week_start.isoformat(),
            "next_week_iso": (week_start + timedelta(days=7)).isoformat() if week_end < today else None,

            #---- STAT OVERVIEW ----
            "consistency_pct": consistency_pct,
            "consistency_note": consistency_note,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "entries_this_week": entries_this_week,
            "entries_note": entries_note,
            "avg_words": avg_words,
            "avg_words_note": avg_words_note,

            "pulse": {"readout_text": readout_text, "bar_heights": bar_heights},
            "days": days,
            "reflections": reflections,
            "trend": {"compare": compare, "sparkline": sparkline, "sparkline_note": sparkline_note},
            "highlights": highlights,
            "commitments": commitments_out,
            "moods": moods_out,
            "insights": insights,
            "word_cloud": word_cloud,
        }
        if group_name:
            data["group_name"] = group_name
            data["group_compare"] = group_compare

        return JsonResponse(data, status=200)


class GetVapidPublicKey(LoginRequiredMixin, View):
    """Hands the frontend the PUBLIC half of the VAPID keypair so it can call
    PushManager.subscribe({applicationServerKey: <this key>}). Safe to expose — the
    private half never leaves the server (see utility/push_sending.py)."""
    def get(self, request):
        # Checks BOTH keys via vapid_configured(), not just the public one - a
        # public-key-only check would let the browser successfully subscribe while
        # every actual send afterwards silently fails deep inside pywebpush the moment
        # it tries to sign with a missing private key.
        if not Static.vapid_configured():
            return JsonResponse({'message': 'Push notifications are not configured on this server yet.'}, status=503)
        return JsonResponse({'vapid_public_key': Static.vapid_public_key()}, status=200)


class SavePushSubscription(LoginRequiredMixin, View):
    """Called right after navigator.serviceWorker + PushManager.subscribe() succeed in
    the browser. Body shape (this is exactly what PushSubscription.toJSON() gives you):
        {"endpoint": "...", "keys": {"p256dh": "...", "auth": "..."}}
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            return JsonResponse({'message': 'Invalid JSON body.'}, status=400)

        endpoint = (data.get('endpoint') or '').strip()
        keys = data.get('keys') or {}
        p256dh = (keys.get('p256dh') or '').strip()
        auth = (keys.get('auth') or '').strip()
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

        if not endpoint or not p256dh or not auth:
            return JsonResponse({'message': 'endpoint, keys.p256dh and keys.auth are all required.'}, status=400)

        from ..models import PushSubscription
        # update_or_create on endpoint: same browser re-subscribing (e.g. after clearing
        # cache) just refreshes its keys/owner instead of creating a duplicate row.
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth, 'user_agent': user_agent},
        )

        from utility.push_sending import send_confirmation_push
        send_confirmation_push(endpoint=endpoint)  # fires instantly, confirms the whole pipeline actually works end to end

        return JsonResponse({'message': 'Push subscription saved. You will now get push reminders for commitments set to push.'}, status=200)


class RemovePushSubscription(LoginRequiredMixin, View):
    """Called when the user turns push off from this browser (or the frontend detects
    the permission was revoked). Deletes only the caller's own subscription row —
    scoped to request.user so nobody can delete someone else's by guessing an endpoint."""
    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            return JsonResponse({'message': 'Invalid JSON body.'}, status=400)

        endpoint = (data.get('endpoint') or '').strip()
        if not endpoint:
            return JsonResponse({'message': 'endpoint is required.'}, status=400)

        from ..models import PushSubscription
        deleted, _ = PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        if deleted == 0:
            return JsonResponse({'message': 'No matching subscription found for your account.'}, status=404)
        return JsonResponse({'message': 'Push subscription removed.'}, status=200)
    
    
    
class DataExport(LoginRequiredMixin, View):
    """Exports everything the user has ever written into this app - every commitment
    they've created (active or not) and every entry logged against it - either as CSV
    or JSON, picked via ?format=csv|json (defaults to csv)."""
    def get(self, request):
        import csv
        from django.http import HttpResponse

        fmt = request.GET.get('format', 'csv').strip().lower()
        if fmt not in ('csv', 'json'):
            return JsonResponse({'message': 'That export format is not available yet.'}, status=400)
        commitments = Commitment.objects.filter(user=request.user).order_by('id')
        if not commitments.exists():
            return JsonResponse({'message': 'You have no commitments yet, nothing to export.'}, status=400)

        rows = []
        for c in commitments:
            entries = Entries.objects.filter(commitment_key=c).order_by('commit_at')
            if not entries.exists():
                rows.append({
                    'commitment_id': c.pk, 'commitment_what': c.what, 'category': c.category,
                    'is_active': c.is_active, 'goal_days': c.goal_days, 'streak_count': c.streak_count,
                    'created_at': c.created_at.isoformat(), 'entry_date': None, 'mood': None,
                    'word_count': None, 'entry_content': None,
                })
                continue
            for e in entries:
                rows.append({
                    'commitment_id': c.pk, 'commitment_what': c.what, 'category': c.category,
                    'is_active': c.is_active, 'goal_days': c.goal_days, 'streak_count': c.streak_count,
                    'created_at': c.created_at.isoformat(), 'entry_date': e.commit_at.isoformat(),
                    'mood': e.mood, 'word_count': e.word_count, 'entry_content': e.content,
                })

        filename_base = f"streak_and_discipline_export_{request.user.username}_{timezone.now().date().isoformat()}"

        if fmt == 'json':
            from django.http import HttpResponse as HResp
            response = HResp(json.dumps({'exported_at': timezone.now().isoformat(), 'rows': rows}, indent=2), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.json"'
            return response

        #csv (also the fallback for any unrecognized ?format= value, e.g. the still-locked pdf/ai options)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
        writer = csv.writer(response)
        writer.writerow(['commitment_id', 'commitment_what', 'category', 'is_active', 'goal_days', 'streak_count', 'created_at', 'entry_date', 'mood', 'word_count', 'entry_content'])
        for r in rows:
            writer.writerow([r['commitment_id'], r['commitment_what'], r['category'], r['is_active'], r['goal_days'], r['streak_count'], r['created_at'], r['entry_date'] or '', r['mood'] or '', r['word_count'] if r['word_count'] is not None else '', r['entry_content'] or ''])
        return response


class BulkDeleteCommitments(LoginRequiredMixin, View):
    """Danger-zone 'delete all' - same rule as a single delete (EachCommitmentArchive):
    is_active=False right away, hidden immediately, hard-removed by the next cron tick.
    No archive/restore anywhere in this product."""
    def post(self, request):
        qs = Commitment.objects.filter(user=request.user, is_active=True)
        count = qs.count()
        if count == 0:
            return JsonResponse({'message': 'You have no active commitments to delete.'}, status=400)
        qs.update(is_active=False, pending_notice='')
        return JsonResponse({'message': f'{count} commitment(s) deleted.'}, status=200)


class ClearAllEntries(LoginRequiredMixin, View):
    """Permanently wipes every journal entry the user has written, across every
    commitment (active or not) - the commitments themselves stay, only the daily
    written entries are removed."""
    def post(self, request):
        qs = Entries.objects.filter(commitment_key__user=request.user)
        count = qs.count()
        if count == 0:
            return JsonResponse({'message': 'You have no entries to clear.'}, status=400)
        qs.delete()
        return JsonResponse({'message': f'{count} entrie(s) cleared.'}, status=200)


class ResetAllStreaks(LoginRequiredMixin, View):
    """Manually zero every active commitment's streak_count, on request - separate from
    (but reuses the same field as) the automatic 24h-inactivity reset the cron job does."""
    def post(self, request):
        qs = Commitment.objects.filter(user=request.user, is_active=True)
        count = qs.count()
        if count == 0:
            return JsonResponse({'message': 'You have no active commitments.'}, status=400)
        qs.update(streak_count=0, pending_notice='')
        return JsonResponse({'message': f'{count} streak(s) reset to zero.'}, status=200)