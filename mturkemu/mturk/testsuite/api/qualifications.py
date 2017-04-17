# File: mturk/testsuite/qualifications.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the definition of some unit tests for
# evaluating the mturk JSON API interface that is hosted by this
# app.

from django.conf import settings
from django.utils import timezone

from mturk.models import *
from mturk.testsuite.utils import RequesterLiveTestCase
from mturk.worker.actor import WorkerActor
from mturk.worker.QualsActor import *
from mturk.xml.quesformanswer import QFormAnswer

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


    def test_qual_auto_grant(self):
        """
        This test is intended to check the qualification auto grant
        process for a worker's request.
        """

        worker1_client = self.create_new_client("test2")
        worker1 = Worker.objects.get(user__username = "test2")

        actor = WorkerActor(worker1)

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

        qualId = obj["QualificationTypeId"]

        # Use the worker to request the qualification
        qual = Qualification.objects.get( aws_id = qualId )
        req = actor.create_qual_request(qual)
        self.assertTrue( req.is_idle() )
        self.assertEqual( req.worker, worker1 )
        self.assertEqual( req.qualification, qual )

        grant = actor.process_qual_request(qual, req)
        self.assertTrue( grant is not None )
        self.assertEqual( grant.value, agval )
        self.assertTrue( req.is_approved() )

        # Attempt to request again - should throw
        with self.assertRaises(QualHasActiveGrant):
            req = actor.create_qual_request(qual)


        # Check that this grant shows up in the list
        # via the requester API

        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            Status="Granted",
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 1 )

        grant = grants[0]
        self.assertEqual( grant["WorkerId"], worker1.aws_id)
        self.assertEqual( grant["QualificationTypeId"], qualId)
        self.assertEqual( grant["Status"], "Granted" )

        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            Status="Revoked",
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 0 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 0 )

        # Revoke the grant of this qualification
        # via the requester API
        reason = "Bad Reason"
        resp = self.client.disassociate_qualification_from_worker(
            WorkerId = worker1.aws_id,
            QualificationTypeId = qualId,
            Reason= reason
            )

        self.is_ok(resp)

        # Check that this grant shows as revoked in the list
        # via the requester API

        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            Status="Granted",
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 0 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 0 )

        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            Status="Revoked",
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 1 )

        grant = grants[0]
        self.assertEqual( grant["WorkerId"], worker1.aws_id)
        self.assertEqual( grant["QualificationTypeId"], qualId)
        self.assertEqual( grant["Status"], "Revoked" )

        # Check that the worker can't request the grant
        # because it has been revoked.

        with self.assertRaises(QualPermamentGrantBlock):
            req = actor.create_qual_request(qual)


        # Create a new worker and auto grant so that we
        # have both a worker with a grant and a worker
        # with a revoke

        worker2_client = self.create_new_client("test3")
        worker2 = Worker.objects.get(user__username = "test3")

        actor2 = WorkerActor(worker2)

        req = actor2.create_qual_request(qual)
        self.assertTrue( req.is_idle() )
        self.assertEqual( req.worker, worker2 )
        self.assertEqual( req.qualification, qual )

        grant = actor2.process_qual_request(qual, req)
        self.assertTrue( grant is not None )
        self.assertEqual( grant.value, agval )
        self.assertTrue( req.is_approved() )

        # List out all grants
        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 2 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 2 )

        revoked = [x for x in grants if x["Status"] == "Revoked" ]
        granted = [x for x in grants if x["Status"] == "Granted" ]

        self.assertEqual( len(revoked), 1 )
        self.assertEqual( len(granted), 1 )

        grant = revoked[0]
        self.assertEqual( grant["WorkerId"], worker1.aws_id)
        self.assertEqual( grant["QualificationTypeId"], qualId)
        self.assertEqual( grant["Status"], "Revoked" )
        revTS = grant["GrantTime"]

        grant = granted[0]
        self.assertEqual( grant["WorkerId"], worker2.aws_id)
        self.assertEqual( grant["QualificationTypeId"], qualId)
        self.assertEqual( grant["Status"], "Granted" )
        grantTS = grant["GrantTime"]

        # I'm not controlling the system clock so
        # I'm doing a differential time comparison here.
        self.assertTrue( grantTS > revTS )


    def test_manual_grant_no_exam(self):
        worker1_client = self.create_new_client("test2")
        worker1 = Worker.objects.get(user__username = "test2")

        actor = WorkerActor(worker1)

        # Create a qual that must be manually associated
        name = "Bottomless"
        desc = "This is the manual qual"
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

        qualId = obj["QualificationTypeId"]

        # Use the worker to request the qualification
        qual = Qualification.objects.get( aws_id = qualId )
        req = actor.create_qual_request(qual)
        self.assertTrue( req.is_idle() )
        self.assertEqual( req.worker, worker1 )
        self.assertEqual( req.qualification, qual )

        grant = actor.process_qual_request(qual, req)
        self.assertTrue( grant is None )

        req.refresh_from_db()
        self.assertTrue(req.is_pending() )
        self.assertFalse( req.is_idle() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_approved() )

        # Attempt to request again - should throw
        with self.assertRaises(QualHasActiveRequest):
            req = actor.create_qual_request(qual)

        # Now there should be a qualification request available
        # for the requester to approve/reject

        resp = self.client.list_qualification_requests(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 1)
        reqs = resp["QualificationRequests"]
        self.assertEqual(len(reqs), 1)

        req = reqs[0]
        self.assertEqual(req["QualificationTypeId"], qualId)
        self.assertEqual(req["WorkerId"], worker1.aws_id)

        qualReqId = req["QualificationRequestId"]

        # Accept this qualification request

        resp = self.client.accept_qualification_request(
            QualificationRequestId = qualReqId,
            IntegerValue = 60
            )

        self.is_ok(resp)

        # Check that the grant exists

        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 1 )

        grant = grants[0]
        self.assertEqual( grant["WorkerId"], worker1.aws_id)
        self.assertEqual( grant["QualificationTypeId"], qualId)
        self.assertEqual( grant["Status"], "Granted" )

        # Create a new qual so that we can reject it

        name = "Topless"
        desc = "This is the other manual qual"
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

        qualId = obj["QualificationTypeId"]

        # Use the worker to request the qualification
        qual = Qualification.objects.get( aws_id = qualId )
        req = actor.create_qual_request(qual)
        self.assertTrue( req.is_idle() )
        self.assertEqual( req.worker, worker1 )
        self.assertEqual( req.qualification, qual )

        grant = actor.process_qual_request(qual, req)
        self.assertTrue( grant is None )

        req.refresh_from_db()
        self.assertTrue(req.is_pending() )
        self.assertFalse( req.is_idle() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_approved() )

        # Attempt to request again - should throw
        with self.assertRaises(QualHasActiveRequest):
            req = actor.create_qual_request(qual)

        # List available requests
        resp = self.client.list_qualification_requests(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 1)
        reqs = resp["QualificationRequests"]
        self.assertEqual(len(reqs), 1)

        req = reqs[0]
        self.assertEqual(req["QualificationTypeId"], qualId)
        self.assertEqual(req["WorkerId"], worker1.aws_id)

        qualReqId = req["QualificationRequestId"]


        # Reject this qualification request

        resp = self.client.reject_qualification_request(
            QualificationRequestId = qualReqId,
            Reason = "Because I can"
            )

        self.is_ok(resp)

        # No Grant will be created - confirm that there is no
        # grant.

        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 0 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 0 )

    def test_manual_grant_with_exam_and_key_01(self):
        """
        Test 01 - PercentageMapping
        """
        worker1_client = self.create_new_client("test2")
        worker1 = Worker.objects.get(user__username = "test2")

        actor = WorkerActor(worker1)

        test = self.load_test_question(2)
        answerKey = self.load_answerkey(1)

        # Create a qual that must be manually associated
        name = "This is the final countdown"
        desc = "This is the manual qual"
        resp = self.client.create_qualification_type(
            Name=name,
            Description=desc,
            QualificationTypeStatus = "Active",
            Test = test,
            AnswerKey = answerKey,
            TestDurationInSeconds = 100
            )

        self.is_ok(resp)

        obj = resp["QualificationType"]
        self.assertEqual(obj["Name"], name)
        self.assertEqual(obj["Description"], desc)
        self.assertEqual(obj["QualificationTypeStatus"], "Active")
        self.assertEqual(obj["IsRequestable"], True)
        self.assertEqual(obj["AutoGranted"], False)

        qualId = obj["QualificationTypeId"]

        # Use the worker to request the qualification
        qual = Qualification.objects.get( aws_id = qualId )
        req = actor.create_qual_request(qual)
        self.assertTrue( req.is_idle() )
        self.assertEqual( req.worker, worker1 )
        self.assertEqual( req.qualification, qual )

        grant = actor.process_qual_request(qual, req)
        self.assertTrue( grant is None )

        req.refresh_from_db()
        self.assertTrue(req.is_idle() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_approved() )

        # Attempt to request again - This won't throw because
        # we want to transition the worker to looking at the
        # test.
        req2 = actor.create_qual_request(qual)
        self.assertTrue(req2.is_idle() )
        self.assertFalse( req2.is_pending() )
        self.assertFalse( req2.is_rejected() )
        self.assertFalse( req2.is_approved() )
        self.assertEqual( req.aws_id, req2.aws_id)

        # I don't believe this qual request should show up
        # here.
        resp = self.client.list_qualification_requests(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 0)
        reqs = resp["QualificationRequests"]
        self.assertEqual(len(reqs), 0)

        # Now as worker actor - submit a test exam answer that
        # can be graded
        answer = {
            "favorite" : ["green"],
            "acceptible" : ["red", "blue"],
        }
        expScore = 66

        actor.submit_test_answer(req, answer)

        self.assertTrue( req.is_approved() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_idle() )

        grant = QualificationGrant.objects.get(
            worker=worker1,
            qualification = req.qualification
        )

        self.assertEqual( grant.value, expScore )
        self.assertEqual( grant.active, True )


        # Check for requests
        resp = self.client.list_qualification_requests(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 0)
        reqs = resp["QualificationRequests"]
        self.assertEqual(len(reqs), 0)

        #  Check for grants
        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 1 )

        grant = grants[0]
        self.assertEqual( grant["WorkerId"], worker1.aws_id)
        self.assertEqual( grant["QualificationTypeId"], qualId)
        self.assertEqual( grant["Status"], "Granted" )

    def test_manual_grant_with_exam_and_key_02(self):
        """
        Test 02 - ScaleMapping
        """
        worker1_client = self.create_new_client("test2")
        worker1 = Worker.objects.get(user__username = "test2")

        actor = WorkerActor(worker1)

        test = self.load_test_question(2)
        answerKey = self.load_answerkey(2)

        # Create a qual that must be manually associated
        name = "This is the final countdown"
        desc = "This is the manual qual"
        resp = self.client.create_qualification_type(
            Name=name,
            Description=desc,
            QualificationTypeStatus = "Active",
            Test = test,
            AnswerKey = answerKey,
            TestDurationInSeconds = 100
            )

        self.is_ok(resp)

        obj = resp["QualificationType"]
        self.assertEqual(obj["Name"], name)
        self.assertEqual(obj["Description"], desc)
        self.assertEqual(obj["QualificationTypeStatus"], "Active")
        self.assertEqual(obj["IsRequestable"], True)
        self.assertEqual(obj["AutoGranted"], False)

        qualId = obj["QualificationTypeId"]

        # Use the worker to request the qualification
        qual = Qualification.objects.get( aws_id = qualId )
        req = actor.create_qual_request(qual)
        self.assertTrue( req.is_idle() )
        self.assertEqual( req.worker, worker1 )
        self.assertEqual( req.qualification, qual )

        grant = actor.process_qual_request(qual, req)
        self.assertTrue( grant is None )

        req.refresh_from_db()
        self.assertTrue(req.is_idle() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_approved() )

        # Attempt to request again - This won't throw because
        # we want to transition the worker to looking at the
        # test.
        req2 = actor.create_qual_request(qual)
        self.assertTrue(req2.is_idle() )
        self.assertFalse( req2.is_pending() )
        self.assertFalse( req2.is_rejected() )
        self.assertFalse( req2.is_approved() )
        self.assertEqual( req.aws_id, req2.aws_id)

        # I don't believe this qual request should show up
        # here.
        resp = self.client.list_qualification_requests(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 0)
        reqs = resp["QualificationRequests"]
        self.assertEqual(len(reqs), 0)

        # Now as worker actor - submit a test exam answer that
        # can be graded
        answer = {
            "favorite" : ["green"],
            "acceptible" : ["red", "blue"],
        }
        expScore = 10

        actor.submit_test_answer(req, answer)

        self.assertTrue( req.is_approved() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_idle() )

        grant = QualificationGrant.objects.get(
            worker=worker1,
            qualification = req.qualification
        )

        self.assertEqual( grant.value, expScore )
        self.assertEqual( grant.active, True )


        # Check for requests
        resp = self.client.list_qualification_requests(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 0)
        reqs = resp["QualificationRequests"]
        self.assertEqual(len(reqs), 0)

        #  Check for grants
        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 1 )

        grant = grants[0]
        self.assertEqual( grant["WorkerId"], worker1.aws_id)
        self.assertEqual( grant["QualificationTypeId"], qualId)
        self.assertEqual( grant["Status"], "Granted" )

    def test_manual_grant_with_exam_and_key_03(self):
        """
        Test 03 - RangeMapping
        """
        worker1_client = self.create_new_client("test2")
        worker1 = Worker.objects.get(user__username = "test2")

        actor = WorkerActor(worker1)

        test = self.load_test_question(2)
        answerKey = self.load_answerkey(3)

        # Create a qual that must be manually associated
        name = "This is the final countdown"
        desc = "This is the manual qual"
        resp = self.client.create_qualification_type(
            Name=name,
            Description=desc,
            QualificationTypeStatus = "Active",
            Test = test,
            AnswerKey = answerKey,
            TestDurationInSeconds = 100
            )

        self.is_ok(resp)

        obj = resp["QualificationType"]
        self.assertEqual(obj["Name"], name)
        self.assertEqual(obj["Description"], desc)
        self.assertEqual(obj["QualificationTypeStatus"], "Active")
        self.assertEqual(obj["IsRequestable"], True)
        self.assertEqual(obj["AutoGranted"], False)

        qualId = obj["QualificationTypeId"]

        # Use the worker to request the qualification
        qual = Qualification.objects.get( aws_id = qualId )
        req = actor.create_qual_request(qual)
        self.assertTrue( req.is_idle() )
        self.assertEqual( req.worker, worker1 )
        self.assertEqual( req.qualification, qual )

        grant = actor.process_qual_request(qual, req)
        self.assertTrue( grant is None )

        req.refresh_from_db()
        self.assertTrue(req.is_idle() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_approved() )

        # Attempt to request again - This won't throw because
        # we want to transition the worker to looking at the
        # test.
        req2 = actor.create_qual_request(qual)
        self.assertTrue(req2.is_idle() )
        self.assertFalse( req2.is_pending() )
        self.assertFalse( req2.is_rejected() )
        self.assertFalse( req2.is_approved() )
        self.assertEqual( req.aws_id, req2.aws_id)

        # I don't believe this qual request should show up
        # here.
        resp = self.client.list_qualification_requests(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 0)
        reqs = resp["QualificationRequests"]
        self.assertEqual(len(reqs), 0)

        # Now as worker actor - submit a test exam answer that
        # can be graded
        answer = {
            "favorite" : ["green"],
            "acceptible" : ["red", "blue"],
        }
        expScore = 20

        actor.submit_test_answer(req, answer)

        self.assertTrue( req.is_approved() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_idle() )

        grant = QualificationGrant.objects.get(
            worker=worker1,
            qualification = req.qualification
        )

        self.assertEqual( grant.value, expScore )
        self.assertEqual( grant.active, True )

        # Create another worker to request the qualification
        # and attempt to get the out of range value

        worker2_client = self.create_new_client("test3")
        worker2 = Worker.objects.get(user__username = "test3")
        actor2 = WorkerActor(worker2)

        req = actor2.create_qual_request(qual)
        self.assertTrue( req.is_idle() )
        self.assertEqual( req.worker, worker2 )
        self.assertEqual( req.qualification, qual )

        grant = actor2.process_qual_request(qual, req)
        self.assertTrue( grant is None )

        req.refresh_from_db()
        self.assertTrue(req.is_idle() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_approved() )

        # Submit a bad answer
        answer = {
            "favorite" : ["blue"],
            "acceptible" : ["red"],
        }
        expScore = 1

        actor2.submit_test_answer(req, answer)

        self.assertTrue( req.is_approved() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_idle() )

        grant = QualificationGrant.objects.get(
            worker=worker2,
            qualification = req.qualification
        )

        self.assertEqual( grant.value, expScore )
        self.assertEqual( grant.active, True )

        # Create another worker to request the qualification
        # and attempt to get the out of range value

        worker3_client = self.create_new_client("test4")
        worker3 = Worker.objects.get(user__username = "test4")
        actor3 = WorkerActor(worker3)

        req = actor3.create_qual_request(qual)
        self.assertTrue( req.is_idle() )
        self.assertEqual( req.worker, worker3 )
        self.assertEqual( req.qualification, qual )

        grant = actor3.process_qual_request(qual, req)
        self.assertTrue( grant is None )

        req.refresh_from_db()
        self.assertTrue(req.is_idle() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_approved() )

        # Submit a bad answer
        answer = {
            "favorite" : ["green"],
            "acceptible" : ["red"],
        }
        expScore = 10

        actor3.submit_test_answer(req, answer)

        self.assertTrue( req.is_approved() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_idle() )

        grant = QualificationGrant.objects.get(
            worker=worker3,
            qualification = req.qualification
        )

        self.assertEqual( grant.value, expScore )
        self.assertEqual( grant.active, True )




    def test_manual_grant_with_exam_and_nokey(self):
        startTime = timezone.now()
        worker1_client = self.create_new_client("test2")
        worker1 = Worker.objects.get(user__username = "test2")

        actor = WorkerActor(worker1)

        test = self.load_test_question(2)

        # Create a qual that must be manually associated
        name = "This is the final countdown"
        desc = "This is the manual qual"
        resp = self.client.create_qualification_type(
            Name=name,
            Description=desc,
            QualificationTypeStatus = "Active",
            Test = test,
            TestDurationInSeconds = 100
            )

        self.is_ok(resp)

        obj = resp["QualificationType"]
        self.assertEqual(obj["Name"], name)
        self.assertEqual(obj["Description"], desc)
        self.assertEqual(obj["QualificationTypeStatus"], "Active")
        self.assertEqual(obj["IsRequestable"], True)
        self.assertEqual(obj["AutoGranted"], False)

        qualId = obj["QualificationTypeId"]

        # Use the worker to request the qualification
        qual = Qualification.objects.get( aws_id = qualId )
        req = actor.create_qual_request(qual)
        self.assertTrue( req.is_idle() )
        self.assertEqual( req.worker, worker1 )
        self.assertEqual( req.qualification, qual )

        grant = actor.process_qual_request(qual, req)
        self.assertTrue( grant is None )

        req.refresh_from_db()
        self.assertTrue(req.is_idle() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_approved() )

        # Attempt to request again - This won't throw because
        # we want to transition the worker to looking at the
        # test.
        req2 = actor.create_qual_request(qual)
        self.assertTrue(req2.is_idle() )
        self.assertFalse( req2.is_pending() )
        self.assertFalse( req2.is_rejected() )
        self.assertFalse( req2.is_approved() )
        self.assertEqual( req.aws_id, req2.aws_id)

        # I don't believe this qual request should show up
        # here yet because the worker has not taken the exam yet.
        resp = self.client.list_qualification_requests(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 0)
        reqs = resp["QualificationRequests"]
        self.assertEqual(len(reqs), 0)

        # Now as worker actor - submit a test exam answer that
        # can be graded
        answer = {
            "favorite" : ["green"],
            "acceptible" : ["red", "blue"],
        }

        actor.submit_test_answer(req, answer)

        self.assertTrue( req.is_pending() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_approved() )
        self.assertFalse( req.is_idle() )

        with self.assertRaises(QualificationGrant.DoesNotExist):
            grant = QualificationGrant.objects.get(
                worker=worker1,
                qualification = req.qualification
            )

        # Now as the requester we will poll for outstanding requests.
        resp = self.client.list_qualification_requests(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 1)
        reqs = resp["QualificationRequests"]
        self.assertEqual(len(reqs), 1)

        obj = reqs[0]

        self.assertEqual( obj["QualificationRequestId"], req.aws_id )
        self.assertEqual( obj["QualificationTypeId"], qual.aws_id )
        self.assertEqual( obj["WorkerId"], worker1.aws_id )
        self.assertEqual( obj["Test"], test )
        self.assertTrue( obj["SubmitTime"] > startTime )
        self.assertTrue( len(obj["Answer"]) > 0 )

        wrkAnsXML = QFormAnswer()
        wrkAnswerSet = wrkAnsXML.parse( obj["Answer"] )
        self.assertEqual( len(wrkAnswerSet), 2 )

        checkedAns = set()
        for name, val in answer.items():
            for wrkAns in wrkAnswerSet:
                if ( wrkAns["QuestionIdentifier"] == name ):
                    wrkValStr = wrkAns["SelectionIdentifier"]
                    wrkVal = wrkValStr.split(" ")
                    wkrVal = [x for x in wrkVal if len(x) > 0]
                    self.assertEqual( len(wkrVal), len(val) )
                    wrkValSet = set(wrkVal)
                    valSet = set(val)
                    self.assertEqual( wrkValSet, valSet )
                    checkedAns.add(name)

        expectedAns = set( answer.keys() )
        self.assertEqual( checkedAns, expectedAns )


        # Accept the grant

        resp = self.client.accept_qualification_request(
            QualificationRequestId=req.aws_id,
            IntegerValue=56
            )

        self.is_ok(resp)

        req.refresh_from_db()
        self.assertTrue(req.is_approved() )
        self.assertFalse( req.is_pending() )
        self.assertFalse( req.is_rejected() )
        self.assertFalse( req.is_idle() )


        #  Check for grants
        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 1 )

        grant = grants[0]
        self.assertEqual( grant["WorkerId"], worker1.aws_id)
        self.assertEqual( grant["QualificationTypeId"], qualId)
        self.assertEqual( grant["Status"], "Granted" )
        self.assertTrue( grant["GrantTime"] > startTime )
        self.assertEqual( grant["IntegerValue"], 56 )

        with self.assertRaises(KeyError):
            grant["LocaleValue"]


    def test_associate_qual_without_request(self):
        """
        """
        startTime = timezone.now()
        worker1_client = self.create_new_client("test2")
        worker1 = Worker.objects.get(user__username = "test2")

        actor = WorkerActor(worker1)

        # Create a qual that must be manually associated
        name = "This is the final countdown"
        desc = "This is the manual qual"
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

        qualId = obj["QualificationTypeId"]

        grantVal = 78

        resp = self.client.associate_qualification_with_worker(
            QualificationTypeId = qualId,
            WorkerId = worker1.aws_id,
            IntegerValue = grantVal
            )

        self.is_ok(resp)

        # List Grants for Workers.
        resp = self.client.list_workers_with_qualification_type(
            QualificationTypeId = qualId,
            MaxResults = 10
            )

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        grants = resp["Qualifications"]
        self.assertEqual( len(grants), 1 )

        grant = grants[0]
        self.assertEqual( grant["WorkerId"], worker1.aws_id)
        self.assertEqual( grant["QualificationTypeId"], qualId)
        self.assertEqual( grant["Status"], "Granted" )
        self.assertTrue( grant["GrantTime"] > startTime )
        self.assertEqual( grant["IntegerValue"], grantVal )

        with self.assertRaises(KeyError):
            grant["LocaleValue"]


        # Get the qualification score directly
        resp = self.client.get_qualification_score(
            QualificationTypeId = qualId,
            WorkerId = worker1.aws_id
        )

        self.is_ok(resp)

        obj = resp["Qualification"]
        self.assertEqual( obj["QualificationTypeId"], qualId )
        self.assertEqual( obj["WorkerId"], worker1.aws_id )
        self.assertTrue( obj["GrantTime"] > startTime )
        self.assertEqual( obj["IntegerValue"], grantVal )
        self.assertEqual( obj["Status"], "Granted" )
        with self.assertRaises( KeyError ):
            grant["LocaleValue"]

        # Generate a different requester user and attempt to
        # Associate the request - this is an illegal operation.
        requester = self.create_new_client("test3")

        worker2_client = self.create_new_client("test4")
        worker2 = Worker.objects.get(user__username = "test4")

        actor2 = WorkerActor(worker2)

        RequestError = self.client._load_exceptions().RequestError
        with self.assertRaises(RequestError):
            resp = requester.associate_qualification_with_worker(
                QualificationTypeId = qualId,
                WorkerId = worker2.aws_id,
                IntegerValue = grantVal
            )

        # Attempt dissociate by different requester -
        # this is an illegal operation.

        with self.assertRaises(RequestError):
            resp = requester.disassociate_qualification_from_worker(
                QualificationTypeId = qualId,
                WorkerId = worker1.aws_id,
                Reason = "some stupid reason"
            )
