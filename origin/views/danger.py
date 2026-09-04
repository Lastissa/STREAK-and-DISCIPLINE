"""THIS FOLDER CONTAINS VIEWS THAT HAVE GREIVOUS CONSEQUENCES WHEN THEY ARE MESSED WITH"""
import json

from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import JsonResponse


class DeleteUserEntireAccount(LoginRequiredMixin, View):
    """DANGER!!! this delete the current user entire account , it queues the account for the next wiping in the next 7 dasy from deletion"""
    def post(self, request):
        data = json.loads(request.body)
        is_it_really_user = request.user.username == data.get('username', 'empty')
        if is_it_really_user is False:
            return JsonResponse({'message': 'user identity invalid'}, status = 403)
        
        #it is realy user, change their is_active to false and them delete account seven days later
        request.user.is_active = False
        request.user.save()
        return JsonResponse({'message': 'success, you can reactivate your account within the next seven days else otilor'}, status = 201)