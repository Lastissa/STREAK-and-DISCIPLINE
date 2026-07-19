from django.test import TestCase
from django.contrib.auth import get_user_model


real = get_user_model().objects.count() #so the test temp table is not used
#test to view all key in the custom user is accurate
class InitialTest(TestCase):
    
    def test_check_keys(self):
        ideal = ['email', 'username']
        count = get_user_model().objects.count()
        print(f"total users real table : {real} & total user testmode table: {count} ")
