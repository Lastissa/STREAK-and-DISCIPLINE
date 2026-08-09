import hmac         #   For secured comparism, hmacis like == but more secured
import logging

from django.http import JsonResponse
from django.views import View

from utility.config import Static
from utility.reminder_engine import run_due_reminders

logger = logging.getLogger(__name__)


class CreateHitCheckinReminders(View):
    def _handle(self, request, secret):
        configured_secret = Static.cron_secret_key()
        if not configured_secret:
            return JsonResponse({'message': 'Cron endpoint is not configured on this server.'}, status=503)
        if not hmac.compare_digest(secret, configured_secret):
            return JsonResponse({'message': f'Forbidden'}, status=403)
        try:
            summary = run_due_reminders()   # Work by looking 30 min into the past and check which reminder have not been sent for that day
        except Exception as e:
            logger.error("Reminder tick crashed: %s", e)
            return JsonResponse({'message': 'Reminder tick failed, see server logs.'}, status=500)
        return JsonResponse(summary, status=200)

    def get(self, request, secret): return self._handle(request, secret)
    def post(self, request, secret): return self._handle(request, secret)
    
    
    
    