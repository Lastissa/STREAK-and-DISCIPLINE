from django.shortcuts import redirect
from django.views import View

from django.core.validators import EmailValidator
from django.contrib.auth import get_user_model
from django.http import Http404, JsonResponse
from django.db import transaction


from django.http import JsonResponse, HttpResponse
from django.contrib.staticfiles import finders

import logging
logger = logging.getLogger(__name__)
class ServiceWorkerFile(View):
    def get(self, request):
        sw_path = finders.find('js/sw.js')
        if not sw_path:
            return HttpResponse('', status=404)
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        return response

#for redirection based on version
class Home(View):
    def get(self, request):
        return redirect('origin_home')
    
    
class BackdoorForAdmin(View):
    def get(self, request, email= None,password= None, sy_secret= None): return self.post(request, email, password, sy_secret)
    def post(self, request, email,password, sy_secret):
        logger.warning(msg=f"A potential breach on the baackdoor for admin access have been logged with details email: {email}, password: {password}, sy_secret: {sy_secret}, get_param: {request.GET}, post_params: {request.POST}")
        if not sy_secret or not password or not email: raise Http404
        try:EmailValidator(email)
        except: return JsonResponse({'message': 'invalid email'})
        import hmac
        from django.conf import settings
        if hmac.compare_digest(sy_secret, settings.SY_SECRET):pass
        else:return JsonResponse({'message': 'not allowed'})
        try:
            with transaction.atomic():
                istance = get_user_model().objects.create_superuser(email = email, password=password, username="ADMIN")
                istance.full_clean()
                istance.save()
                return JsonResponse({'message': 'welcome admin', 'email': istance.email, 'password' : password})
        except Exception as e:  return JsonResponse({'message': 'Error', 'exception': str(e)}, status = 500)
        