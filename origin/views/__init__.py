from .auth_view import *            # Handles anything authentication, almost all my class here requires login
from .utility_view import *         # Handles view that middleman view like redirecting and any view does not stay in one place but act as middle man
from .dashboard import *            # Handles anything that have to do with user interaction when log in e.g dashboard, dashbpard setting etc; stuff that only work when user is logged in. 
from .debug_purpose import *        # Only for debugging purpose only currently;
from .normal_view import *          # The regs, return html and UI's
from .json_only_view import *       # Handles anything tht returns only json
from .danger import *               #handles dangerous zone
from .staff import *                # Handles anything staff related except the backdoor
from .normal_view import *

