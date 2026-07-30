#THIS VIEW RETURNS ONLY JSON AND IT INCLUDE OPERATION WNHERE ONLY JSON IS REQUIRED

from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import Commitment, Entries, Profile, ChoicesValidatorInModels, Friendship
from django.shortcuts import reverse
from django.http import JsonResponse
from django.utils import timezone

from django.db import models


class CommitmentData(LoginRequiredMixin, View):
    """RETURNS DATA FOR THE DASHBOARD HOME TO USE TO DISPLAY A QUICK VIEW OF USER COMMITMENTS WITH THE LINK THAT REDORECT USER TO VIEW ACTUAL FULL DATA"""
    def get(self, request):
        commitment_istance = Commitment.objects.filter(user = request.user).all()
        if not commitment_istance.exists(): data = [
            {
                'id' : 0,                               #datakey is very important as without it , the current ui wont load
                'url' : '',                             #datakey is very important as without it , the current ui wont load
                "what": "No commitment",                #datakey is very important as without it , the current ui wont load
                "category": 'other',                    #datakey is very important as without it , the current ui wont load
                "streak_count": 0,                      #datakey is very important as without it , the current ui wont load
                "goal_days": 0,                         #datakey is very important as without it , the current ui wont load
                "days_since_start": 0,                  #datakey is very important as without it , the current ui wont load 
                "checkin_time": "00:00",                #datakey is very important as without it , the current ui wont load
                'is_active': False,                     #datakey is very important as without it , the current ui wont load
                "checked_in_today": False,              #datakey is very important as without it , the current ui wont load
                'message' : 'no commitment yet'         #datakey is very important as without it , the current ui wont load
            }
        ]
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
                "checked_in_today": (i.last_check_in is not None and i.last_check_in.date() == timezone.now().date()),                
            }
            for i in commitment_istance 
            ]
            status = 'all good'

        return JsonResponse({'commitments' : data}, status = 200)


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
            'message' : 'user does not have any entries, create commitment and check in to view entries in a beutiful layout'.upper(),
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


class UserPicture(LoginRequiredMixin, View):
    """INCHARGE OF ALWAYS BRINNGIN BACK THE URL FOR USER PICTIRE(get) OR UPDATING THE PROFILE PICTURE (post) IN THE DB"""
    def get(self, request):
        """find url from db and return it to clien"""
        istance = Profile.objects.filter(user = request.user).first().profile_img_url
        return JsonResponse({'message': "success", 'url' :istance}, status = 200)
    
    def post(self, request):
        """take url from user and save it in the db or cloudinary; nt sure fr now"""
        

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
        for i in all_commitments:
            uid = i.user_id
            if uid in commitments_by_user:
                commitments_by_user[uid].append(i.streak_count)
            else:
                commitments_by_user[uid] = [i.streak_count]

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
    
    
class DashboardJson(LoginRequiredMixin, View):
    """RETURN THE JSON FORMAT OF USER DATA BY JUST DOING /JSON ON THEIR DASHBOARD"""
    def get(self, request):
        profile_istance = Profile.objects.filter(user = request.user).first()
        Commitment_istance = Commitment.objects.filter(user = request.user).all()
        all_friendships = Friendship.objects.filter(
            models.Q(from_user=request.user) | models.Q(to_user=request.user)  # Q handles OR
        ).select_related('from_user', 'to_user').all()                         #JOIN handles eager loading(selected from), istead for loop that lead to N+1q
        
        partner_request_received = [i for i in all_friendships if all_friendships.to_user == request.user]
        friend_request_sent = [i for i in all_friendships if all_friendships.from_user == request.user]
        
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
