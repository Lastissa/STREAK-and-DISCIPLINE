from django.core.cache import cache
import random
from django.utils import timezone
from django.templatetags.static import static
import os


def get_consistency_Value() -> str:
    """Return a string to be set in the consistency text on the landing_page, it send that same string to cache and it remain active for two minutes before it get reset again """
    consistency = cache.get('consistency')
    if consistency is None:
        consistency = random.randint(94,98)
        cache.set('consistency', consistency, timeout=60*2)
        
    return str(consistency)

def get_journal_created_value()->str:
    """set a primary key to the cache on first page visit, on each page visit, get the key, increment it by one and store it back again
    NB: THIS IS JUST A TEMPRORAY SOLUTION"""
    journal_created = cache.get('journal_created')
    if journal_created is None:
        journal_created = 10
    else:journal_created += 0.2
    
    cache.set('journal_created', journal_created)
    
    return str(round(journal_created))

def get_copyright_year():
    return (timezone.now().year)

def intro_word(list_lenght = 2, max = False) -> list:
    """for intro word i will use to show message to user using the message.info() with max saying return all data"""
    words = [
            'He who conquers himself conquers all" - Opeyemi',
            "if 'THEY' can do it, you can do it too",
            'The sky is far but not for someone who is discipline to get there',
            "You don't have to be ready. You just have to start.",
            "Small, consistent actions rewrite who you are.",
            "Motivation fades. Discipline stays.",
            "One honest sentence a day is all it takes.",
            "The person you want to be is built on days like today.",
            "You've lied to yourself long enough. Time to keep your word.",
            "No audience. No applause. Just you keeping promises to yourself.",
            "Tomorrow's pride is paid for with today's discipline.",
            "You're one decision away from a completely different life.",
            "The streak doesn't care about your feelings. It just counts.",
            "Winning the morning wins the day.",
            "Your future self is begging you to start today.",
            "Don't break the chain. Not today.",
            "You can't think your way into discipline. You act your way into it.",
            "Excuses are lies you tell yourself. Discipline is the truth.",
            "One day or day one. You decide.",
            "Champions don't wait for the mood. They build the habit."
                       ]
    if max is True: return words
    return random.sample(words, list_lenght)
    
def template_based_reusables(request):
    """To save data that will be reused i template and i dont have to import them as they will be import automatically like i was in a render function"""
    
    customer_care_phone_number = Static.customer_care_phone_number()
    customer_care_whatsapp_number = Static.customer_care_whatsapp_number()
    footer_copyright_note = f"{timezone.now().year} STREAK & DISCIPLINE. All rights reserved."
    custom_base_url = Static.custom_base_url()
    
    #the current page's SEO/GEO metadata (see SeoGeo class below) - resolved from the URL name so
    #every template just needs one `{% include "reusables/metadata.html" %}` and gets the right
    #title/description/schema for whatever page it is, without every view having to pass it in.
    current_url_name = request.resolver_match.url_name if getattr(request, 'resolver_match', None) else None
    seo = SeoGeo.for_page(current_url_name)
    
    return {
        'customer_care_phone_number' : customer_care_phone_number,
        'customer_care_whatsapp_number': customer_care_whatsapp_number,
        'password_reset_whatsapp_number': Static.password_reset_whatsapp_number(), #dedicated number for the "email didn't arrive" password-reset fallback flow - see PasswordReset view + password_reset.html
        'footer_copyright_note': footer_copyright_note,
        'custom_base_url' : os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8002').split(',')[0],
        'logo_url' : Static.logo_url(),
        'oficial_email': Static.official_email(),
        'seo': seo,
        'mobile_dark_url': static('img/mobile_dark.png'), #'https://res.cloudinary.com/brop3jeq/image/upload/v1784524602/mobile_dark_iuvjyq.png',
        'mobile_light_url': static('img/mobile_light.png'),#'https://res.cloudinary.com/brop3jeq/image/upload/v1784524602/mobile_light_xvuaxj.png',
        'desktop_dark_url' : static('img/desktop_dark.png'),#'https://res.cloudinary.com/brop3jeq/image/upload/v1784524602/desktop_dark_nvt6lr.png',
        'desktop_light_url' : static('img/desktop_light.png'),#'https://res.cloudinary.com/brop3jeq/image/upload/v1784524602/desktop_light_rrgglg.png',
        'font_awesome_all_min_css' : static('fontawesome/css/all.min.css'),
        'advance_landing_page_css': static('cdn/landing_page.css'),
        'advance_landing_page_js': static('cdn/landing_page.js'),
        'user_1': static('img/user_support/user_1.png'),
        'user_2': static('img/user_support/user_2.png'),
        'user_3': static('img/user_support/user_3.png'),
        'user_4': static('img/user_support/user_4.png'),
        'user_5': static('img/user_support/user_5.png'),
        'customer_support_1': static('img/user_support/customer_support_1.jpg'),
        'customer_support_2': static('img/user_support/customer_support_2.jpg'),
        'customer_support_3': static('img/user_support/customer_support_3.jpg'),
        'customer_support_4': static('img/user_support/customer_support_4.jpg'),      
        'free_tier_member' : Static.tier(0),
        'premium_tier_member' : Static.tier(1),
        'gold_tier_member' : Static.tier(2),
        'intro_words': intro_word(max=True)
    }
    
    
class Static:
    
    def __int__(self):
        """For data that will not change and are short """
        pass
    @classmethod
    def token_lenght(self) -> int:
        """Lenght for token in url"""
        return 8
    @classmethod
    def logo_url(self) -> str:
        """Logo url for the site"""
        return 'https://res.cloudinary.com/brop3jeq/image/upload/v1786142757/discipline_and_streak_qrb1nr.png'
    
    @classmethod
    def token_expiry_time(self)-> int:
        """The Official amount of seconds it takes before expirey"""
        return int(10*60)
    @classmethod
    def custom_base_url(self) -> str:
        """the official domain of streak adn discipline"""
        return os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8002').split(',')[0]# incase i need to access base url in templates in situations where i cannot use {% url ''%}
    @classmethod
    def official_email(self) -> str:
        """THE single source of truth for the support email. Every template/view should read
        this (or the `oficial_email` context var it feeds - see template_based_reusables above)
        instead of typing an email address by hand - that's how we previously ended up with two
        or three DIFFERENT support emails hardcoded across different pages."""
        return "sydstrict@gmail.com"

    @classmethod
    def customer_care_phone_number(self) -> str:
        """THE single source of truth for the support phone number (international format, no spaces)."""
        return '+2347013687825'

    @classmethod
    def customer_care_whatsapp_number(self) -> str:
        """General customer-care WhatsApp number (same number as the phone line above, kept as its
        own method since a business could one day want these to differ)."""
        return self.customer_care_phone_number()

    @classmethod
    def password_reset_whatsapp_number(self) -> str:
        """Dedicated WhatsApp number for the password-reset manual fallback ONLY (see
        PasswordReset view / password_reset.html): when hosting hiccups block outgoing email,
        the user DMs their email here and support forwards the reset link by hand. Deliberately
        a separate method from customer_care_whatsapp_number() even though it currently points at
        a different number, so this one flow can be redirected independently later without
        touching general customer care."""
        return '+2348113577875'  # 08113577875 in local (Nigerian) format

    @classmethod
    def whatsapp_link(self, number: str, message: str) -> str:
        """Build a safe wa.me deep-link with the message properly urlencoded. Centralised here so
        every "DM us on WhatsApp" button across the site (password reset, 400 page, etc.) builds
        its link the exact same, correct way instead of hand-rolling %20-encoded strings in
        templates."""
        from urllib.parse import quote
        clean_number = number.replace('+', '').replace(' ', '')
        return f"https://wa.me/{clean_number}?text={quote(message)}"
    
    @classmethod
    def tier(self, tier : int) -> list:
        """returns the features shown in a tier"""
        if tier == 0: return ['5 active commitment','Daily check-in reminder via email','Weekly report summary', '1 partner']
        elif tier == 1: return ['50 active commitments', 'Daily check-in reminder via whatsapp or email and push', 'Advance weekly report summary','Personalized coach','5 partner', 'upload profile picture']
        elif tier == 2: return ['unlimited commitments', 'Daily check-in reminder via whatsapp or email and push + offline reminders','Custom periodical summary','Personalized coach', '20 partners' , 'Advance analytics includes what you should do istead of just data visualization','create Groups', 'Upload profile picture']

    @classmethod
    def vapid_public_key(self) -> str:
        return os.getenv('VAPID_PUBLIC_KEY', '')

    @classmethod
    def vapid_private_key(self) -> str:
        return os.getenv('VAPID_PRIVATE_KEY', '')

    @classmethod
    def vapid_admin_email(self) -> str:
        return os.getenv('VAPID_ADMIN_EMAIL', self.official_email())

    @classmethod
    def vapid_configured(self) -> bool:
        """True only if BOTH halves of the VAPID keypair are set. Checking only the
        public key is a real trap: the public key alone is enough for the browser to
        successfully subscribe (so everything LOOKS like it worked, the person even
        gets the confirmation prompt) but every actual send afterwards fails deep
        inside pywebpush the moment it tries to sign with a missing private key -
        invisibly, since that happens on a background thread with nothing watching."""
        return bool(self.vapid_public_key()) and bool(self.vapid_private_key())

    @classmethod
    def cron_secret_key(self) -> str:
        return os.getenv('CRON_SECRET_KEY', '')
    @classmethod
    def emoji_translator(self):
        """Mappping for each feeling that cam possvile in the database"""
        MOOD_EMOJI = {
        # Positive / High Energy
        'proud': '😄',
        'accomplished': '🏆',
        'confident': '😎',
        'determined': '🔥',
        'focused': '💪',
        'motivated': '🚀',
        'disciplined': '⚡',
        'strong': '🦾',
        'unstoppable': '💥',
        'excited': '🤩',
        'energetic': '⚡',
        'optimistic': '🌤️',
        'inspired': '✨',
        'passionate': '❤️‍🔥',
        'courageous': '🦁',

        # Positive / Calm
        'calm': '🙂',
        'peaceful': '🧘',
        'content': '😊',
        'grateful': '🙏',
        'hopeful': '🌈',
        'relieved': '😌',
        'satisfied': '👍',
        'balanced': '⚖️',
        'patient': '⏳',
        'present': '🧠',
        'grounded': '🌍',

        # Positive / Social
        'loved': '🥰',
        'supported': '🤝',
        'connected': '🔗',
        'appreciated': '💛',
        'valued': '🌟',

        # Neutral
        'okay': '😐',
        'meh': '😑',
        'numb': '😶',
        'indifferent': '🤷',
        'neutral': '➖',
        'distracted': '📱',
        'restless': '🔄',
        'bored': '🥱',
        'curious': '🤔',

        # Low Energy / Tired
        'tired': '😮‍💨',
        'exhausted': '😩',
        'drained': '🪫',
        'lazy': '🛋️',
        'unmotivated': '😒',
        'sluggish': '🐌',
        'burnt_out': '🔥',
        'sleepy': '🥱',
        'lethargic': '💤',

        # Negative / Mild
        'worried': '😟',
        'anxious': '😰',
        'nervous': '😬',
        'stressed': '😫',
        'overwhelmed': '🌊',
        'uncertain': '❓',
        'confused': '😕',
        'hesitant': '🤚',
        'doubtful': '🤨',

        # Negative / Moderate
        'frustrated': '😤',
        'irritated': '😠',
        'annoyed': '🙄',
        'angry': '😡',
        'resentful': '😾',
        'bitter': '🍋',
        'disappointed': '😔',
        'discouraged': '📉',
        'defeated': '🏳️',

        # Negative / Deep
        'sad': '😢',
        'lonely': '🧍',
        'isolated': '🏝️',
        'hopeless': '🕳️',
        'empty': '🫙',
        'ashamed': '😳',
        'guilty': '😞',
        'regretful': '💭',
        'worthless': '🗑️',
        'broken': '💔',
        'grieving': '🕊️',
        'depressed': '🌧️',

        # Reflective
        'reflective': '🪞',
        'introspective': '🔍',
        'thoughtful': '💡',
        'nostalgic': '📸',
        'humbled': '🙇',
        }
        return MOOD_EMOJI


import datetime
def custom_date_formatter(datetime_data: datetime.datetime, include_year_m_d = True, include_hour = True, include_min = True):
    """
RETURNS A CLEANED FORMAT OF THE DATETIME FOR DISPLAY

include_year_m_d : to use the Datetime. ... .date() -yyyy-mm-dd
include_hour : to include hour : datetime. ... .hour -hh
include min: to include min : datetime. ... minutes -mm
    """
    to_return = ""
    if include_year_m_d == True: to_return = datetime_data.date()
    if include_hour == True: to_return = f"{to_return} {datetime_data.hour}"
    if include_min == True: to_return = f"{to_return}:{datetime_data.minute}"
    
    return to_return


class SeoGeo:
    DEFAULT = {
        'title': 'STREAK & DISCIPLINE — Build unbreakable habits, one honest check-in at a time',
        'description': 'STREAK & DISCIPLINE is a daily accountability app for building and tracking personal commitments, streaks, and habits.',
        'geo_summary': 'STREAK & DISCIPLINE is a habit-tracking and accountability web application. Users create "commitments" (personal goals), check in daily, and the app tracks a consecutive-day streak per commitment, sends reminders, and shows analytics.',
        'robots': 'index, follow',
    }

    #keyed by the view's URL `name=` (see origin/urls.py) - only PUBLIC/marketing-relevant pages
    #need real SEO effort (search engines can't index anything behind login anyway); dashboard/auth
    #pages are left on DEFAULT with robots noindex below.
    PAGES = {
        'origin_home': {
            'title': 'STREAK & DISCIPLINE — Build unbreakable habits, one honest check-in at a time',
            'description': 'Track daily commitments, keep your streak alive, and stay accountable with reminders, analytics, and an optional accountability partner. Free to start.',
            'geo_summary': 'STREAK & DISCIPLINE is a habit-tracking and accountability web app. Core features: daily commitment check-ins, streak counting, email/push/WhatsApp reminders, an accountability-partner (social) mode, and weekly analytics reports. Pricing tiers: free, premium, gold.',
        },
        'origin_blog': {
            'title': 'Blog & Updates — STREAK & DISCIPLINE',
            'description': 'Product updates, discipline tips, and real stories from users building their streaks with STREAK & DISCIPLINE.',
            'geo_summary': 'The STREAK & DISCIPLINE blog publishes product updates, practical discipline/habit-building tips, and first-person accountability stories submitted by users of the app.',
        },
        'origin_leaderboard': {
            'title': 'Leaderboard — STREAK & DISCIPLINE',
            'description': 'See how top users are staying consistent this week on STREAK & DISCIPLINE\'s public leaderboard.',
            'geo_summary': 'The STREAK & DISCIPLINE leaderboard is an opt-in public ranking of users by weekly consistency/streak performance.',
        },
        'origin_signup': {
            'title': 'Sign Up — STREAK & DISCIPLINE',
            'description': 'Create your free STREAK & DISCIPLINE account and start your first streak today.',
        },
        'origin_login': {
            'title': 'Log In — STREAK & DISCIPLINE',
            'description': 'Log in to your STREAK & DISCIPLINE account to check in on today\'s commitments.',
            'robots': 'noindex, follow',
        },
        'origin_extra': {
            'title': 'Help, Terms & Privacy — STREAK & DISCIPLINE',
            'description': 'Terms of service, privacy policy, and help center for STREAK & DISCIPLINE.',
        },
        'origin_navigation': {
            'title': 'Site Navigation Guide — STREAK & DISCIPLINE',
            'description': 'A living map of every page and feature on STREAK & DISCIPLINE.',
        },
    }

    #url names that should never be indexed by search engines (private/dashboard/account pages) -
    #anything not explicitly listed in PAGES above with its own 'robots' key falls back to this
    #check, so newly added private pages are safe by default instead of accidentally indexable.
    NOINDEX_PREFIXES = ('origin_dashboard', 'origin_profile', 'origin_settings', 'origin_relationship',
                         'origin_reports', 'origin_commitments', 'origin_each_commitment', 'origin_onboarding',
                         'origin_staff', 'origin_password_reset', 'origin_deactivated', 'origin_leaderboard',
                         'origin_weekly_analysis')

    @classmethod
    def for_page(cls, url_name):
        """Resolve the SEO/GEO dict for a given URL name, merged over DEFAULT so a page
        only has to override the fields it actually wants to change."""
        page = dict(cls.DEFAULT)
        page.update(cls.PAGES.get(url_name, {}))
        if 'robots' not in cls.PAGES.get(url_name, {}) and url_name and url_name.startswith(cls.NOINDEX_PREFIXES):
            page['robots'] = 'noindex, nofollow'
        return page
