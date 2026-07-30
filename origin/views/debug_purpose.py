from django.views import View
from django.http import JsonResponse
from django.contrib.auth import logout

"""debugging purpose so i can logout all user on a device at once"""
class Logout(View):
    def get(self, request): return self.post(request)
    def post(self, request):
        logout(request)
        return JsonResponse({'message' : 'All active members  have been logged out on this device'}, status = 200)
    