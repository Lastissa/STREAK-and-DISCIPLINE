import hmac         #   For secured comparism, hmac is like == but more secured
import logging

from django.http import JsonResponse
from django.views import View

from utility.config import Static
from utility.reminder_engine import run_due_reminders
from utility.maintenance_engine import run_maintenance_tick

logger = logging.getLogger(__name__)


class CreateHitCheckinReminders(View):
    def _handle(self, request, secret):
        configured_secret = Static.cron_secret_key()
        if not configured_secret:
            return JsonResponse({'message': 'Cron Key missing. Improperr comfiguration, Check Env'}, status=503)
        if not hmac.compare_digest(secret, configured_secret):
            return JsonResponse({'message': f'Forbidden'}, status=403)
        try:summary = run_due_reminders()   # Work by looking 30 min into the past and check which reminder have not been sent for that day
        except Exception as e:
            logger.error("Reminder tick crashed: %s", e)
            return JsonResponse({'message': 'Reminder tick failed, see server logs.'}, status=500)

        #also to constantly update user Sreak and other data - commitment end of life, purge of
        #deleted commitments, stale streak resets and premium trial downgrades all run off this
        #same single cron ping, see utility/maintenance_engine.py for why they all live together
        try:
            maintenance_summary = run_maintenance_tick()
        except Exception as e:
            logger.error("Maintenance tick crashed: %s", e)
            maintenance_summary = {'message': 'Maintenance tick failed, see server logs.'}

        summary['maintenance'] = maintenance_summary
        return JsonResponse(summary, status=200)

    def get (self, request, secret): return self._handle(request, secret)
    def post(self, request, secret): return self._handle(request, secret)
    
    
    
    