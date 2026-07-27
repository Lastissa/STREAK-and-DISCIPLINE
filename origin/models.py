from django.contrib.auth.models import AbstractBaseUser,BaseUserManager, PermissionsMixin
from django.db import models


#to replace the choice since django does not validate them - i will use custom validator istead
class ChoicesValidatorInModels:
    def __init__(self):
        """Incase attackers want to edit the content of the incoming values that make use of certain tect, this will block them"""
        
        self.tier = ['free', 'premium', 'gold']
        self.theme = ['dark', 'light']
        self.social_mode = ['solo', 'partner']
        self.commitment_category = ['other', 'fitness', 'study', 'work', 'health', 'mindset', 'growth']
        self.report_delivery_mode = ['email', 'whatsapp', 'push']
        self.mood = [
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
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
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
    # profile_img_url = models.URLField(max_length=500, blank=True, null=True)
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
    # partner_list = models.JSONField() #this will store only the userid in a list, the downslide if user change their username, their user id in this list might be useless, maybe i will inform user to upsate their partner that they have updated their username and their partner should look it up again and delete the old one
    
    
    def __str__(self):
        return self.user.email



#each individual commitment - can be many and to track the count, i jsut use .object.fileter(xxx).count()
class Commitment(models.Model):
    user = models.ForeignKey(CustomeUser, on_delete=models.CASCADE) # a user can have more than one commitment
    is_active =  models.BooleanField(default=True) #This tell the current state of a commitment wether its active or not
    streak_count = models.IntegerField(null=False,default=1)#this tell the consequtive rows in a day user have showed up, reset on each day miss
    checkin_time = models.TimeField(blank=False, null=False,default='21:00') #time user is expected to have checked in for that day -send email if they have not check in at that time
    what = models.CharField(blank= False, null= False,max_length=120) #what this commitment is about?
    category = models.CharField(max_length=20, default = custom_val.commitment_category[0]) #under which category does this commitment fall under?
    why = models.TextField(blank=True) # can be long text for showing why the user is dedicated to this commitment 
    minimum_effort = models.CharField(max_length=120, blank=True) #to evaluate user user expected note on days where they are not tht strong but they still show up
    goal_days = models.PositiveIntegerField(blank=False, null=False)   # 0 means forever
    created_at = models.DateTimeField(auto_now_add=True) #to track current day in streak and know the end of streak
    
    #sending email
    last_check_in = models.DateTimeField(null=True, blank=False, default=None)#to track user last check in istead of going to look at that entry - on initial , its None
    reminder_active = models.BooleanField(default=True)#wether to on reminder or not
    user_selected_reminder_time = models.TimeField(null=True, blank=False, default=None)#the time to which email will be sent to user
    #send via email a at the user specified reminder time, and a general mail should be send few minutes before the day ends to all user who have not been active, thats if user reminder time is at least 5 minutes < than this shcedules time 
    mode_of_delivery = models.CharField(max_length=10, default= custom_val.report_delivery_mode[0])
    whatsapp_number = models.CharField(max_length=20, blank=True) #if the user chooses whtsap so i can save their phone number
    
    def __str__(self):
        return f"{self.user.email} Commitments -- what_name: {self.what}"
    



    
    
    
#this is to link the entries data to the commitment it belong so each commitment can have its data since each pk is unique
class Entries(models.Model):
    commitment_id = models.ForeignKey(Commitment, on_delete=models.CASCADE) #hold each day entry attached to their respective commitment
    commit_at = models.DateField(auto_now_add=True) #the full datetime user wrote this commitment, used for abalytics and also to prevent user from creating new commit on that same dat
    content = models.TextField(blank=True)  #the note for that partiular commit
    mood = models.CharField(max_length=50, blank=True)
    word_count = models.PositiveIntegerField(default=0) #this will be for analysis purpose later
    
    class Meta:
        unique_together = ('commitment_id', 'commit_at') #this make sure this is treated as unique and no duplicate ,
    
    #overide rhe default save so automatically, work count get saved
    def save(self, *args, **kwargs):
        """Custom save to auto dectect the word count of the content"""
        if self.content: self.word_count = len(self.content.split())
        else: self.word_count = 0
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"latest commit for {self.commitment_id.user.email} is {self.commit_at}"

    
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
    