from django.core.cache import cache
import random
from django.utils import timezone

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
    return (timezone.datetime.now().year)

def intro_word(list_lenght = 2) -> list:
    """for intro word i will use to show message to user using the message.info()"""
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
    return random.sample(words, 2)
    
def template_based_reusables(request):
    """To save data that will be reused i template and i dont have to import them as they will be import automatically like i was in a render function"""
    
    customer_care_phone_number = '+2347013687825' 
    customer_care_whatsapp_number = '+2347013687825'
    footer_copyright_note = f"{timezone.now().year} STREAK & DISCIPLINE. All rights reserved."
    custom_base_url = '' # incase i need to access base url in templates in situations where i cannot use {% url ''%}
    
    return {
        'customer_care_phone_number' : customer_care_phone_number,
        'customer_care_whatsapp_number': customer_care_whatsapp_number,
        'footer_copyright_note': footer_copyright_note,
        'logo_url' : 'https://res.cloudinary.com/brop3jeq/image/upload/v1784524604/logo_jvljxp.png',
        'mobile_dark_url': 'https://res.cloudinary.com/brop3jeq/image/upload/v1784524602/mobile_dark_iuvjyq.png',
        'mobile_light_url':'https://res.cloudinary.com/brop3jeq/image/upload/v1784524602/mobile_light_xvuaxj.png',
        'desktop_dark_url' : 'https://res.cloudinary.com/brop3jeq/image/upload/v1784524602/desktop_dark_nvt6lr.png',
        'desktop_light_url' : 'https://res.cloudinary.com/brop3jeq/image/upload/v1784524602/desktop_light_rrgglg.png',
        'custom_base_url' : custom_base_url       
    }