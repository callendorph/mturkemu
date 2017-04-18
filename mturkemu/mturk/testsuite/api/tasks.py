# File: mturk/testsuite/api/tasks.py
# Author: Carl Allendorph
#
# Description:
#   This file contains unit tests associated with the
# task creation and management API for the requester.
#

from django.utils import timezone

from mturk.models import *
from mturk.testsuite.utils import RequesterLiveTestCase, load_quesform
from mturk.worker.actor import WorkerActor
from mturk.worker.TasksActor import *

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


    def test_create_task_with_tasktype(self):
        """
        Create Task with a tasktype Object. This test generally does
        a run through the entire process of creating a task, reviewing
        its submitted assignments, and completing the task.
        @note - This test is VERY long. I've decided that it is not worth
           my time right now to break this up in to lots of smaller
           tests.
        """
        startTime = timezone.now()
        self.create_quals()
        self.create_workers()

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

        numAssigns = 2
        maxLife = 10000

        question = load_quesform(1)

        annot = "Pigs fly at Midnight"
        resp = self.client.create_hit_with_hit_type(
            HITTypeId = taskTypeId,
            MaxAssignments = 2,
            LifetimeInSeconds = maxLife,
            Question = question,
            RequesterAnnotation = annot,
            UniqueRequestToken = "blarg"
        )

        self.is_ok(resp)

        obj = resp["HIT"]

        self.assertEqual( obj["HITTypeId"], taskTypeId )
        self.assertTrue( obj["CreationTime"] > startTime )
        self.assertEqual( obj["Title"], title )
        self.assertEqual( obj["Description"], desc )
        self.assertEqual( obj["Question"], question )
        self.assertEqual( obj["Keywords"], kwdStr )
        self.assertEqual( obj["HITStatus"], "Assignable")
        self.assertEqual( obj["MaxAssignments"], numAssigns)
        self.assertEqual( obj["Reward"], reward )
        self.assertEqual( obj["AutoApprovalDelayInSeconds"], appSecs)
        self.assertTrue(
            obj["Expiration"] > (startTime + timedelta(seconds=maxLife))
        )
        self.assertEqual( obj["AssignmentDurationInSeconds"], assignSecs)
        self.assertEqual( obj["RequesterAnnotation"], annot)
        self.assertEqual( obj["HITReviewStatus"], "NotReviewed")
        # Stats
        self.assertEqual( obj["NumberOfAssignmentsPending"], 0)
        self.assertEqual( obj["NumberOfAssignmentsAvailable"], 2)
        self.assertEqual( obj["NumberOfAssignmentsCompleted"], 0)

        taskId = obj["HITId"]

        # Use workers to accept and complete the task.
        task = Task.objects.get( aws_id = taskId )
        assignment = self.actors[0].accept_task(task)

        # Check that an assertion is raised when the
        # worker tries to accept a task they have already accepted.
        with self.assertRaises(AssignmentAlreadyAccepted):
            self.actors[0].accept_task(task)

        # Get the HIT state so that we can see the stats change.
        resp = self.client.get_hit(
            HITId = taskId
            )
        self.is_ok(resp)

        obj = resp["HIT"]
        self.assertEqual( obj["NumberOfAssignmentsPending"], 1)
        self.assertEqual( obj["NumberOfAssignmentsAvailable"], 1 )
        self.assertEqual( obj["NumberOfAssignmentsCompleted"], 0)
        self.assertEqual( obj["HITStatus"], "Assignable" )

        # Submit data for the assignment to put assignment into
        # pending state.
        data = {
            "my_question_id": "Jimmy"
        }

        self.actors[0].complete_assignment(assignment, data)

        # Get the HIT state so that we can see the stats change.
        resp = self.client.get_hit(
            HITId = taskId
            )
        self.is_ok(resp)

        obj = resp["HIT"]
        self.assertEqual( obj["NumberOfAssignmentsPending"], 0)
        self.assertEqual( obj["NumberOfAssignmentsAvailable"], 1 )
        self.assertEqual( obj["NumberOfAssignmentsCompleted"], 0)
        self.assertEqual( obj["HITStatus"], "Assignable" )

        with self.assertRaises( TaskAlreadyHasAssignment ):
            self.actors[0].accept_task(task)

        assignment = self.actors[1].accept_task(task)

        # Get the HIT state so that we can see the stats change.
        resp = self.client.get_hit(
            HITId = taskId
            )
        self.is_ok(resp)

        obj = resp["HIT"]
        self.assertEqual( obj["NumberOfAssignmentsPending"], 1)
        self.assertEqual( obj["NumberOfAssignmentsAvailable"], 0 )
        self.assertEqual( obj["NumberOfAssignmentsCompleted"], 0)
        self.assertEqual( obj["HITStatus"], "Unassignable" )

        # Submit data for the assignment to put assignment into
        # pending state.
        data = {
            "my_question_id": "Johns"
        }
        self.actors[1].complete_assignment(assignment, data)

        # Get the HIT state so that we can see the stats change.
        resp = self.client.get_hit(
            HITId = taskId
            )
        self.is_ok(resp)

        obj = resp["HIT"]
        self.assertEqual( obj["NumberOfAssignmentsPending"], 0)
        self.assertEqual( obj["NumberOfAssignmentsAvailable"], 0 )
        self.assertEqual( obj["NumberOfAssignmentsCompleted"], 0)
        self.assertEqual( obj["HITStatus"], "Reviewable" )

        # Look for Reviewing Tasks - this should be a null list
        resp = self.client.list_reviewable_hits(
            HITTypeId = taskTypeId,
            Status="Reviewing",
            MaxResults= 10
        )
        self.is_ok(resp)
        numResults = resp["NumResults"]
        self.assertEqual( numResults, 0 )
        tasks = resp["HITs"]
        self.assertEqual( len(tasks), 0 )

        # Look for reviewable HITs
        resp = self.client.list_reviewable_hits(
            HITTypeId = taskTypeId,
            MaxResults= 10
        )
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        tasks = resp["HITs"]
        self.assertEqual( len(tasks), 1 )

        obj = tasks[0]

        self.assertEqual(obj["HITId"], taskId )
        self.assertEqual( obj["HITTypeId"], taskTypeId)
        self.assertEqual( obj["Title"], title )
        self.assertEqual( obj["Description"], desc )

        # Transition this task from Reviewable to Reviewing.

        resp = self.client.update_hit_review_status(HITId = taskId)
        self.is_ok(resp)

        # Look for Reviewable Tasks - this should be a null list
        # now that we have transitioned the task
        resp = self.client.list_reviewable_hits(
            HITTypeId = taskTypeId,
            Status="Reviewable",
            MaxResults= 10
        )
        self.is_ok(resp)
        numResults = resp["NumResults"]
        self.assertEqual( numResults, 0 )
        tasks = resp["HITs"]
        self.assertEqual( len(tasks), 0 )

        # Find Tasks in the Reviewing State - this should
        # be where we find our task
        resp = self.client.list_reviewable_hits(
            HITTypeId = taskTypeId,
            Status="Reviewing",
            MaxResults= 10
        )
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        tasks = resp["HITs"]
        self.assertEqual( len(tasks), 1 )

        obj = tasks[0]

        self.assertEqual(obj["HITId"], taskId )
        self.assertEqual( obj["HITTypeId"], taskTypeId)
        self.assertEqual( obj["Title"], title )
        self.assertEqual( obj["Description"], desc )

        # Now let's review the assignments associated
        # with this task.

        # Check that the approved and rejected starts out empty
        resp = self.client.list_assignments_for_hit(
            HITId = taskId,
            AssignmentStatuses=["Approved", "Rejected"],
        )
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 0 )
        assignments = resp["Assignments"]
        self.assertEqual( len(assignments), 0 )

        # Check for submitted assigns - there should be 2
        resp = self.client.list_assignments_for_hit(
            HITId = taskId,
            AssignmentStatuses=["Submitted"],
        )
        self.is_ok(resp)
        numResults = resp["NumResults"]
        self.assertEqual( numResults, 2 )
        assignments = resp["Assignments"]
        self.assertEqual( len(assignments), 2 )

        workerSet = set([])
        for assignment in assignments:
            # Test out the "get_assignment" method
            assignId = assignment["AssignmentId"]
            resp = self.client.get_assignment( AssignmentId = assignId )
            self.is_ok(resp)

            obj = resp["Assignment"]
            self.assertEqual( obj["AssignmentId"], assignId )
            compKeys = [
                "WorkerId", "AssignmentStatus", "Answer",
                "AutoApprovalTime", "SubmitTime", "Deadline",
                "AcceptTime",
                ]
            for compKey in compKeys:
                self.assertEqual( obj[compKey], assignment[compKey] )

            invalidKeys = [
                "ApprovalTime", "RejectionTime"
            ]
            for invalidKey in invalidKeys:
                with self.assertRaises(KeyError):
                    obj[invalidKey]
                with self.assertRaises(KeyError):
                    assignment[invalidKey]

            acceptTime = obj["AcceptTime"]
            subTime = obj["SubmitTime"]
            autoTime = obj["AutoApprovalTime"]
            deadline = obj["Deadline"]
            self.assertTrue( acceptTime > startTime )
            self.assertTrue( subTime > acceptTime )
            self.assertTrue( autoTime > subTime )
            self.assertTrue( deadline > subTime )

            self.assertEqual( obj["AssignmentStatus"], "Submitted" )

            self.assertTrue( len(obj["Answer"]) > 0 )
            # @todo - check the worker answer here
            workerSet.add( obj["WorkerId"])

        # Excpected Worker Set:
        expWorkers = set([
            self.actors[0].worker.aws_id,
            self.actors[1].worker.aws_id
        ])
        self.assertEqual( expWorkers, workerSet)

        # Approve first assignment
        assignId = assignments[0]["AssignmentId"]
        resp = self.client.approve_assignment(
            AssignmentId = assignId
            )
        self.is_ok(resp)

        resp = self.client.get_assignment( AssignmentId = assignId )
        self.is_ok(resp)

        obj = resp["Assignment"]
        self.assertEqual( obj["AssignmentId"], assignId )
        self.assertEqual( obj["AssignmentStatus"], "Approved")

        approveTime = obj["ApprovalTime"]
        subTime = obj["SubmitTime"]
        self.assertTrue( approveTime > subTime )

        with self.assertRaises(KeyError):
            rejTime = obj["RejectionTime"]

        # Attempt as the requester to reject this assignment even
        # though we have already approved it - this should generate
        # an error.
        RequestError = self.client._load_exceptions().RequestError
        with self.assertRaises(RequestError):
            resp = self.client.reject_assignment(
                AssignmentId = assignId,
                RequesterFeedback = "bs"
                )

        # Check Task Stats
        resp = self.client.get_hit(
            HITId = taskId
            )
        self.is_ok(resp)

        obj = resp["HIT"]
        self.assertEqual( obj["NumberOfAssignmentsPending"], 0)
        self.assertEqual( obj["NumberOfAssignmentsAvailable"], 0 )
        self.assertEqual( obj["NumberOfAssignmentsCompleted"], 1)
        self.assertEqual( obj["HITStatus"], "Reviewing" )

        # Now let's test the rejection of the second assignment.
        assignId = assignments[1]["AssignmentId"]
        reason = "Arbitrary Reason"
        resp = self.client.reject_assignment(
            AssignmentId = assignId,
            RequesterFeedback = "Arbitrary Reason"
            )
        self.is_ok(resp)

        resp = self.client.get_assignment( AssignmentId = assignId )
        self.is_ok(resp)

        obj = resp["Assignment"]
        self.assertEqual( obj["AssignmentId"], assignId )
        self.assertEqual( obj["AssignmentStatus"], "Rejected")

        rejTime = obj["RejectionTime"]
        subTime = obj["SubmitTime"]
        self.assertTrue( rejTime > subTime )

        with self.assertRaises(KeyError):
            rejTime = obj["ApprovalTime"]

        # Check Task Stats
        resp = self.client.get_hit(
            HITId = taskId
            )
        self.is_ok(resp)

        obj = resp["HIT"]
        self.assertEqual( obj["NumberOfAssignmentsPending"], 0)
        self.assertEqual( obj["NumberOfAssignmentsAvailable"], 0 )
        self.assertEqual( obj["NumberOfAssignmentsCompleted"], 2)
        self.assertEqual( obj["HITStatus"], "Reviewing" )


        # Test the list assignments method for this hit
        # so that we can very they are doing what is expected.
        resp = self.client.list_assignments_for_hit(
            HITId = taskId,
            AssignmentStatuses=["Submitted"],
        )
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 0 )
        assignments = resp["Assignments"]
        self.assertEqual( len(assignments), 0 )

        # Test only approved list
        resp = self.client.list_assignments_for_hit(
            HITId = taskId,
            AssignmentStatuses=["Approved"],
        )
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        assignments = resp["Assignments"]
        self.assertEqual( len(assignments), 1 )

        # Test approved and rejected list
        resp = self.client.list_assignments_for_hit(
            HITId = taskId,
            AssignmentStatuses=["Approved", "Rejected"],
        )
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 2 )
        assignments = resp["Assignments"]
        self.assertEqual( len(assignments), 2 )

        # Test Rejected Only List
        resp = self.client.list_assignments_for_hit(
            HITId = taskId,
            AssignmentStatuses=["Rejected"],
        )
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 1 )
        assignments = resp["Assignments"]
        self.assertEqual( len(assignments), 1 )

        assignment = assignments[0]

        # Override the rejection and approve this second assignment
        assignId = assignment["AssignmentId"]
        with self.assertRaises(RequestError):
            resp = self.client.approve_assignment(
                AssignmentId = assignId,
                OverrideRejection =  False
                )

        resp = self.client.approve_assignment(
            AssignmentId = assignId,
            OverrideRejection = True
            )
        self.is_ok(resp)

        resp = self.client.get_assignment( AssignmentId = assignId )
        self.is_ok(resp)

        obj = resp["Assignment"]
        self.assertEqual( obj["AssignmentId"], assignId )
        self.assertEqual( obj["AssignmentStatus"], "Approved")

        approveTime = obj["ApprovalTime"]
        rejTime = obj["RejectionTime"]
        subTime = obj["SubmitTime"]
        self.assertTrue( rejTime > subTime )
        self.assertTrue( approveTime > rejTime )

        # Check stats again
        resp = self.client.get_hit(
            HITId = taskId
            )
        self.is_ok(resp)

        obj = resp["HIT"]
        self.assertEqual( obj["NumberOfAssignmentsPending"], 0)
        self.assertEqual( obj["NumberOfAssignmentsAvailable"], 0 )
        self.assertEqual( obj["NumberOfAssignmentsCompleted"], 2)
        self.assertEqual( obj["HITStatus"], "Reviewing" )
