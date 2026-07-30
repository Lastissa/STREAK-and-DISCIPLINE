"""THE DASHBOARD IS DIVERSE AND TO ALLOW IT SCALE, IT NEED TO HAVE IT OWN VIEW"""
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.utils import timezone
from ..models import Profile, Commitment, Entries
from django.contrib import messages



class Onboarding(LoginRequiredMixin, View):
    """PRE DASHBOARD"""
    login_url = '/v1/login/'
    def get(self, request):
        #check user tier, if it does not exist, redirect user to onboarding
        user_profile = Profile.objects.filter(user = request.user).first()
        print(user_profile)
        if user_profile is None:
            return render(request,'html/onboarding.html')
            logger.error(msg="User is not suppose to have a profile , if user have a profile, redirect them to dashboard")
        else: return redirect('origin_dashboard')


class ProfileSettings(LoginRequiredMixin, View):
    """FOR PROFILE IN THE ASIDE"""
    def get(self, request):
        user_profile = Profile.objects.filter(user = request.user).order_by('tier').first()
        if user_profile is None:
            #incase user does not have tier configured and want to access this page, dont allow
            messages.warning(request, message="Please Finish your onboarding before accessing this page, head to login and sigin in with you creedentials and you will be taken to onboarding")
            return render(request, 'html/full_screen_message.html')
        return render(request, 'html/profile.html')    
  
class Dashboard(LoginRequiredMixin, View):
    """THE FIRST LANDING PAGE WHEN DASHBOARD IS CLICKED, COMES RIGHT AFTER ONBOARDING DONE ALSO"""
    login_url = '/v1/login/'
    def get(self, request):
        user_profile = Profile.objects.filter(user = request.user).order_by('tier').first()
        if user_profile is None:
            #incase user does not have tier configured and want to access this page, dont allow
            messages.warning(request, message="Please Finish your onboarding before accessing this page, head to login and sigin in with you creedentials and you will be taken to onboarding")
            return render(request, 'html/full_screen_message.html')
        
        commitment_istance = Commitment.objects.filter(user=request.user, is_active=True)
        consistency_pct = [i.streak_count for i in  commitment_istance] #different from zeal score --- loop through streak; sum them all and divide by all
        c_pct = sum(consistency_pct) / (len(consistency_pct)+1) #i added one to curb the issue of division by zero
        data = {
            'tier' : user_profile.tier,
            'Upcoming_milestone': 6 - timezone.now().weekday(),
            'ai_insight_active' : user_profile.ai_insight_active,
            'social_mode' : user_profile.social_mode,
            'total_active_commitments': commitment_istance.count(),
            'consistency_pct': c_pct,  
             'total_entries': Entries.objects.filter(commitment_key__user = request.user).count(),       #Hold usr current tier
             'theme_mode': request.COOKIES.get("sd-theme", user_profile.theme.lower()),
            
            'public_searchable_username ' : user_profile.public_searchable_username,
            'zeal_score' : user_profile.zeal_score
            
        }
        return render(request, 'html/dashboard.html', data)


class EachCommitmentView(LoginRequiredMixin, View):
    """This is for viewing each commitment data, note and every other details based on A commitment"""
    def get(self, request, commitment_key): return self.post(request, commitment_key=commitment_key)
    def post(self, request, commitment_key):
        messages.info(request, message=f"This page for {request.user.username} with commitment id: {commitment_key} is still being built, Check back later")
        return render(request, 'html/full_screen_message.html')
   
    
class DashboardCommitmentView(LoginRequiredMixin, View):
    """The commitment page on dashboard contents"""
    login_url= '/v1/login/'
    def get(self, request):
        
        istance = Profile.objects.filter(user = request.user).first()
        if istance is None:
            #incase user does not have tier configured and want to access this page, dont allow
            messages.warning(request, message="Please Finish your onboarding before accessing this page, head to login and sigin in with you creedentials and you will be taken to onboarding")
            return render(request, 'html/full_screen_message.html')
        return render(request, 'html/commitments.html', {'tier' : istance})
    
    