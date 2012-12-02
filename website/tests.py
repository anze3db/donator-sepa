"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from website.models import get_payments_list

class DBtest(TestCase):
    def test_get_all_db(self):
        print get_payments_list("2012-12-8", 1)
        self.failUnlessEqual(1 + 1, 3)

