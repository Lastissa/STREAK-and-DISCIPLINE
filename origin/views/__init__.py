from .auth_view import *            # Handles anything authentication, almost all my class here requires login
from .utility_view import *         # Handles view that middleman view like redirecting and any view does not stay in one place but act as middle man
from .dashboard import *            # Handles anything that have to do with user interaction when log in e.g dashboard, dashbpard setting etc; stuff that only work when user is logged in. 
from .debug_purpose import *        # Only for debugging purpose only currently;
from .normal_view import *          # The regs, return html and UI's
from .json_only_view import *       # Handles anything tht returns only json
from .danger import *               #handles dangerous zone
from .staff import *                # Handles anything staff related except the backdoor
from .cron_job_View import *        #For the background task i need to handle since i am using render free
#NOTE: "from .normal_view import *" used to be duplicated here (imported a second time,
#after json_only_view). Wildcard imports resolve last-import-wins on name collisions, so
#that duplicate line was silently letting normal_view.py's stale/broken PartnerWidget
#override the fixed one in json_only_view.py. Removed - keep each view class defined in
#exactly one file to avoid this happening again.

