# File: mturk/tests/api.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the definition of some unit tests for
# evaluating the mturk JSON API interface that is hosted by this
# app.

from django.test import TestCase, LiveServerTestCase
from django.contrib.auth.models import User

from mturk.models import *

import boto3

class RequesterBasics(LiveServerTestCase):

    def setUp(self):

        # Setup a requester account and create an
        # access ID / key for the account

        userCreate = {
            "username" : "test1",
            "password" : "test1",
        }
        reqUser = User.objects.create_user(**userCreate)

        requester = Requester.objects.get(user=reqUser)

        # Generate a credential for the requester to use.
        aLen = 20
        self.accessKey = Credential.create_random_key(aLen)
        self.secretKey = Credential.create_random_key(aLen)

        cred = Credential.objects.create(
            requester = requester,
            access_key = self.accessKey,
            secret_key = self.secretKey
        )

    def is_ok(self, resp):
        code = resp["ResponseMetadata"]["HTTPStatusCode"]
        if ( code != 200 ):
            raise Exception("Failed Request: %s" % pformat(resp))

    def test_basic_access(self):

        url = self.live_server_url
        client = boto3.client(
            "mturk",
            aws_access_key_id = self.accessKey,
            aws_secret_access_key = self.secretKey,
            verify=False,
            region_name="us-east-1",
            endpoint_url=url
            )


        resp = client.get_account_balance()
        self.is_ok(resp)

        balance = resp["AvailableBalance"]
        self.assertEqual(balance, "10000.00")
