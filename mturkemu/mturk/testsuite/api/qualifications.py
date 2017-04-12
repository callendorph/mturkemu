# File: mturk/testsuite/qualifications.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the definition of some unit tests for
# evaluating the mturk JSON API interface that is hosted by this
# app.

from django.conf import settings

from mturk.models import *
from mturk.testsuite.utils import RequesterLiveTestCase

import os.path

class QualificationTests(RequesterLiveTestCase):

    def load_test_question(self, index):
        fpath = os.path.join(
            settings.BASE_DIR,
            "mturk/testsuite/data/quesform_%02d.xml" % index
        )
        with open(fpath, "r") as f:
            test = f.read()
        return(test)

    def load_answerkey(self, index):
        fpath = os.path.join(
            settings.BASE_DIR,
            "mturk/testsuite/data/answerkey_%02d.xml" % index
        )
        with open(fpath, "r") as f:
            answerKey = f.read()
        return(answerKey)

    def test_duplicate_qual_error(self):
        name = "qwer"
        desc = "This is another qual"

        resp = self.client.create_qualification_type(
            Name=name,
            Description=desc,
            QualificationTypeStatus = "Active",
            )

        self.is_ok(resp)

        obj = resp["QualificationType"]
        self.assertEqual(obj["Name"], name)
        self.assertEqual(obj["Description"], desc)
        self.assertEqual(obj["QualificationTypeStatus"], "Active")
        self.assertEqual(obj["IsRequestable"], True)
        self.assertEqual(obj["AutoGranted"], False)

        # Confirm that a qualification with same name and make sure
        # it throws
        RequestError = self.client._load_exceptions().RequestError

        with self.assertRaises(RequestError):
            resp = self.client.create_qualification_type(
                Name=name,
                Description="This is a qual 2",
                QualificationTypeStatus = "Active"
            )

    def test_invalid_create_args(self):
        # Attempt to create an invalid request with a test and
        # an autogrant flag
        test = self.load_test_question(1)
        dur = 10
        name = "fdsa"
        desc = "garbage garbage garbage"

        RequestError = self.client._load_exceptions().RequestError

        with self.assertRaises(RequestError):
            resp = self.client.create_qualification_type(
                Name=name,
                Description=desc,
                QualificationTypeStatus = "Active",
                Test = test,
                TestDurationInSeconds = dur,
                AutoGranted=True,
                AutoGrantedValue = 10
            )

    def test_get_invalid_qualtype(self):

        RequestError = self.client._load_exceptions().RequestError

        with self.assertRaises(RequestError):
            resp = self.client.get_qualification_type(
                QualificationTypeId = "A1939"
                )

        with self.assertRaises(RequestError):
            resp = self.client.list_qualification_requests(
                QualificationTypeId = "ABDC",
                MaxResults = 10
            )


    def test_qual_creation(self):
        qualCount = 0

        name = "asdf"
        desc = "This is a qual"
        dur = 100
        test = self.load_test_question(1)

        resp = self.client.create_qualification_type(
            Name=name,
            Description=desc,
            QualificationTypeStatus = "Active",
            Test = test,
            TestDurationInSeconds = dur
            )

        self.is_ok(resp)

        obj = resp["QualificationType"]
        self.assertEqual(obj["Name"], name)
        self.assertEqual(obj["Description"], desc)
        self.assertEqual(obj["QualificationTypeStatus"], "Active")
        self.assertEqual(obj["TestDurationInSeconds"], dur)
        self.assertEqual(obj["Test"], test)
        self.assertEqual(obj["IsRequestable"], True)
        self.assertEqual(obj["AutoGranted"], False)

        qualCount += 1

        # Create a more limited qual with no test - manual
        #   approval only.

        name = "qwer"
        desc = "This is another qual"

        resp = self.client.create_qualification_type(
            Name=name,
            Description=desc,
            QualificationTypeStatus = "Active",
            )

        self.is_ok(resp)
        obj = resp["QualificationType"]
        self.assertEqual(obj["Name"], name)
        self.assertEqual(obj["Description"], desc)
        self.assertEqual(obj["QualificationTypeStatus"], "Active")
        self.assertEqual(obj["IsRequestable"], True)
        self.assertEqual(obj["AutoGranted"], False)

        qualCount += 1

        # Create a qual with auto grant
        name = "zxcv"
        desc = "This is the other qual"
        agval = 10
        resp = self.client.create_qualification_type(
            Name=name,
            Description=desc,
            QualificationTypeStatus = "Active",
            AutoGranted = True,
            AutoGrantedValue= agval
            )

        self.is_ok(resp)

        obj = resp["QualificationType"]
        self.assertEqual(obj["Name"], name)
        self.assertEqual(obj["Description"], desc)
        self.assertEqual(obj["QualificationTypeStatus"], "Active")
        self.assertEqual(obj["IsRequestable"], True)
        self.assertEqual(obj["AutoGranted"], True)
        self.assertEqual(obj["AutoGrantedValue"], agval)

        qualCount += 1

        # Create a qual with test and answerkey
        name = "jdjs"
        desc = "This is a qual with an answerkey"
        dur = 100
        test = self.load_test_question(2)
        answerKey = self.load_answerkey(1)
        retry = 1000

        resp = self.client.create_qualification_type(
            Name=name,
            Description=desc,
            QualificationTypeStatus = "Active",
            Test = test,
            AnswerKey = answerKey,
            TestDurationInSeconds = dur,
            RetryDelayInSeconds = retry
            )

        self.is_ok(resp)

        obj = resp["QualificationType"]
        self.assertEqual(obj["Name"], name)
        self.assertEqual(obj["Description"], desc)
        self.assertEqual(obj["QualificationTypeStatus"], "Active")
        self.assertEqual(obj["TestDurationInSeconds"], dur)
        self.assertEqual(obj["Test"], test)
        self.assertEqual(obj["AnswerKey"], answerKey)
        self.assertEqual(obj["IsRequestable"], True)
        self.assertEqual(obj["AutoGranted"], False)
        self.assertEqual(obj["RetryDelayInSeconds"], retry)
        qualCount += 1

        qualId = obj["QualificationTypeId"]

        # Check for qualification requests - these should not be
        #   any present right now

        resp = self.client.list_qualification_requests(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)
        numResults = resp["NumResults"]
        self.assertEqual(numResults, 0)
        qualReqs = resp["QualificationRequests"]
        self.assertEqual(len(qualReqs), 0 )

        # Check Qualification Type Accessor

        resp = self.client.get_qualification_type(
            QualificationTypeId = qualId
            )
        self.is_ok(resp)

        obj = resp["QualificationType"]
        self.assertEqual(obj["QualificationTypeId"], qualId)
        self.assertEqual(obj["Name"], name)
        self.assertEqual(obj["Description"], desc)
        self.assertEqual(obj["QualificationTypeStatus"], "Active")

        # Attempt to list the qualifications for our
        # requester.
        resp = self.client.list_qualification_types(
            MustBeRequestable=True, MustBeOwnedByCaller = True,
            MaxResults=10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, qualCount)
        quals = resp["QualificationTypes"]
        self.assertEqual( len(quals), qualCount )

        # Create a new account so that we can attempt to list quals
        # with other parameters

        client2 = self.create_new_client("test2")

        resp = client2.list_qualification_types(
            MustBeRequestable=True, MustBeOwnedByCaller = False,
            MaxResults=10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, qualCount)
        quals = resp["QualificationTypes"]
        self.assertEqual( len(quals), qualCount )

        # Query for quals created by this new client - which
        # shoudl be zero
        resp = client2.list_qualification_types(
            MustBeRequestable=True, MustBeOwnedByCaller = True,
            MaxResults=10
            )
        self.is_ok(resp)
        numResults = resp["NumResults"]
        self.assertEqual(numResults, 0)
        quals = resp["QualificationTypes"]
        self.assertEqual( len(quals), 0 )
