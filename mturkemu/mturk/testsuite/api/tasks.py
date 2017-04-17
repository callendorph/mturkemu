# File: mturk/testsuite/api/tasks.py
# Author: Carl Allendorph
#
# Description:
#   This file contains unit tests associated with the
# task creation and management API for the requester.
#

from mturk.models import *
from mturk.testsuite.utils import RequesterLiveTestCase
from mturk.worker.actor import WorkerActor

from datetime import timedelta
from decimal import Decimal

class TaskTests(RequesterLiveTestCase):

    def test_create_hit_type(self):
        """
        """
        appSecs = 10000
        assignSecs = 100
        reward = "0.05"
        title = "Some Task"
        desc = "Some long rambling description"
        kwds = ["asdf", "qwer", "hgfd"]
        kwdStr = ",".join(kwds)
        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = []
            )

        self.is_ok(resp)

        taskTypeId = resp["HITTypeId"]
        self.assertTrue( len(taskTypeId) > 0 )

        tt = TaskType.objects.get(aws_id = taskTypeId)
        self.assertEqual( tt.auto_approve, timedelta(seconds=appSecs))
        self.assertEqual( tt.assignment_duration, timedelta(seconds=assignSecs))
        self.assertEqual( tt.title, title )
        self.assertEqual( tt.description, desc )
        self.assertEqual( tt.reward, Decimal(reward))
        self.assertEqual( tt.qualifications.count(), 0 )

        # Attempt to create the same task type again - it should
        # return the exact same object

        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = []
            )

        self.is_ok(resp)

        taskTypeId2 = resp["HITTypeId"]

        self.assertEqual( taskTypeId, taskTypeId2 )

        # Attempt to create a new task that is just slightly
        # different and confirm that it created a new object.
        title2 = "Gargoyle"
        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title2,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = []
            )

        self.is_ok(resp)

        taskTypeId2 = resp["HITTypeId"]

        self.assertNotEqual( taskTypeId, taskTypeId2 )


        # Now try a slightly more different task type
        # by changing the keywords
        kwdStr2 = "asdf,qwer"
        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title2,
            Keywords = kwdStr2,
            Description = desc,
            QualificationRequirements = []
            )

        self.is_ok(resp)

        taskTypeId3 = resp["HITTypeId"]

        self.assertNotEqual( taskTypeId3, taskTypeId )
        self.assertNotEqual( taskTypeId3, taskTypeId2 )

        # Again - slight keyword set variation
        kwdStr3 = "asdf,qwer,uyuy"
        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title2,
            Keywords = kwdStr3,
            Description = desc,
            QualificationRequirements = []
            )

        self.is_ok(resp)

        taskTypeId4 = resp["HITTypeId"]

        self.assertNotEqual( taskTypeId4, taskTypeId )
        self.assertNotEqual( taskTypeId4, taskTypeId2 )
        self.assertNotEqual( taskTypeId4, taskTypeId3 )

        # Again - with no keyword set
        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title2,
            Description = desc,
            QualificationRequirements = []
            )

        self.is_ok(resp)

        taskTypeId5 = resp["HITTypeId"]

        self.assertNotEqual( taskTypeId5, taskTypeId )
        self.assertNotEqual( taskTypeId5, taskTypeId2 )
        self.assertNotEqual( taskTypeId5, taskTypeId3 )
        self.assertNotEqual( taskTypeId5, taskTypeId4 )

        # Create a new requester and attempt to get the task
        # type with the same arguments - these should be
        # different task type objects.
        requester = self.create_new_client("test2")

        resp = requester.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = []
            )

        self.is_ok(resp)

        reqTaskTypeId = resp["HITTypeId"]
        self.assertNotEqual( reqTaskTypeId, taskTypeId )

    def create_quals(self):
        """
        Create some qualification objects for the default
        requester so that we have something to work with in our
        tests.
        """
        self.quals = []

        resp = self.client.create_qualification_type(
            Name="Test Qual 1",
            Description="Some Stuff",
            QualificationTypeStatus = "Active",
            )

        self.is_ok(resp)

        self.quals.append( resp["QualificationType"]["QualificationTypeId"])

        resp = self.client.create_qualification_type(
            Name="Test Qual 2",
            Description="Some Other Stuff",
            QualificationTypeStatus = "Active",
            )

        self.is_ok(resp)

        self.quals.append( resp["QualificationType"]["QualificationTypeId"])


    def create_workers(self):
        self.actors = []
        usernames = ["test2", "test3", "test4"]
        vals = [ 10, 20, 30 ]
        for i,username in enumerate(usernames):
            worker_client = self.create_new_client(username)
            worker = Worker.objects.get(user__username = username)
            self.actors.append( WorkerActor(worker) )
            resp = self.client.associate_qualification_with_worker(
                QualificationTypeId = self.quals[0],
                WorkerId = worker.aws_id,
                IntegerValue = vals[i]
            )
            self.is_ok(resp)


    def test_create_hit_type_with_quals(self):
        """
        """

        # Create some qualifications to reference in the
        self.create_quals()

        appSecs = 10000
        assignSecs = 100
        reward = "0.05"
        title = "Some Task"
        desc = "Some long rambling description"
        kwds = ["asdf", "qwer", "hgfd"]
        kwdStr = ",".join(kwds)
        qualReqs = [
            {
                "QualificationTypeId" : self.quals[0],
                "Comparator" : "GreaterThan",
                "IntegerValues" : [ 10 ],
                "RequiredToPreview" : False
            },
        ]
        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = qualReqs
            )

        self.is_ok(resp)

        taskTypeId = resp["HITTypeId"]
        self.assertTrue( len(taskTypeId) > 0 )

        tt = TaskType.objects.get(aws_id = taskTypeId)
        self.assertEqual( tt.auto_approve, timedelta(seconds=appSecs))
        self.assertEqual( tt.assignment_duration, timedelta(seconds=assignSecs))
        self.assertEqual( tt.title, title )
        self.assertEqual( tt.description, desc )
        self.assertEqual( tt.reward, Decimal(reward))
        self.assertEqual( tt.qualifications.count(), 1 )

        qualReq = tt.qualifications.all()[0]
        self.assertEqual(qualReq.qualification.aws_id, self.quals[0])
        self.assertEqual(qualReq.comparator, QualComparatorField.GREATER_THAN)
        self.assertEqual(qualReq.required_to_preview, False)

        vals = qualReq.get_int_values()
        self.assertEqual(len(vals), 1 )
        self.assertEqual(vals[0], 10 )

        # Check if the create method gives the same type back
        # with the same args.
        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = qualReqs
            )

        self.is_ok(resp)

        taskTypeId2 = resp["HITTypeId"]
        self.assertEqual( taskTypeId, taskTypeId2 )

        # Check a subtle difference in the qual req - should
        # create a new task type

        qualReqs2 = [
            {
                "QualificationTypeId" : self.quals[0],
                "Comparator" : "GreaterThan",
                "IntegerValues" : [ 11 ],
                "RequiredToPreview" : False
            },
        ]
        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = qualReqs2
            )

        self.is_ok(resp)

        taskTypeId3 = resp["HITTypeId"]
        self.assertNotEqual( taskTypeId3, taskTypeId )

        # Check a subtle difference in the qual req - should
        # create a new task type

        qualReqs3 = [
            {
                "QualificationTypeId" : self.quals[0],
                "Comparator" : "LessThan",
                "IntegerValues" : [ 10 ],
                "RequiredToPreview" : False
            },
        ]
        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = qualReqs3
            )

        self.is_ok(resp)

        taskTypeId4 = resp["HITTypeId"]
        self.assertNotEqual( taskTypeId4, taskTypeId )
        self.assertNotEqual( taskTypeId4, taskTypeId3 )

        # Check a subtle difference in the qual req - should
        # create a new task type

        qualReqs4 = [
            {
                "QualificationTypeId" : self.quals[0],
                "Comparator" : "GreaterThan",
                "IntegerValues" : [ 10 ],
                "RequiredToPreview" : True
            },
        ]
        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = qualReqs4
            )

        self.is_ok(resp)

        taskTypeId5 = resp["HITTypeId"]
        self.assertNotEqual( taskTypeId5, taskTypeId )
        self.assertNotEqual( taskTypeId5, taskTypeId3 )
        self.assertNotEqual( taskTypeId5, taskTypeId4 )

    def test_qualreq_comparators_int(self):
        """
        """
        # Create some qualifications to reference in the
        self.create_quals()
        self.create_workers()

        inputVecs = [
            "GreaterThan",
            "GreaterThanOrEqualTo",
            "LessThan",
            "LessThanOrEqualTo",
            "EqualTo",
            "NotEqualTo",
            # These are the trivial examples of In/NotIn
            # which are equivalent to the EqualTo/NotEqualTo
            "In",
            "NotIn",
        ]

        outputVecs = [
            [False, False, True],
            [False, True, True],
            [True, False, False],
            [True, True, False],
            [False, True, False],
            [True, False, True],
            [False, True, False],
            [True, False, True],
        ]

        appSecs = 10000
        assignSecs = 100
        reward = "0.05"
        title = "Some Task"
        desc = "Some long rambling description"
        kwds = ["asdf", "qwer", "hgfd"]
        kwdStr = ",".join(kwds)


        for i,inputVec in enumerate(inputVecs):
            outputVec = outputVecs[i]

            qualReqs = [
                {
                    "QualificationTypeId" : self.quals[0],
                    "Comparator" : inputVec,
                    "IntegerValues" : [ 20 ],
                    "RequiredToPreview" : False
                },
            ]

            resp = self.client.create_hit_type(
                AutoApprovalDelayInSeconds = appSecs,
                AssignmentDurationInSeconds = assignSecs,
                Reward = reward,
                Title = title,
                Keywords = kwdStr,
                Description = desc,
                QualificationRequirements = qualReqs
            )

            self.is_ok(resp)

            taskTypeId = resp["HITTypeId"]
            self.assertTrue( len(taskTypeId) > 0 )

            tt = TaskType.objects.get(aws_id = taskTypeId)
            self.assertTrue( tt.qualifications.count() > 0 )

            for i,expResult in enumerate(outputVec):
                self.assertTrue(
                    self.actors[i].check_prerequisite_quals( tt ) == expResult
                )

        # Do some more complicated checks on the In/NotIn operations

        # In Comparator
        qualReqs = [
            {
                "QualificationTypeId" : self.quals[0],
                "Comparator" : "In",
                "IntegerValues" : [ 20, 10 ],
                "RequiredToPreview" : False
            },
        ]

        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = qualReqs
        )

        self.is_ok(resp)

        taskTypeId = resp["HITTypeId"]
        self.assertTrue( len(taskTypeId) > 0 )

        tt = TaskType.objects.get(aws_id = taskTypeId)
        self.assertTrue( tt.qualifications.count() > 0 )

        expResults = [True, True, False]
        for i,expResult in enumerate(expResults):
            self.assertTrue(
                self.actors[i].check_prerequisite_quals( tt ) == expResult
            )
        # Not In Comparator
        qualReqs = [
            {
                "QualificationTypeId" : self.quals[0],
                "Comparator" : "NotIn",
                "IntegerValues" : [ 20, 10 ],
                "RequiredToPreview" : False
            },
        ]

        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = qualReqs
        )

        self.is_ok(resp)

        taskTypeId = resp["HITTypeId"]
        self.assertTrue( len(taskTypeId) > 0 )

        tt = TaskType.objects.get(aws_id = taskTypeId)
        self.assertTrue( tt.qualifications.count() > 0 )

        expResults = [False, False, True]
        for i,expResult in enumerate(expResults):
            self.assertTrue(
                self.actors[i].check_prerequisite_quals( tt ) == expResult
            )

        # Check The "Exists" and "DoesNotExist" comparators
        qualReqs = [
            {
                "QualificationTypeId" : self.quals[1],
                "Comparator" : "Exists",
                "IntegerValues" : [ 10 ],
                "RequiredToPreview" : False
            },
        ]

        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = qualReqs
        )

        self.is_ok(resp)

        taskTypeId = resp["HITTypeId"]
        self.assertTrue( len(taskTypeId) > 0 )

        tt = TaskType.objects.get(aws_id = taskTypeId)
        self.assertTrue( tt.qualifications.count() > 0 )

        expResults = [False, False, False]
        for i,expResult in enumerate(expResults):
            self.assertTrue(
                self.actors[i].check_prerequisite_quals( tt ) == expResult
            )

        # Not exists
        qualReqs = [
            {
                "QualificationTypeId" : self.quals[1],
                "Comparator" : "DoesNotExist",
                "IntegerValues" : [ 10 ],
                "RequiredToPreview" : False
            },
        ]

        resp = self.client.create_hit_type(
            AutoApprovalDelayInSeconds = appSecs,
            AssignmentDurationInSeconds = assignSecs,
            Reward = reward,
            Title = title,
            Keywords = kwdStr,
            Description = desc,
            QualificationRequirements = qualReqs
        )

        self.is_ok(resp)

        taskTypeId = resp["HITTypeId"]
        self.assertTrue( len(taskTypeId) > 0 )

        tt = TaskType.objects.get(aws_id = taskTypeId)
        self.assertTrue( tt.qualifications.count() > 0 )

        expResults = [True, True, True]
        for i,expResult in enumerate(expResults):
            self.assertTrue(
                self.actors[i].check_prerequisite_quals( tt ) == expResult
            )
