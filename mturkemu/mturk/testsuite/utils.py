# File: mturk/testsuite/utils.py
# Author: Carl Allendorph
#
# Description:
#    This file contains some utilities for the testsuite unit tests.
#

from mturk.models import *
from django.test import LiveServerTestCase
from django.contrib.auth.models import User

import boto3

class RequesterLiveTestCase(LiveServerTestCase):
    """
    Live server test case with a requester user
    configured with credentials and a boto3 client
    object created and ready.
    """
    def setUp(self):
        super().setUp()

        # Setup a requester account and create an
        # access ID / key for the account
        self.client = self.create_new_client("test1")

    def create_new_client(self, username):
        """
        Create a new client for a user with the passed
        username. If that user does not exist, then a user
        will be created before creating the client.
        """
        # Setup a requester account and create an
        # access ID / key for the account
        try:
            reqUser = User.objects.get(username=username)
        except User.DoesNotExist:
            userCreate = {
                "username" : username,
                "password" : username+"0",
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

        url = self.live_server_url
        client = boto3.client(
            "mturk",
            aws_access_key_id = self.accessKey,
            aws_secret_access_key = self.secretKey,
            verify=False,
            region_name="us-east-1",
            endpoint_url=url
            )
        return(client)

    def is_ok(self, resp):
        """
        Check if the response from the service is a valid
        HTTP OK response.
        """
        code = resp["ResponseMetadata"]["HTTPStatusCode"]
        self.assertEqual(code, 200)
