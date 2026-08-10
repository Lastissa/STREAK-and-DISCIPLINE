from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as V_Error
from django.contrib import messages
from django.shortcuts import redirect, render
from django.db import transaction, IntegrityError, models
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin

from utility.send_bulk_email import send_news_email

from ..models import StaffTempToken, News, Profile, ChoicesValidatorInModels
from utility.config import Static
from utility.email_sending import send_staff_access_code_email
from utility.file_upload import upload_news_banner

import json, random, logging

logger = logging.getLogger(__name__)


class StaffSignup(View):
    def get(self, request):
        messages.info(request=request, message="Staff accounts require an access code from an admin before you can sign up.")
        return render(request, 'html/staff_signup.html')


class StaffMakeTokenRequest(View):
    """INCHARGE OF SENDING EMAIL TO THE OFFICIAL GMAIL WITH TOKEN FOR STAFF TO VERIFY THEM BEFORE ACCOUNT CREATION CAN START"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            email = (data.get('email') or '').strip()
            username = (data.get('username') or '').strip()

            validate_email(email)
            if not username:
                return JsonResponse({'message': 'Please choose a username before requesting a code.'}, status=400)

            # block requesting a code for an email that already has an account and is a staff
            if get_user_model().objects.filter(email__iexact=email, is_staff = True).exists():
                return JsonResponse({'message': 'You are not allowed to create account staff, contact admin for necessary actions -old user '}, status=409)

            # simple rate limit so one person can't spam the official inbox with requests
            rate_key = f"staff_token_request_{email.upper()}"
            if cache.get(rate_key):
                return JsonResponse({'message': 'A code was already requested for this email a moment ago. Please wait a minute and try again.'}, status=429)
            cache.set(rate_key, True, timeout=60)

            # build a fresh token, always prefixed 'st-' for staff (admin tokens, if ever
            # issued directly in the db/admin, use 'ad-' — see StaffTempToken.type)
            raw_token = "".join(random.sample("123456789abcdefghijklmnopqrsuvwxyzABCDEFGHIJKLMNOPRSTUVWXYZ", Static.token_lenght()))
            token = f"st-{raw_token}"

            # any previous unclaimed request for this exact email is now stale, replace it
            StaffTempToken.objects.filter(email__iexact=email, type='staff').delete()
            StaffTempToken.objects.create(email=email, token=token, type='staff')

            # synchronous on purpose: if this fails we want to tell the requester right away
            # rather than have them wait on a code that never arrived
            send_staff_access_code_email(token=token, requester_email=email)

            return JsonResponse({
                'message': f"Request received. An access code has been sent to our official inbox — an admin will share it with you personally. Codes expire after {int(Static.token_expiry_time() / 60)} minutes."
            }, status=200)

        except V_Error:
            return JsonResponse({'message': 'Please enter a valid email address.'}, status=400)
        except Exception as e:
            logger.error(msg=f"staff token request failed: {e}")
            return JsonResponse({'message': 'Something went wrong requesting your access code. Please refresh and try again.'}, status=500)


class VerifyStaffTokenAndCreateAccount(View):
    """INCHARGE OF VERIFYING THE TOKEN STAFF BOUGHT AND VERIFY IT AGAINT BOTH THEIR STAFF TYPE AND TABLE"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            email = (data.get('email') or '').strip()
            username = (data.get('username') or '').strip()
            password1 = data.get('password1') or ''
            password2 = data.get('password2') or ''
            token = (data.get('token') or '').strip()

            validate_email(email)
            if not username:
                return JsonResponse({'message': 'Username is required.'}, status=400)
            if not token:
                return JsonResponse({'message': 'Please enter the access code an admin gave you.'}, status=400)
            if len(password1) < 8:
                return JsonResponse({'message': 'Password must be at least 8 characters.'}, status=400)
            if password1 != password2:
                return JsonResponse({'message': 'Passwords do not match.'}, status=400)

            # if get_user_model().objects.filter(email__iexact=email).exists():
            #     return JsonResponse({'message': 'An account with this email already exists. Please login instead.'}, status=409)

            token_istance = StaffTempToken.objects.filter(email__iexact=email, token=token, type='staff').first()
            if token_istance is None:
                return JsonResponse({'message': 'Invalid access code. Please recheck the code with an admin or request a new one.'}, status=400)

            token_expired = (timezone.now() - token_istance.time_sent).total_seconds() >= Static.token_expiry_time()
            if token_expired:
                token_istance.delete()
                return JsonResponse({'message': f"This access code has expired ({int(Static.token_expiry_time() / 60)} minute limit). Please request a new one."}, status=400)

            with transaction.atomic():
                # CustomManager.create_user() intentionally skips the initial save() when
                # 'is_staff' is passed in, the same way create_superuser() does — so we save
                # it ourselves right after.
                user = get_user_model().objects.create_user(email=email, username=username, password=password1, is_staff=True)
                user.save()
                token_istance.delete()

            logger.warning(msg=f"staff account created for {email}")
            messages.info(request, message = "Staff Account Created, You Have Been Redirected To Login.")
            return JsonResponse({'message': 'success'}, status=200)

        except V_Error:
            return JsonResponse({'message': 'Please enter a valid email address.'}, status=400)
        except Exception as e:
            logger.error(msg=f"staff account verification failed: {e}")
            return JsonResponse({'message': 'Something went wrong creating your account. Please try again.'}, status=500)


class AccountWithStaffStatus(View):
    """ON REGULAR LOGIN , THIS WILL TRY TO DECTECT THE STATUS OF THE USER , IF STAFF OR SUPERUSER DECTECTED? BEFORE GOING TO ONBOARDING OR DASHBOARD, THIS ONE IS LIKE THE MIDDLEMAN THAT DECTECS IF USER IS STAFF AND TRY TO REDIRECT THEM TO admin colsole BUT IT ASK FIRST? YOU ARE A STAFF MEMBER? DO YOU WANT TO CONTINUE HERE OR WANT TO BEREDIRETED TO THE ADMIN CONSOLE?"""
    def get(self, request):
        STAFF_TOOLS = [
            {
                'title': 'Blog & News',
                'description': 'Publish, edit and manage the News posts shown on the public Blog & Updates page.',
                'icon': 'fa-newspaper',
                'url_name': 'origin_blog',
                'status': 'live',
            },
            {
                'title': 'User Management',
                'description': 'Search users, deactivate/reactivate accounts, and change subscription tier.',
                'icon': 'fa-users-gear',
                'url_name': 'origin_staff_users',
                'status': 'live',
            },
            {
                'title': 'Active Sessions',
                'description': 'See who is currently logged in right now, pulled straight from the session table.',
                'icon': 'fa-tower-broadcast',
                'url_name': 'origin_staff_users',
                'status': 'live',
            },
            # ---------------------------------------------------------------
            # ADD FUTURE STAFF TOOLS HERE, following the exact shape above.
            # Leave 'status': 'soon' and 'url_name': None until the tool's
            # view + url actually exist, then flip it to 'live' and add the
            # real url_name once it's ready to use.
            # ---------------------------------------------------------------
        ]
        if not (request.user.is_staff or request.user.is_superuser):
                    return redirect('origin_dashboard')
        
        tools = []
        for tool in STAFF_TOOLS:
            entry = dict(tool)
            entry['url'] = reverse(tool['url_name']) if entry.get('status') == 'live' and tool.get('url_name') else None
            tools.append(entry)
        
        print(request.COOKIES.get('sd-theme', ''))
        if request.user.is_staff: return render(request, 'html/staff_hub.html', {'staff_tools': tools, 'page_theme': request.COOKIES.get('sd-theme', '')})
        messages.error(request, message="YOU ARE NEVER SUPPOSE TO  SEE THIS BUT IF SEEN , AN ALSO BIG MAX REDIRECT ERROR WAS ABOUT TO HAPPE BUT I CAUGJHT IT HERE")
        return render(request, 'html/full_error_message.html')


class CreateBlog(View):
    """For staff to create news, i can still use the admin but who knows , i might grow and need more hand"""
    def post(self, request):
        data = request.POST
        banner = request.FILES.get('banner')
        if not request.user.is_staff: return JsonResponse({'message': 'Permission Denied'}, status = 403)

        #real, specific errors instead of a blanket "Server Error" - a missing field, an
        #over-length value, and an actual server crash are three very different problems
        #and staff debugging this needs to be able to tell them apart at a glance
        required_fields = ['title', 'tag', 'excerpt', 'read_time', 'featured', 'actual_content']
        missing = [f for f in required_fields if f not in data or str(data.get(f)).strip() == '']
        if missing:
            return JsonResponse({'message': f"Missing required field(s): {', '.join(missing)}"}, status=400)

        MAX_LENGTHS = {'title': 220, 'tag': 30, 'excerpt': 1000}
        for field, limit in MAX_LENGTHS.items():
            if len(str(data[field])) > limit:
                return JsonResponse({'message': f"'{field}' is {len(str(data[field]))} characters, but the database column only allows {limit}. Trim it and try again."}, status=400)

        try:
            read_time = int(data['read_time'])
        except (TypeError, ValueError):
            return JsonResponse({'message': f"'read_time' must be a whole number, got '{data.get('read_time')}'."}, status=400)

        try:
            with transaction.atomic():
                news_ist = News.objects.create(
                    title = data['title'],
                    tag = data['tag'],
                    excerpt = data['excerpt'],
                    read_time = read_time,
                    featured = str(data['featured']).strip().upper() == "TRUE",
                    actual_content = data['actual_content']
                )

                if banner:
                    output = upload_news_banner(uploaded_file= banner, id = news_ist.id)
                    news_ist.banner = output['url']

                news_ist.full_clean()
                news_ist.save()

            if banner:
                try:
                    send_news_email(news_instance=news_ist)
                except Exception as mail_err:
                    #the post itself succeeded - a failed notification email should never look like a failed post
                    logger.error("News published (id=%s) but the notification email failed: %s", news_ist.id, mail_err)
                    return JsonResponse({'message': 'Post published, but the notification email failed to send (this is likely the known production email issue, not a post failure).'}, status=200)
            return JsonResponse({'message': 'Post published successfully' + (' with banner.' if banner else ' without a banner.')}, status = 200)

        except IntegrityError as e:
            #most commonly: title isn't unique (News.title has unique=True)
            logger.error("News publish IntegrityError: %s", e)
            if 'title' in str(e).lower() or 'unique' in str(e).lower():
                return JsonResponse({'message': f"A post with the title \"{data['title']}\" already exists. Titles must be unique."}, status=400)
            return JsonResponse({'message': f"Database rejected this post: {e}"}, status=400)
        except DjangoValidationError as e:
            logger.error("News publish ValidationError: %s", e)
            return JsonResponse({'message': f"Validation failed: {'; '.join(e.messages) if hasattr(e, 'messages') else str(e)}"}, status=400)
        except Exception as e:
            #still logged with full context server-side, but staff (the only people who can
            #hit this endpoint) also get the real reason back instead of a dead-end message
            logger.error("Staff news upload failed unexpectedly: %s", e, exc_info=True)
            return JsonResponse({'message': f"Unexpected server error: {e}"}, status = 500)


class EditBlog(View):
    """Staff-only edit of an existing post - title/tag/excerpt/read_time/featured/content.
    Banner changes go through ChangeBlogBanner below so a banner-only update doesn't
    force staff to resend the whole article body."""
    def post(self, request, pk):
        if not request.user.is_staff: return JsonResponse({'message': 'Permission Denied'}, status = 403)
        post = News.objects.filter(pk=pk).first()
        if post is None:
            return JsonResponse({'message': f'No news post found with id {pk}.'}, status=404)

        data = request.POST
        MAX_LENGTHS = {'title': 220, 'tag': 30, 'excerpt': 160}
        for field, limit in MAX_LENGTHS.items():
            if field in data and len(str(data[field])) > limit:
                return JsonResponse({'message': f"'{field}' is {len(str(data[field]))} characters, but the database column only allows {limit}. Trim it and try again."}, status=400)

        if 'read_time' in data:
            try:
                post.read_time = int(data['read_time'])
            except (TypeError, ValueError):
                return JsonResponse({'message': f"'read_time' must be a whole number, got '{data.get('read_time')}'."}, status=400)

        for field in ('title', 'tag', 'excerpt', 'actual_content'):
            if field in data and str(data[field]).strip() != '':
                setattr(post, field, data[field])
        if 'featured' in data:
            post.featured = str(data['featured']).strip().upper() == 'TRUE'

        try:
            with transaction.atomic():
                post.full_clean()
                post.save()
        except IntegrityError as e:
            logger.error("News edit IntegrityError (id=%s): %s", pk, e)
            if 'title' in str(e).lower() or 'unique' in str(e).lower():
                return JsonResponse({'message': f"A post with the title \"{data.get('title')}\" already exists. Titles must be unique."}, status=400)
            return JsonResponse({'message': f"Database rejected this edit: {e}"}, status=400)
        except DjangoValidationError as e:
            logger.error("News edit ValidationError (id=%s): %s", pk, e)
            return JsonResponse({'message': f"Validation failed: {'; '.join(e.messages) if hasattr(e, 'messages') else str(e)}"}, status=400)
        except Exception as e:
            logger.error("Staff news edit failed unexpectedly (id=%s): %s", pk, e, exc_info=True)
            return JsonResponse({'message': f"Unexpected server error: {e}"}, status=500)

        return JsonResponse({'message': 'Post updated successfully.'}, status=200)


class ChangeBlogBanner(View):
    """Staff-only: replace just the banner image on an existing post. upload_news_banner
    uses a deterministic public_id (news_banner_<id>) with overwrite=True, so this
    naturally replaces the old image at the same Cloudinary slot rather than leaking
    an orphaned upload every time someone swaps the picture."""
    def post(self, request, pk):
        if not request.user.is_staff: return JsonResponse({'message': 'Permission Denied'}, status = 403)
        post = News.objects.filter(pk=pk).first()
        if post is None:
            return JsonResponse({'message': f'No news post found with id {pk}.'}, status=404)

        banner = request.FILES.get('banner')
        if not banner:
            return JsonResponse({'message': 'No image file was attached to this request.'}, status=400)

        try:
            output = upload_news_banner(uploaded_file=banner, id=post.id)
            post.banner = output['url']
            post.full_clean()
            post.save()
        except Exception as e:
            logger.error("News banner change failed (id=%s): %s", pk, e, exc_info=True)
            return JsonResponse({'message': f"Image upload failed: {e}"}, status=500)

        return JsonResponse({'message': 'Banner updated successfully.', 'banner_url': post.banner}, status=200)


class DeleteBlog(View):
    """Staff-only: permanently remove a post. Unlike user commitments, news posts are
    site content, not personal data, so this is a normal hard delete - no soft-delete/
    cron-purge dance needed here."""
    def post(self, request, pk):
        if not request.user.is_staff: return JsonResponse({'message': 'Permission Denied'}, status = 403)
        post = News.objects.filter(pk=pk).first()
        if post is None:
            return JsonResponse({'message': f'No news post found with id {pk}.'}, status=404)
        title = post.title
        post.delete()
        return JsonResponse({'message': f'"{title}" was deleted.'}, status=200)
    
    
class StaffView(LoginRequiredMixin, View):
    pass


def _staff_gate(request):
    """Shared guard for every staff-only view below - not a real permission system, just
    consistent with how the rest of this app checks is_staff inline."""
    return request.user.is_staff or request.user.is_superuser


class StaffUsersPage(LoginRequiredMixin, View):
    """The page itself - search box + results table + tier editor + active-sessions
    panel all live here so staff have one place to manage accounts."""
    def get(self, request):
        if not _staff_gate(request):
            return redirect('origin_dashboard')
        return render(request, 'html/staff_users.html', {
            'page_theme': request.COOKIES.get('sd-theme', ''),
            'tier_choices': ChoicesValidatorInModels().tier,
        })


class StaffUserSearch(LoginRequiredMixin, View):
    """?q= matches on username or email (icontains). Never returns password hashes or
    anything beyond what staff actually need to act on an account."""
    def get(self, request):
        if not _staff_gate(request):
            return JsonResponse({'message': 'Permission Denied'}, status=403)

        q = request.GET.get('q', '').strip()
        if not q:
            return JsonResponse({'message': 'Type something to search for.', 'results': []}, status=200)

        User = get_user_model()
        users = User.objects.filter(models.Q(username__icontains=q) | models.Q(email__icontains=q)).order_by('-date_joined')[:25]

        results = []
        for u in users:
            profile = Profile.objects.filter(user=u).first()
            results.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'is_active': u.is_active,
                'is_staff': u.is_staff,
                'tier': profile.tier if profile else None,
                'date_joined': u.date_joined.strftime('%b %d, %Y') if u.date_joined else None,
            })
        return JsonResponse({'message': 'success', 'results': results}, status=200)


class StaffUserManage(LoginRequiredMixin, View):
    """One endpoint, three actions (?action=deactivate|reactivate|set_tier). Deactivating
    a user here is EXACTLY the same mechanism as the user's own "Delete Account" button
    (danger.DeleteUserEntireAccount) - is_active flips to False, nothing is actually
    erased. It is NOT the commitment-delete rule (which hides+hard-deletes) - accounts
    stay fully recoverable/reactivatable by staff at any time."""
    def post(self, request, user_id):
        if not _staff_gate(request):
            return JsonResponse({'message': 'Permission Denied'}, status=403)

        User = get_user_model()
        target = User.objects.filter(pk=user_id).first()
        if target is None:
            return JsonResponse({'message': f'No user found with id {user_id}.'}, status=404)
        if target.is_superuser and target.id != request.user.id:
            return JsonResponse({'message': 'You cannot manage a superuser account from here.'}, status=403)

        action = request.POST.get('action')

        if action == 'deactivate':
            if target.id == request.user.id:
                return JsonResponse({'message': "You can't deactivate your own account from here."}, status=400)
            target.is_active = False
            target.save(update_fields=['is_active'])
            return JsonResponse({'message': f'{target.username} has been deactivated.'}, status=200)

        if action == 'reactivate':
            target.is_active = True
            target.save(update_fields=['is_active'])
            return JsonResponse({'message': f'{target.username} has been reactivated.'}, status=200)

        if action == 'set_tier':
            tier = request.POST.get('tier')
            valid_tiers = ChoicesValidatorInModels().tier
            if tier not in valid_tiers:
                return JsonResponse({'message': f"'{tier}' isn't a valid tier. Choose one of: {', '.join(valid_tiers)}."}, status=400)
            profile = Profile.objects.filter(user=target).first()
            if profile is None:
                return JsonResponse({'message': f'{target.username} has no profile yet (onboarding not finished) - nothing to set a tier on.'}, status=400)
            profile.tier = tier
            profile.save(update_fields=['tier'])
            return JsonResponse({'message': f"{target.username}'s tier set to {tier}."}, status=200)

        return JsonResponse({'message': f"Unknown action '{action}'. Expected deactivate, reactivate, or set_tier."}, status=400)


class StaffActiveSessions(LoginRequiredMixin, View):
    """Pulls straight from django's own session table (django_session) - decodes every
    non-expired session, matches the _auth_user_id it carries back to a user row, and
    lists whoever is currently logged in. This is a live snapshot, not a login-history
    log - a session disappears from here the moment it expires or the user logs out."""
    def get(self, request):
        if not _staff_gate(request):
            return JsonResponse({'message': 'Permission Denied'}, status=403)

        from django.contrib.sessions.models import Session
        from django.contrib.sessions.backends.db import SessionStore

        User = get_user_model()
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now()).order_by('-expire_date')

        seen_user_ids = set()
        rows = []
        for s in active_sessions:
            data = s.get_decoded()
            uid = data.get('_auth_user_id')
            if not uid:
                continue  # anonymous/guest session, nothing to attach to a user
            uid = int(uid)
            user = User.objects.filter(pk=uid).first()
            if user is None:
                continue
            rows.append({
                'user_id': uid,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
                'session_key': s.session_key[:8] + '…',   # never expose the full key
                'expires_at': timezone.localtime(s.expire_date).strftime('%b %d, %Y %I:%M %p'),
            })
            seen_user_ids.add(uid)

        return JsonResponse({
            'message': 'success',
            'sessions': rows,
            'unique_users_online': len(seen_user_ids),
            'total_active_sessions': len(rows),
        }, status=200)