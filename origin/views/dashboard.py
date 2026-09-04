"""THE DASHBOARD IS DIVERSE AND TO ALLOW IT SCALE, IT NEED TO HAVE IT OWN VIEW"""
import json
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.utils import timezone
from ..models import Friendship, Profile, Commitment, Entries
from django.contrib import messages
from django.http import JsonResponse

from .utility_view import optimization
from ..models import ChoicesValidatorInModels

class Onboarding(LoginRequiredMixin, View):
    """PRE DASHBOARD"""
    login_url = '/v1/login/'
    def get(self, request):
        #check user tier, if it does not exist, redirect user to onboarding
        user_profile = Profile.objects.filter(user = request.user).first()
        if user_profile is None:
            if request.user.is_superuser or request.user.is_staff: return redirect('origin_staff_home')
                
            return render(request,'html/onboarding.html')
            logger.error(msg="User is not suppose to have a profile , if user have a profile, redirect them to dashboard")
        else: return redirect('origin_dashboard')


class ProfileSettings(LoginRequiredMixin, View):
    """FOR PROFILE IN THE DASHBOARD ASIDE USER INTERFACE"""
    login_url = '/v1/login/'
    def get(self, request):
        user_profile = Profile.objects.filter(user = request.user).order_by('tier').first()
        if user_profile is None:
            #incase user does not have tier configured and want to access this page, dont allow
            messages.warning(request, message="Please Finish your onboarding before accessing this page, head to login and sigin in with you creedentials and you will be taken to onboarding")
            return render(request, 'html/full_screen_message.html')
        
        #recently-deleted (is_active=False) commitments still inside their 24h recovery window -
        #see EachCommitmentArchive/ReactivateCommitment (json_only_view.py) + purge_deleted_commitments
        #(utility/maintenance_engine.py) for the full lifecycle this list represents.
        recovery_cutoff = timezone.now() - timezone.timedelta(hours=24)
        recoverable_commitments = Commitment.objects.filter(
            user=request.user,
            is_active=False,
            deactivated_at__isnull=False,
            deactivated_at__gt=recovery_cutoff,
        ).order_by('-deactivated_at')
        #hand the template a plain "hours left" number per row instead of making it do date math
        recoverable_commitments_with_countdown = [
            {
                'commitment': c,
                'hours_left': max(0, round(24 - (timezone.now() - c.deactivated_at).total_seconds() / 3600)),
            }
            for c in recoverable_commitments
        ]

        #user exist with tier configured
        return render(request, 'html/profile.html', {
            'tier': user_profile.tier,
            'theme': request.COOKIES.get('sd-theme', 'dark'),
            'public_id': user_profile.public_searchable_username,
            'leaderboard_optin': user_profile.leaderboard_optin,
            'streak_visible': user_profile.streak_count_is_public_visible,
            'ai_insight_active': user_profile.ai_insight_active,
            'weekly_report': user_profile.weekly_report_email_active,
            'custom_reports': user_profile.custom_report_email_active,
            'newsletter': user_profile.receive_newsletter,
            'zeal_score': user_profile.zeal_score,
            'social_mode': user_profile.social_mode,
            'recoverable_commitments': recoverable_commitments_with_countdown,
        })    
  
class Dashboard(LoginRequiredMixin, View):
    """THE FIRST LANDING PAGE WHEN DASHBOARD IS CLICKED, COMES RIGHT AFTER ONBOARDING DONE ALSO"""
    login_url = '/v1/login/'
    def get(self, request):
        if request.user.is_staff or request.user.is_superuser: return redirect('origin_staff_home')        
        user_profile = Profile.objects.filter(user = request.user).order_by('tier').first()
        if user_profile is None:
            #incase user does not have tier configured and want to access this page, dont allow
            messages.warning(request, message="Please Finish your onboarding before accessing this page, head to login and sigin in with you creedentials and you will be taken to onboarding")
            return render(request, 'html/full_screen_message.html')
        commitment_istance = Commitment.objects.filter(user=request.user, is_active=True).all()

        #flush pending notices (e.g streak resets from the cron job) to django messages, then clear so they don't repeat
        noticed_qs = commitment_istance.exclude(pending_notice='')
        for c in noticed_qs:
            messages.warning(request, message=c.pending_notice)
        noticed_qs.update(pending_notice='')

        #---- milestone celebrations (50% / 100% of goal_days) ----
        #One-time only (per commitment) on the dashboard - see Commitment.milestone_50_notified /
        #milestone_100_notified in models.py for why. dashboard.html reads `celebrations` and fires
        #the matching 3D effect (confetti "hooray" for 50%, full standing-ovation for 100%) once on
        #load, then the effect never repeats here again even if the user keeps visiting the
        #dashboard - hitting 100% specifically ALSO stays replayable forever, but only on the
        #commitment's OWN page (see EachCommitmentView), never here again.
        celebrations = []
        for c in commitment_istance:
            pct = c.progress_percent()
            if pct >= 100 and not c.milestone_100_notified:
                celebrations.append({'id': c.pk, 'what': c.what, 'level': 100})
                c.milestone_100_notified = True
                c.save(update_fields=['milestone_100_notified'])
            elif pct >= 50 and not c.milestone_50_notified:
                celebrations.append({'id': c.pk, 'what': c.what, 'level': 50})
                c.milestone_50_notified = True
                c.save(update_fields=['milestone_50_notified'])

        consistency = [0 for i in commitment_istance if i.streak_count > 0]    #Find the amount of streak score > 0 / total commitment (i use the tenchique of all ocnsistncy must have a streak score but are they all greater than zero?) ; that give the consistency_cpt
        avg_streak_Counter = [ i.streak_count for i in commitment_istance]
        try:    avg_streak = sum(avg_streak_Counter) / len(avg_streak_Counter) #i added one to curb the issue of division by zero   sum them all and divide by all to to get roughly avg 
        except ZeroDivisionError: avg_streak = 0
        
        user_profile.zeal_score = round(avg_streak*commitment_istance.count())
        user_profile.save()
        try: cpct = (len(consistency)/commitment_istance.count())*100
        except:cpct=0
        data = {
            'tier' : user_profile.tier,
            'zeal_score' : user_profile.zeal_score,
            'Upcoming_milestone': 6 - timezone.now().weekday(), #This is to make sure user are celebrated weekly
            'ai_insight_active' : user_profile.ai_insight_active,
            'social_mode' : user_profile.social_mode,
            'total_active_commitments': commitment_istance.count(),
            'consistency_pct': cpct,  
             'total_entries': Entries.objects.filter(commitment_key__user = request.user).count(),       #Hold usr current tier
             'theme_mode': request.COOKIES.get("sd-theme", 'dark'),
            
            'public_searchable_username ' : user_profile.public_searchable_username,
            'celebrations_json': json.dumps(celebrations),
            
        }
        
        optimization() #this is for debugging and optimization, it will print the query count and the sql query in the console
        return render(request, 'html/dashboard.html', data)
    


        
        
class EachCommitmentView(LoginRequiredMixin, View):
    login_url = '/v1/login/'
    """This is for viewing each commitment data, note and every other details based on X commitment(ENTRIES)"""
    def get(self, request, commitment_key): return self.post(request, commitment_key=commitment_key)
    def post(self, request, commitment_key):
        #get the instance i will need
        profile_istance = Profile.objects.filter(user = request.user).first()
        if profile_istance is None: return JsonResponse({'message': 'no profile attached to this account, please contact customer support ASAP'}, statu = 400)
        commitment_istance = Commitment.objects.filter(user = request.user, pk = commitment_key, is_active=True).first() #is_active=True so a deleted commitment can never be viewed again, even via a saved/old link
        if commitment_istance is None:
            messages.warning(request, message="This commitment doesn't exist or was deleted.")
            return redirect('origin_commitments')

        #flush any pending_notice (e.g a streak reset from the cron job) to the user as an honest django message, then clear it so it doesn't repeat on the next visit
        if commitment_istance.pending_notice:
            messages.warning(request, message=commitment_istance.pending_notice)
            commitment_istance.pending_notice = ''
            commitment_istance.save(update_fields=['pending_notice'])

        today_entry_istance = Entries.objects.filter(commitment_key__user = request.user, commitment_key__pk = commitment_key, commit_at = timezone.datetime.now().date()).select_related('commitment_key').first()
        
        return render(request, 'html/commitment_detail-entries.html',{
            'theme-mode': request.COOKIES.get('sd-theme', 'dark'),
            'tier': profile_istance.tier,
            'ai_insight_active': profile_istance.ai_insight_active,
            'commitment':    commitment_istance,        # full model instance,
            'commitment_id': commitment_istance.pk,     # int ; used by all JS API calls
            'has_entry_today': today_entry_istance is not None,
            'today_entry':     today_entry_istance,
            'motion_list': ChoicesValidatorInModels().mood,         # list of strings, same as commitment page
            #standing-ovation replay: unlike the dashboard's one-time 50%/100% toast (see Dashboard
            #view above + Commitment.milestone_100_notified), the commitment's OWN page replays the
            #full celebration EVERY visit once it's hit 100% - simply because completed_at is set,
            #no "already shown" flag involved here on purpose.
            'replay_celebration': commitment_istance.completed_at is not None,
            
        })
   
class Relationship(LoginRequiredMixin, View):
    """This is for the relationship page on dashboard"""
    login_url = '/v1/login/'
    def get(self, request):
        istance = Profile.objects.filter(user = request.user).first()

        optimization() #this is for debugging and optimization, it will print the query count and the sql query in the console

        return render(request, 'html/relationship.html', {
            'theme_mode': request.COOKIES.get('sd-theme', 'dark'),
            'tier': istance.tier,
            'ai_insight_active' : istance.ai_insight_active,
            })

class PartnerAcceptedDashboard(LoginRequiredMixin, View):
    login_url = 'v1/login/'
    def get(self, request, userid):
        print(request.user, userid)
        istance = Profile.objects.filter(user=request.user).first()
        if istance is None:
            messages.warning(request, message="Please Finish your onboarding before accessing this page, head to login and sigin in with you creedentials and you will be taken to onboarding")
            return render(request, 'html/full_screen_message.html')

        #validate tht indeed there is a friendship with status accpetd bwn this request.user and userid
        userid_user_ist = Profile.objects.filter(public_searchable_username__iexact = userid).first()
        if userid_user_ist is None:
            #user dey whine me
            messages.error(request, message= "ERROR 403.   You are not AUTHORIZED to visit this page, to gain access; add partner and once they accept your request, go to dashboard -> relationship -> partners.")
            return render(request, 'html/full_screen_message.html')
        
        #check if partner is still in partner mode or have change to solo
        if userid_user_ist.social_mode != 'partner':
            messages.error(request, message= f"ERROR 403. Your partner {userid} have changed their social mode to solo and due to STREAK & DISCIPLINE security, you are denied access to view this page.")
            return render(request, 'html/full_screen_message.html')
        #check if that relationship exist
        relationship = Friendship.objects.filter(
            from_user = userid_user_ist.user,
            to_user = request.user,
            status__iexact = 'accepted'
        ).first()
        
        if relationship is None:
            messages.error(request, message= f"ERROR 403. You are not authorized to visit this page, This error can surface if {userid} remove you from their Partner List.")
            return render(request)
        
        #relationship is valid and not none
        
        commitment_istance = Commitment.objects.filter(user=userid_user_ist.user, is_active=True).all()
        streaks = [c.streak_count for c in commitment_istance]
        active_count = len(streaks)
        combined_streak = sum(streaks)
        longest_streak = max(streaks) if streaks else 0
        with_progress = len([s for s in streaks if s > 0])
        consistency_pct = round((with_progress / active_count) * 100) if active_count else 0
        total_checkins = Entries.objects.filter(commitment_key__user=userid_user_ist.user).count()

        last_entry = Entries.objects.filter(commitment_key__user=userid_user_ist.user).order_by('-commit_at').first()
        today = timezone.now().date()
        last_active_days_ago = (today - last_entry.commit_at).days if last_entry else None

        optimization()

        return render(request, 'html/partner_detail.html', {
            'theme_mode': request.COOKIES.get('sd-theme', 'dark'),
            'tier': istance.tier,
            'ai_insight_active': istance.ai_insight_active,
            'partner_userid': userid_user_ist.public_searchable_username,
            'partner_username': userid_user_ist.user.username,
            'partner_zeal_score': userid_user_ist.zeal_score,
            'active_commitments_count': active_count,
            'combined_streak': combined_streak,
            'longest_streak': longest_streak,
            'consistency_pct': consistency_pct,
            'total_checkins': total_checkins,
            'last_active_days_ago': last_active_days_ago,
            'partner_since': relationship.updated_at,
        })



    
class DashboardCommitmentView(LoginRequiredMixin, View):
    """The commitment page on dashboard contents"""
    login_url= '/v1/login/'
    def get(self, request):
        
        istance = Profile.objects.filter(user = request.user).first()
        if istance is None:
            #incase user does not have tier configured and want to access this page, dont allow
            messages.warning(request, message="Please Finish your onboarding before accessing this page, head to login and sigin in with you creedentials and you will be taken to onboarding")
            return render(request, 'html/full_screen_message.html')
        
        #flush pending notices (e.g streak resets from the cron job) to django messages, then clear so they don't repeat
        noticed = Commitment.objects.filter(user=request.user, is_active=True).exclude(pending_notice='')
        for c in noticed:
            messages.warning(request, message=c.pending_notice)
        noticed.update(pending_notice='')

        open_add_commitment = request.GET.get('add', False)
        return render(request, 'html/commitments.html', {
            'tier' : istance.tier,
            'ai_insight_active': istance.ai_insight_active,
            'add': open_add_commitment,
            'motion_list': ['Happy', 'Sad', 'more happy', 'more sad', 'mix of balance']
            })
    
    
class DashbaordAnalytics(LoginRequiredMixin, View):
    """This is for the analytics page on dashboard"""
    login_url = '/v1/login/'
    def get(self, request):
        istance = Profile.objects.filter(user = request.user).first()
        return render(request, 'html/reports.html', {
            'theme_mode': request.COOKIES.get('sd-theme', 'dark'),
            })