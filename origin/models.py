from django.contrib.auth.models import AbstractBaseUser,BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


#to replace the choice since django does not validate them - i will use custom validator istead
class ChoicesValidatorInModels:
    def __init__(self):
        """Incase attackers want to edit the content of the incoming values that make use of certain tect, this will block them"""
        
        self.tier = ['free', 'premium', 'gold']
        self.theme = ['dark', 'light']
        self.partner_limit = {
            self.tier[0]: 1,
            self.tier[1]: 5,
            self.tier[2]: 20
        }
        self.social_mode = ['solo', 'partner']
        self.commitment_category = ['other', 'fitness', 'study', 'work', 'health', 'mindset', 'growth']
        self.report_delivery_mode = ['email', 'whatsapp', 'push']
        self.mood = [
            'minimum', #On days when user check in with minimum effort
            'proud', 'accomplished', 'confident', 'determined', 'focused',
            'motivated', 'disciplined', 'strong', 'unstoppable', 'excited',
            'energetic', 'optimistic', 'inspired', 'passionate', 'courageous',
            'calm', 'peaceful', 'content', 'grateful', 'hopeful',
            'relieved', 'satisfied', 'balanced', 'patient', 'present', 'grounded',
            'loved', 'supported', 'connected', 'appreciated', 'valued',
            'okay', 'meh', 'numb', 'indifferent', 'neutral',
            'distracted', 'restless', 'bored', 'curious',
            'tired', 'exhausted', 'drained', 'lazy', 'unmotivated',
            'sluggish', 'burnt_out', 'sleepy', 'lethargic',
            'worried', 'anxious', 'nervous', 'stressed', 'overwhelmed',
            'uncertain', 'confused', 'hesitant', 'doubtful',
            'frustrated', 'irritated', 'annoyed', 'angry', 'resentful',
            'bitter', 'disappointed', 'discouraged', 'defeated',
            'sad', 'lonely', 'isolated', 'hopeless', 'empty',
            'ashamed', 'guilty', 'regretful', 'worthless', 'broken',
            'grieving', 'depressed',
            'reflective', 'introspective', 'thoughtful', 'nostalgic', 'humbled',
        ]
        self.friendship_status = ['pending', 'accepted', 'rejected']
        self.news_category = [
            'update',               #   SOMETHING WORTH KNOWING LIKE "PRESS THIS BTN TO DO THIS"
            'feature',              #   AN ADDITIOANL UPDATE HAVE BEEN MADE TO THE SITE
            'story',                #   A WILLING USER SHARED THEIR STORY WITH US
            'quotes',               #   REGULAR WORD OF MOTIVATION.
            'announcement',         #   BIGGER NEWS - LAUNCHES, MILESTONES, POLICY CHANGES
            'tips',                 #   SHORT PRACTICAL ADVICE FOR STAYING DISCIPLINED
            'guide',                #   LONGER HOW-TO / WALKTHROUGH CONTENT
            'milestone',            #   COMMUNITY OR PRODUCT MILESTONE (E.G "10,000 USERS")
            'community',            #   SPOTLIGHT ON THE COMMUNITY / LEADERBOARD / PARTNERS
            ]
    

custom_val = ChoicesValidatorInModels()

#For customizing the model manager e.g ........object.....
class CustomManager(BaseUserManager):
    def create_user(self, email, password = None, **kwargs):
        if not email : raise ValueError("Email is required, basic mean of authentication")
        email = email.upper()
        user = self.model(email=email, **kwargs)
        user.set_password(password)
        if 'is_staff' not in kwargs.keys():user.save()#added the if to avoid multiple db saves
        return user
    
    def create_superuser(self, email, password, **kwargs):
        kwargs.setdefault('is_staff', True)
        kwargs.setdefault('is_superuser', True)
        
        user = self.create_user(email, **kwargs)
        user.set_password(password) #set password since create_user will not set password
        user.save()
        return user

#replacement for user model
class CustomeUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, null=False)
    email = models.EmailField(null=False,unique=True)
    url = models.URLField(blank=True, null=True) #for storing user own domain, just temp
    is_active = models.BooleanField(default=True)#for deactivating user account istead of deleting and them delete 7 days later if user really want to delete account
    last_is_active_false_date = models.DateField(auto_now=True)#to know when user deactivated their account and how many days left
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_checkup_notice_sent_at = models.DateTimeField(null=True, blank=True, default=None)#set by the cron job's send_inactivity_checkups() every time a "we miss you" email+push goes out, so the same user isn't re-notified every single tick - only once per 4 days of continued inactivity
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', ]
    objects = CustomManager()
    
    def __str__(self):
        return self.email
    
    def staff_superuser_active(self):
        """Return true if user is staff, superuser and also active"""
        if self.is_superuser and self.is_active and self.is_staff: return True
        
    
    
#saving credentials for when password reset password so i can verify and delete once they have been used
class PasswordResetToken(models.Model):
    user = models.ForeignKey(CustomeUser, on_delete=models.CASCADE)
    token = models.CharField(blank=False, null=False)
    date_created = models.DateTimeField(auto_now_add=True) #i will check for this for validity period
    
    def __str__(self):
        return "PasswordResetToken"
    


#This hold the user profile as details that can be shared or does not depepnds on security
class Profile(models.Model):
    user = models.OneToOneField(CustomeUser, on_delete=models.CASCADE) #onetoonefeild cos it need to be unique unlike foreignKey
    tier = models.CharField(max_length=20, default= custom_val.tier[0])
    profile_img_url = models.URLField(max_length=500, blank=True, null=True)
    public_searchable_username = models.CharField(max_length=50, blank=True, unique=True) # this is user unique id and can be changed by user anytime, it contain their username from base user and their database CustomeUser pk which is alwasy unique e.g opeyemi01, its used incase the user want to share info other user and to avoid leaking credentials, i adeed unique true cos ope01 to yemi01(yemi01 might already exist)
    leaderboard_optin = models.BooleanField(default=False) #This hides the user from appearing in the public leaderboard analysis -though the streak will still be visible to their partner
    streak_count_is_public_visible = models.BooleanField(default=False) #This hides the streak from showing to the public leaderboard if leaderboard optin is enabled
    ai_insight_active = models.BooleanField(default=True) #this let me know if i can send user data to AI to generate inference
    receive_newsletter = models.BooleanField(default=False) #wether the user want to be receiving random news and tip 
    theme = models.CharField(max_length=10, default= custom_val.theme[0]) # to save user pefrence of theme mode so whenever they login, theme aways adjust back to how they want it
    weekly_report_email_active = models.BooleanField(default=True) #to determine_wether_user want the default weeekly mail
    custom_report_email_active = models.BooleanField(default=False) #send custom emails to user based on prefrence, maybe every three days o 5 days or montly ---not available to free tier 
    social_mode = models.CharField(max_length=10, default=custom_val.social_mode[0]) #to get status of user wether they have partner mode enabled or no one can see their streak
    zeal_score = models.PositiveIntegerField(default=0)  #this look at the active commitments and evaluate a fire count = commitment count * avergae streek of all active streak, purpose is to give user a quick overview on the dashboard
    
    
    def __str__(self):
        return self.user.email



#each individual commitment - can be many and to track the count, i jsut use .object.fileter(xxx).count()
class Commitment(models.Model):
    user = models.ForeignKey(CustomeUser, on_delete=models.CASCADE) # a user can have more than one commitment
    is_active =  models.BooleanField(default=True) #This tell the current state of a commitment wether its active or not
    streak_count = models.IntegerField(null=False,default=0)#this tell the consequtive rows in a day user have showed up, reset on each day miss
    checkin_time = models.TimeField(blank=False, null=False,default='21:00') #time user is expected to have checked in for that day -send email if they have not check in at that time
    what = models.CharField(blank= False, null= False,max_length=120) #what this commitment is about?
    category = models.CharField(max_length=20, default = custom_val.commitment_category[0]) #under which category does this commitment fall under?
    why = models.TextField(blank=True) # can be long text for showing why the user is dedicated to this commitment 
    minimum_effort = models.CharField(max_length=120, blank=True) #to evaluate user user expected note on days where they are not tht strong but they still show up
    goal_days = models.PositiveIntegerField(blank=False, null=False)   # 0 means forever
    created_at = models.DateTimeField(auto_now_add=True, blank=False, null=False) #to track current day in streak and know the end of streak
    
    #sending email
    last_check_in = models.DateTimeField(null=True, blank=False, default=None)#to track user last check in istead of going to look at that entry - on initial , its None
    reminder_active = models.BooleanField(default=True)#wether to on reminder or not
    user_selected_reminder_time = models.TimeField(null=True, blank=False, default=None)#the time to which email will be sent to user
    #send via email a at the user specified reminder time, and a general mail should be send few minutes before the day ends to all user who have not been active, thats if user reminder time is at least 5 minutes < than this shcedules time 
    mode_of_delivery = models.CharField(max_length=10, default= custom_val.report_delivery_mode[2]) #defaults to push now since email delivery is currently unreliable in production
    whatsapp_number = models.CharField(max_length=20, blank=True) #if the user chooses whtsap so i can save their phone number using +xxxxxxxxxxxxxxx
    last_reminder_sent_at = models.DateTimeField(null=True, blank=True, default=None)   #to keep track for reminders for commitment
    pending_notice = models.CharField(max_length=255, blank=True, default='') #set by the cron job (e.g "streak reset - you missed your 24hr check-in window") and flushed out to the user as a django message next time they load a page that touches this commitment
    completed_at = models.DateTimeField(null=True, blank=True, default=None) #set when goal_days is reached (100%) - NOTE: this NO LONGER deactivates the commitment (see complete_expired_commitments in utility/maintenance_engine.py), its only job now is to flag the commitment as "done" so the dashboard/commitment page can replay the standing-ovation celebration. The commitment stays is_active=True and keeps living its life (user can keep journaling on it if they want).

    #---- soft-delete / "recoverable delete" support ----
    #the button that used to be labelled "Archive" is now labelled "Delete" everywhere in the UI, but under
    #the hood it still just flips is_active to False (soft delete) - nothing about the DB behaviour changed,
    #only the wording shown to the user + this new timestamp so we know WHEN it happened.
    deactivated_at = models.DateTimeField(null=True, blank=True, default=None) #stamped the moment the user hits "Delete" (EachCommitmentArchive). Used two ways: (1) the profile page reads it to show a "recover within 24 hours" countdown, (2) the maintenance cron (purge_deleted_commitments) only hard-deletes a commitment once THIS is more than 24h in the past - never based on is_active alone anymore, so nothing gets permanently wiped before the 24h recovery window has genuinely passed.

    #---- milestone celebrations (50% / 100% of goal_days) ----
    #Percentage itself is NOT stored (it's computed on the fly from created_at/goal_days -
    #see Commitment.progress_percent below) - these two booleans exist purely so the
    #DASHBOARD's one-time "hooray"/"standing ovation" toast only ever fires ONCE per
    #commitment instead of on every single dashboard visit. The commitment's OWN detail
    #page is different on purpose: it replays the 100% celebration on every visit once
    #completed_at is set (see EachCommitmentView), no flag needed there.
    milestone_50_notified = models.BooleanField(default=False) #flips True the first time the dashboard has shown the 50% celebration for this commitment
    milestone_100_notified = models.BooleanField(default=False) #flips True the first time the dashboard has shown the 100% celebration for this commitment (separate from completed_at, which is what the commitment detail page checks to decide whether to replay ITS celebration)

    def progress_percent(self) -> int:
        """0-100 progress toward goal_days, based on how many days old the commitment is
        (same "age in days" math complete_expired_commitments in utility/maintenance_engine.py
        uses for 100%). goal_days=0 means "forever" - no percentage makes sense, so this
        always returns 0 for those and they never trigger a milestone celebration."""
        if not self.goal_days:
            return 0
        age_days = (timezone.now().date() - self.created_at.date()).days
        return max(0, min(100, round((age_days / self.goal_days) * 100)))
    def __str__(self):
        return f"{self.user.email} Commitments -- what_name: {self.what}; status -> {self.is_active}"
    



    
    
    
#this is to link the entries data to the commitment it belong so each commitment can have its data since each pk is unique
class Entries(models.Model):
    commitment_key = models.ForeignKey(Commitment, on_delete=models.CASCADE) #hold each day entry attached to their respective commitment
    commit_at = models.DateField(auto_now_add=True) #the full datetime user wrote this commitment, used for abalytics and also to prevent user from creating new commit on that same dat
    content = models.TextField(blank=True)  #the note for that partiular commit
    mood = models.CharField(max_length=50, blank=True, default= custom_val.mood[0])
    word_count = models.PositiveIntegerField(default=0) #this will be for analysis purpose later
    
    class Meta:
        unique_together = ('commitment_key', 'commit_at') #this make sure this is treated as unique and no duplicate ,
    
    #overide rhe default save so automatically, work count get saved
    def save(self, *args, **kwargs):
        """Custom save to auto dectect the word count of the content"""
        if self.content: self.word_count = len(self.content.split())
        else: self.word_count = 0
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"latest commit for {self.commitment_key.user.email} is {self.commit_at}"

    
#this tracks current state of friendship like pending, accepted, rejected and date they are sent   
class Friendship(models.Model):
    from_user = models.ForeignKey(CustomeUser, on_delete= models.CASCADE, related_name='from_user_rn') #this hold who send the request
    to_user = models.ForeignKey(CustomeUser, on_delete= models.CASCADE, related_name='to_user_rn') #this is the receiver of the friend request
    status = models.CharField(max_length=10, default = custom_val.friendship_status[0]) #curent state of the request, allowed to be updated by both sender and receiver
    created_at = models.DateTimeField(auto_now_add=True) #timestamp as to whn the interaction was created
    updated_at = models.DateTimeField(auto_now=True) # last action perfomed update , will auto update anytime i call save 
    
    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"
    
    class Meta:
        unique_together = ('from_user', 'to_user') #this make sure this is treated as unique and no duplicate , i will just edit the status each time istead of creating new column of the same two users
        
        
        
class News(models.Model):
    title = models.CharField(max_length=220, blank=False, null= False, unique=True)          # News title
    tag = models.CharField(max_length=30, blank=False, null= False)            # Category of post based on the custom choiced class
    excerpt = models.CharField(max_length=1001, blank=False, null= False)        # Frist few lines of the full text
    date = models.DateField(auto_now_add= True)                 # Date created
    read_time = models.IntegerField(blank=False, null=False)    # Estimated time user is suppose to read it for
    banner = models.URLField(null=True, blank=True)                        # IF the news have a banner and the image of the banner
    featured = models.BooleanField(default=True)               # for full width set to true
    actual_content = models.TextField(default="", blank=True, null= True)# This hold the actual content that will be displayed on its own page

    #---- user-submitted stories (tag == 'story') ----
    #Staff-authored posts (created from staff/create_blog) leave this NULL - that's how the blog
    #template tells a staff post apart from a community one and shows the right badge ("Staff" vs
    #"Community Story" / "user typed"). Ordinary users can only ever create tag='story' posts via the
    #public "share your story" form on the blog page.
    submitted_by = models.ForeignKey(CustomeUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_stories') #who actually wrote this (null for staff-authored posts). Kept even when is_anonymous=True, purely for internal moderation - the byline shown publicly still respects is_anonymous.
    is_anonymous = models.BooleanField(default=False) #user's own choice at submission time - when True the byline shown on the blog reads "Anonymous" instead of their username

    class Meta:
        unique_together= ('title', 'tag',)

    def __str__(self):
        return "News"

    def is_staff_authored(self) -> bool:
        """True for posts written by staff through the staff hub (submitted_by is empty).
        Used purely for the small badge shown on the blog card ('Staff' vs 'User typed')."""
        return self.submitted_by_id is None
    
    
    
    
class PushSubscription(models.Model):
    user = models.ForeignKey(CustomeUser, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PushSubscription for {self.user.email}"
    
#every new signup starts on premium automatically for 7 days, then the cron job downgrades them back to free once expires_at has passed (unless they genuinely paid, which is out of scope of this model - this only tracks the FREE TRIAL)
class PremiumTrial(models.Model):
    user = models.OneToOneField(CustomeUser, on_delete=models.CASCADE, related_name='premium_trial')
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField() #started_at + 7 days, set on creation
    downgraded = models.BooleanField(default=False) #flips true the moment the cron job knocks the profile tier back down to free, so we never try to downgrade the same user twice
    downgraded_at = models.DateTimeField(null=True, blank=True, default=None)

    def __str__(self):
        return f"Premium trial for {self.user.email} (expires {self.expires_at:%Y-%m-%d})"


class StaffTempToken(models.Model):
    email = models.EmailField()
    token = models.CharField(max_length=10)
    type = models.CharField(max_length=20)          #   STAFF OR ADMIN; SO TELL THE KIND OF INCOMING TOKEN AS STAFF TOKEN WILL ALWSY START WITH st- AND ADMIN TOKEN ALWASY START WITH  ad-
    time_sent = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Staff registration tokens : {self.email}"