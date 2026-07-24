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
    username = models.CharField(null=False, unique=True)
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
    