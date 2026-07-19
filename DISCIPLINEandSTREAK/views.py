from django.shortcuts import redirect
from django.views import View

#for redirection based on version
class Home(View):
    def get(self, request):
        return redirect('origin_home')