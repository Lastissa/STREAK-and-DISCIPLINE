from django.contrib.auth.models import AbstractBaseUser,BaseUserManager, PermissionsMixin
from django.db import models


#For customizing the model manager e.g ........object.....
class CustomManager(BaseUserManager):
    def create_user(self, email, password = None, **kwargs):
        if not email : raise ValueError("Email is required, basic mean of authentication")
        email = self.normalize_email(email)
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
    tier = models.CharField(max_length=20, default='free', choices=[
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('gold', 'Gold') 
        ])
    public_searchable_username = models.CharField(max_length=50, blank=True, unique=True) # this is user unique id and can be changed by user anytime, it contain their username from base user and their database CustomeUser pk which is alwasy unique e.g opeyemi01, its used incase the user want to share info other user and to avoid leaking credentials, i adeed unique true cos ope01 to yemi01(yemi01 might already exist)
    leaderboard_optin = models.BooleanField(default=False) #This hides the user from appearing in the public leaderboard analysis
    streak_count_is_public_visible = models.BooleanField(default=False) #This hides the streak from showing to the public leaderboard if leaderboard optin is enabled
    ai_insight_active = models.BooleanField(default=True) #this let me know if i can send user data to AI to generate inference
    receive_newsletter = models.BooleanField(default=False) #wether the user want to be receiving random news and tip 
    display_name = models.CharField(max_length=40, blank=True) #only show if username from customer user is very small or empty
    theme = models.CharField(max_length=10, default='dark', choices=[('dark', 'Dark'), ('light', 'Light')]) # to save user pefrence of theme mode so whenever they login, theme aways adjust back to how they want it
    weekly_report_email_active = models.BooleanField(default=True) #to determine_wether_user want the default weeekly mail
    custom_report_email_active = models.BooleanField(default=False) #send custom emails to user based on prefrence, maybe every three days o 5 days or montly 
    social_mode = models.CharField(max_length=10, default='solo', choices=[('solo', 'Solo'), ('friend', 'With Partner')]) #to get status of user wether they have partner mode enabled or no one can see their streak
    zeal_score = models.PositiveIntegerField(default=0)  #this look at the active commitments and evaluate a fire count = commitment count * avergae streek of all active streak, purpose is to give user a quick overview on the dashboard
    # partner_list = models.JSONField() #this will store only the userid in a list, the downslide if user change their username, their user id in this list might be useless, maybe i will inform user to upsate their partner that they have updated their username and their partner should look it up again and delete the old one
    
    
    def __str__(self):
        return "Profile"

#each individual commitment - can be many and to track the count, i jsut use .object.fileter(xxx).count()
class Commitment(models.Model):
    CATEGORY_CHOICES = [
        ('fitness', 'Fitness'),
        ('study', 'Study'),
        ('work', 'Work'),
        ('health', 'Health'),
        ('mindset', 'Mindset'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(CustomeUser, on_delete=models.CASCADE) # a user can have more than one commitment
    is_active =  models.BooleanField(default=True) #This tell the current state of a commitment wether its active or not
    streak_count = models.IntegerField(default=0)#this tell the consequtive rows in a day user have showed up, reset on each day miss
    checkin_time = models.TimeField(default='21:00') #time user is expected to have checked in for that day
    what = models.CharField(max_length=120) #what this commitment is about?
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES) #under which category does this commitment fall under?
    why = models.TextField(blank=True) # can be long text for showing why the user is dedicated to this commitment 
    minimum_effort = models.CharField(max_length=120) #to evaluate user user expected note on days where they are not tht strong but they still show up
    goal_days = models.PositiveIntegerField(default=365)   # 0 means forever
    created_at = models.DateTimeField(auto_now_add=True) #to track current day in streak and kow the end of streak
    
    #sending email
    last_check_in = models.DateTimeField(null=True, blank=False, default=None)#to track user last check in istead of going to look at that entry
    reminder_active = models.BooleanField(default=True)#wether to on reminder or not
    #send via email a few minutes before commitment is due, 2 hours after commitment is due , and also 12 hours reminder later if the commitment is stil due if commitment for that day have not been updated 
    mode_of_delivery = models.CharField(max_length=10, default='email', choices=[
        ('email', 'Email'), #we will always default to email if user is on free tier
        ('whatsapp', 'WhatsApp'),
        ('push', 'Push'),
    ])
    whatsapp_number = models.CharField(max_length=20, blank=True) #if the user chooses whtsap so i can save their phone number
    
    def __str__(self):
        return "Commitment"
    



    
    
    
#this is to link the entries data to the commitment it belong so each commitment can have its data since each pk is unique
class Entries(models.Model):
    commitment_id = models.ForeignKey(Commitment, on_delete=models.CASCADE) #hold each day entry attached to their respective commitment
    commit_at = models.DateField(auto_now_add=True) #the full datetime user wrote this commitment, used for abalytics and also to prevent user from creating new commit on that same dat
    content = models.TextField(blank=True)  #the note for that partiular commit
    mood = models.CharField(max_length=50, blank=True, choices=[
    # Positive / High Energy
    ('proud', 'Proud'),
    ('accomplished', 'Accomplished'),
    ('confident', 'Confident'),
    ('determined', 'Determined'),
    ('focused', 'Focused'),
    ('motivated', 'Motivated'),
    ('disciplined', 'Disciplined'),
    ('strong', 'Strong'),
    ('unstoppable', 'Unstoppable'),
    ('excited', 'Excited'),
    ('energetic', 'Energetic'),
    ('optimistic', 'Optimistic'),
    ('inspired', 'Inspired'),
    ('passionate', 'Passionate'),
    ('courageous', 'Courageous'),

    # Positive / Calm
    ('calm', 'Calm'),
    ('peaceful', 'Peaceful'),
    ('content', 'Content'),
    ('grateful', 'Grateful'),
    ('hopeful', 'Hopeful'),
    ('relieved', 'Relieved'),
    ('satisfied', 'Satisfied'),
    ('balanced', 'Balanced'),
    ('patient', 'Patient'),
    ('present', 'Present'),
    ('grounded', 'Grounded'),

    # Positive / Social
    ('loved', 'Loved'),
    ('supported', 'Supported'),
    ('connected', 'Connected'),
    ('appreciated', 'Appreciated'),
    ('valued', 'Valued'),

    # Neutral
    ('okay', 'Okay'),
    ('meh', 'Meh'),
    ('numb', 'Numb'),
    ('indifferent', 'Indifferent'),
    ('neutral', 'Neutral'),
    ('distracted', 'Distracted'),
    ('restless', 'Restless'),
    ('bored', 'Bored'),
    ('curious', 'Curious'),

    # Low Energy / Tired
    ('tired', 'Tired'),
    ('exhausted', 'Exhausted'),
    ('drained', 'Drained'),
    ('lazy', 'Lazy'),
    ('unmotivated', 'Unmotivated'),
    ('sluggish', 'Sluggish'),
    ('burnt_out', 'Burnt Out'),
    ('sleepy', 'Sleepy'),
    ('lethargic', 'Lethargic'),

    # Negative / Mild
    ('worried', 'Worried'),
    ('anxious', 'Anxious'),
    ('nervous', 'Nervous'),
    ('stressed', 'Stressed'),
    ('overwhelmed', 'Overwhelmed'),
    ('uncertain', 'Uncertain'),
    ('confused', 'Confused'),
    ('hesitant', 'Hesitant'),
    ('doubtful', 'Doubtful'),

    # Negative / Moderate
    ('frustrated', 'Frustrated'),
    ('irritated', 'Irritated'),
    ('annoyed', 'Annoyed'),
    ('angry', 'Angry'),
    ('resentful', 'Resentful'),
    ('bitter', 'Bitter'),
    ('disappointed', 'Disappointed'),
    ('discouraged', 'Discouraged'),
    ('defeated', 'Defeated'),

    # Negative / Deep
    ('sad', 'Sad'),
    ('lonely', 'Lonely'),
    ('isolated', 'Isolated'),
    ('hopeless', 'Hopeless'),
    ('empty', 'Empty'),
    ('ashamed', 'Ashamed'),
    ('guilty', 'Guilty'),
    ('regretful', 'Regretful'),
    ('worthless', 'Worthless'),
    ('broken', 'Broken'),
    ('grieving', 'Grieving'),
    ('depressed', 'Depressed'),

    # Reflective
    ('reflective', 'Reflective'),
    ('introspective', 'Introspective'),
    ('thoughtful', 'Thoughtful'),
    ('nostalgic', 'Nostalgic'),
    ('humbled', 'Humbled'),
    ]) 
    word_count = models.PositiveIntegerField(default=0) #this will be for analysis purpose later
    
    class Meta:
        unique_together = ('commitment_id', 'commit_at') #this make sure this is treated as unique and no duplicate ,

    def __str__(self):
        return f"latest commit for {self.commitment_id.email} is {self.commit_at}"

    
#this tracks current state of friendship like pending, accepted, rejected and date they are sent   
class Friendship(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    from_user = models.ForeignKey(CustomeUser, on_delete= models.CASCADE, related_name='from_user_rn') #this hold who send the request
    to_user = models.ForeignKey(CustomeUser, on_delete= models.CASCADE, related_name='to_user_rn') #this is the receiver of the friend request
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending') #curent state of the request, allowed to be updated by both sender and receiver
    created_at = models.DateTimeField(auto_now_add=True) #timestamp as to whn the interaction was created
    updated_at = models.DateTimeField(auto_now=True) # last action perfomed update , will auto update anytime i call save 
    
    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"
    
    class Meta:
        unique_together = ('from_user', 'to_user') #this make sure this is treated as unique and no duplicate , i will just edit the status each time istead of creating new column of the same two users
    