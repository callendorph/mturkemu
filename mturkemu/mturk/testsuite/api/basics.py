# File: mturk/testsuite/api/basics.py
# Author: Carl Allendorph
#
# Description:
#    This file contains some basic unit tests for the
# requester API interface.
#

from mturk.testsuite.utils import RequesterLiveTestCase

class RequesterBasics(RequesterLiveTestCase):

    def test_basic_access(self):
        """
        Get the default account balance as a simple sanity check
        """

        resp = self.client.get_account_balance()
        self.is_ok(resp)

        balance = resp["AvailableBalance"]
        self.assertEqual(balance, "10000.00")
