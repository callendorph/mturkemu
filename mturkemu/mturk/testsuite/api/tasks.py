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
        """
        Utility method for creating users with some prepared qualifications
        associated with those workers.
        Use the 'self.actors' object to access the workers created.
        """
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
        # Create a separate requester to test access constraints
        requester = self.create_new_client("req1")

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

        # Get the Task state so that we can see the stats change.
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

        # Get the Task state so that we can see the stats change.
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

        # Now we will have worker 2 take a look at the assignment
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



    def test_create_task(self):
        """
        In this test we will create a task without a task type. We will
        also test task creation with qualification requirements
        """
        startTime = timezone.now()
        self.create_quals()
        self.create_workers()

        maxAssigns = 3
        lifetime = 10000
        assignDur = 1000
        reward = "0.13"
        title = "Create Task with Quals"
        desc = "Little bit of sugar"
        annot = "asdf"
        question = load_quesform(2)

        resp = self.client.create_hit(
            MaxAssignments = maxAssigns,
            LifetimeInSeconds = lifetime,
            AssignmentDurationInSeconds = assignDur,
            Reward = reward,
            Title = title,
            Description = desc,
            Question = question,
            RequesterAnnotation = annot,
            QualificationRequirements=[
                {
                    "QualificationTypeId" : self.quals[0],
                    "Comparator" : "GreaterThan",
                    "IntegerValues" : [ 20 ],
                    "RequiredToPreview" : False
                }
            ],
            UniqueRequestToken="ureuw"
        )
        self.is_ok(resp)

        obj = resp["HIT"]

        self.assertTrue( len(obj["HITTypeId"]) > 0 )

        self.assertTrue( obj["CreationTime"] > startTime )
        self.assertEqual( obj["Title"], title )
        self.assertEqual( obj["Description"], desc )
        self.assertEqual( obj["Question"], question )
        self.assertEqual( obj["HITStatus"], "Assignable" )
        self.assertEqual( obj["MaxAssignments"], maxAssigns )
        self.assertEqual( obj["Reward"], reward )
        self.assertTrue( obj["AutoApprovalDelayInSeconds"] > 0 )
        self.assertTrue( obj["Expiration"] > startTime )
        self.assertTrue( obj["Expiration"] > obj["CreationTime"] )
        self.assertEqual( obj["AssignmentDurationInSeconds"], assignDur)
        self.assertEqual( obj["RequesterAnnotation"], annot )

        qualreqs = obj["QualificationRequirements"]
        self.assertEqual( len(qualreqs), 1 )

        qualreq = qualreqs[0]
        self.assertEqual( qualreq["QualificationTypeId"], self.quals[0] )
        self.assertEqual( qualreq["Comparator"], "GreaterThan" )
        self.assertEqual( qualreq["IntegerValues"], [ 20 ] )
        self.assertEqual( qualreq["RequiredToPreview"], False )

        with self.assertRaises(KeyError):
            qualreq["LocaleValues"]

        taskId = obj["HITId"]

        task = Task.objects.get( aws_id = taskId )

        avail, pend, complete, submitted = task.compute_assignment_stats()
        self.assertEqual( avail, maxAssigns )
        self.assertEqual( pend, 0 )
        self.assertEqual( complete, 0 )
        self.assertEqual( submitted, 0 )

        # Now we will try to access the task with a worker who
        # does not have the necessary qualifications.
        with self.assertRaises(TaskPrereqError):
            assignment = self.actors[0].accept_task( task )
        with self.assertRaises(TaskPrereqError):
            assignment = self.actors[1].accept_task( task )

        # Confirm the HIT's stats haven't change
        task.refresh_from_db()
        avail, pend, complete, submitted = task.compute_assignment_stats()
        self.assertEqual( avail, maxAssigns )
        self.assertEqual( pend, 0 )
        self.assertEqual( complete, 0 )
        self.assertEqual( submitted, 0 )

        # Try with actor that meets the qualification
        assignment = self.actors[2].accept_task( task )

        task.refresh_from_db()
        avail, pend, complete, submitted = task.compute_assignment_stats()
        self.assertEqual( avail, maxAssigns - 1 )
        self.assertEqual( pend, 1 )
        self.assertEqual( complete, 0 )
        self.assertEqual( submitted, 0 )

        self.assertEqual( assignment.task, task )
        self.assertEqual( assignment.worker.aws_id, self.actors[2].worker.aws_id )


    def test_delete_task(self):
        """
        Test the creation and deletion of a task
        """

        startTime = timezone.now()
        self.create_quals()
        self.create_workers()

        maxAssigns = 1
        lifetime = 10000
        assignDur = 1000
        reward = "0.13"
        title = "Create Task with Quals"
        desc = "Little bit of sugar"
        annot = "asdf"
        question = load_quesform(2)

        resp = self.client.create_hit(
            MaxAssignments = maxAssigns,
            LifetimeInSeconds = lifetime,
            AssignmentDurationInSeconds = assignDur,
            Reward = reward,
            Title = title,
            Description = desc,
            Question = question,
            RequesterAnnotation = annot,
            UniqueRequestToken="ureuw"
        )
        self.is_ok(resp)

        taskId = resp["HIT"]["HITId"]

        # We should not be able to delete a task until it
        # has transitioned to the reviewable state (or later) and
        # all assignments are approved/rejected.
        RequestError = self.client._load_exceptions().RequestError
        with self.assertRaises(RequestError):
            resp = self.client.delete_hit(HITId = taskId)


        resp = self.client.get_hit(HITId = taskId)
        self.is_ok(resp)

        taskObj = resp["HIT"]
        self.assertEqual( taskObj["HITStatus"], "Assignable" )

        # Accept and complete an assignment and then retest the
        # delete method
        task = Task.objects.get( aws_id = taskId )
        assignment = self.actors[0].accept_task(task)

        resp = self.client.get_hit(HITId = taskId)
        self.is_ok(resp)

        taskObj = resp["HIT"]
        self.assertEqual( taskObj["HITStatus"], "Unassignable" )

        with self.assertRaises(RequestError):
            resp = self.client.delete_hit(HITId = taskId)

        data = {
            "favorite" : ["blue"],
            "acceptible" : ["red", "blue"]
        }
        self.actors[0].complete_assignment( assignment, data )

        resp = self.client.get_hit(HITId = taskId)
        self.is_ok(resp)

        taskObj = resp["HIT"]
        self.assertEqual( taskObj["HITStatus"], "Reviewable" )

        # State is now reviewable but we haven't approved/rejected
        #   the assignment so we should still not be able to
        #   delete the task
        with self.assertRaises(RequestError):
            resp = self.client.delete_hit(HITId = taskId)

        resp = self.client.approve_assignment(
            AssignmentId = assignment.aws_id,
            RequesterFeedback = "Good Job"
        )
        self.is_ok(resp)

        # Check status
        resp = self.client.get_hit(HITId = taskId)
        self.is_ok(resp)

        taskObj = resp["HIT"]
        self.assertEqual( taskObj["HITStatus"], "Reviewable" )
        self.assertEqual( taskObj["NumberOfAssignmentsCompleted"], 1 )

        # Now finally we should be able to delete the Task

        # Test that another requester can't delete our Task
        requester = self.create_new_client("req1")
        with self.assertRaises(RequestError):
            resp = requester.delete_hit(HITId = taskId)

        resp = self.client.delete_hit(HITId = taskId)
        self.is_ok(resp)

        with self.assertRaises(RequestError):
            self.client.get_hit(HITId = taskId)


    def test_list_hits(self):
        """
        Test the "ListHITs" method
        """

        # First let's create a bunch of a tasks that we
        # can look through
        numTasksToCreate = 10

        maxAssigns = 1
        lifetime = 10000
        assignDur = 1000
        reward = "0.13"
        title = "Create Task with Quals"
        desc = "Little bit of sugar"
        annot = "asdf"
        question = load_quesform(2)

        taskIds = []

        for i in range(0, numTasksToCreate):
            resp = self.client.create_hit(
                MaxAssignments = maxAssigns,
                LifetimeInSeconds = lifetime,
                AssignmentDurationInSeconds = assignDur,
                Reward = reward,
                Title = title,
                Description = desc,
                Question = question,
                RequesterAnnotation = annot,
                UniqueRequestToken="ureuw" + str(i)
            )
            self.is_ok(resp)

            taskObj = resp["HIT"]
            taskIds.append( taskObj["HITId"] )


        # List out the tasks
        obsTaskIds = []

        # Get a chunk of HITs
        resp = self.client.list_hits( MaxResults = 5 )
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 5 )
        tasks = resp["HITs"]
        self.assertEqual( len(tasks), 5 )

        for task in tasks:
            obsTaskIds.append( task["HITId"] )

        nextToken = resp["NextToken"]
        self.assertTrue( len(nextToken) > 0 )

        # Get the next chunk
        resp = self.client.list_hits(MaxResults = 5, NextToken = nextToken )
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 5 )
        tasks = resp["HITs"]
        self.assertEqual( len(tasks), 5 )

        for task in tasks:
            obsTaskIds.append( task["HITId"] )

        nextToken = resp["NextToken"]
        self.assertTrue( len(nextToken) > 0 )

        # Get final chunk - should be zero len
        resp = self.client.list_hits(MaxResults = 5, NextToken = nextToken )
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 0 )
        tasks = resp["HITs"]
        self.assertEqual( len(tasks), 0 )


        # Compare the known task ids with the observed task ids
        self.assertEqual( set(obsTaskIds), set(taskIds) )

        # Create another requester and attempt to look
        # for tasks - we should not be able to see main user's
        # tasks.

        requester = self.create_new_client("req1")

        resp = requester.list_hits(MaxResults = 5)
        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual( numResults, 0 )


    def test_return_assignment(self):
        """
        This test will check the "return" assignment behavior for
        a worker.
        """
        startTime = timezone.now()
        self.create_quals()
        self.create_workers()

        maxAssigns = 2
        lifetime = 10000
        assignDur = 1000
        reward = "0.13"
        title = "Create Task with Quals"
        desc = "Little bit of sugar"
        annot = "asdf"
        question = load_quesform(2)

        resp = self.client.create_hit(
            MaxAssignments = maxAssigns,
            LifetimeInSeconds = lifetime,
            AssignmentDurationInSeconds = assignDur,
            Reward = reward,
            Title = title,
            Description = desc,
            Question = question,
            RequesterAnnotation = annot,
            UniqueRequestToken="ureuw"
        )
        self.is_ok(resp)

        taskId = resp["HIT"]["HITId"]
        task = Task.objects.get(aws_id = taskId)

        self.actors[0].worker.refresh_from_db()
        self.assertEqual( self.actors[0].worker.returned_hits, 0 )

        avail, pend, complete, submitted = task.compute_assignment_stats()
        self.assertEqual( avail, maxAssigns )
        self.assertEqual( pend, 0 )
        self.assertEqual( complete, 0 )
        self.assertEqual( submitted, 0 )

        assignment = self.actors[0].accept_task(task)

        task.refresh_from_db()
        avail, pend, complete, submitted = task.compute_assignment_stats()
        self.assertEqual( avail, maxAssigns - 1 )
        self.assertEqual( pend, 1 )
        self.assertEqual( complete, 0 )
        self.assertEqual( submitted, 0 )

        # Check if another worker can return the assignment
        # accepted by the first user
        with self.assertRaises(Assignment.DoesNotExist):
            self.actors[1].return_task(task)

        # return the task by the actual worker
        self.actors[0].return_task(task)

        task.refresh_from_db()
        avail, pend, complete, submitted = task.compute_assignment_stats()
        self.assertEqual( avail, maxAssigns )
        self.assertEqual( pend, 0 )
        self.assertEqual( complete, 0 )
        self.assertEqual( submitted, 0 )

        # Check that the worker's stats have updated.
        self.actors[0].worker.refresh_from_db()
        self.assertEqual( self.actors[0].worker.returned_hits, 1 )

    def test_award_bonus(self):
        """
        This test will check the functioning of the bonus award to a
        worker for an assignment
        """
        startTime = timezone.now()
        self.create_quals()
        self.create_workers()
        requester = self.create_new_client("req1")

        maxAssigns = 1
        lifetime = 10000
        assignDur = 1000
        reward = "0.13"
        title = "Create Task with Quals"
        desc = "Little bit of sugar"
        annot = "asdf"
        question = load_quesform(2)

        resp = self.client.create_hit(
            MaxAssignments = maxAssigns,
            LifetimeInSeconds = lifetime,
            AssignmentDurationInSeconds = assignDur,
            Reward = reward,
            Title = title,
            Description = desc,
            Question = question,
            RequesterAnnotation = annot,
            UniqueRequestToken="ureuw"
        )
        self.is_ok(resp)

        taskId = resp["HIT"]["HITId"]
        task = Task.objects.get(aws_id = taskId)

        assignment = self.actors[0].accept_task(task)

        # Check that the bonus function can't be used here
        RequestError = self.client._load_exceptions().RequestError
        with self.assertRaises(RequestError):
            resp = self.client.send_bonus(
                WorkerId = self.actors[0].worker.aws_id,
                BonusAmount = "1.00",
                AssignmentId = assignment.aws_id,
                Reason = "What a good job",
            )

        with self.assertRaises(RequestError):
            resp = requester.send_bonus(
                WorkerId = self.actors[0].worker.aws_id,
                BonusAmount = "1.00",
                AssignmentId = assignment.aws_id,
                Reason = "What a good job",
            )

        numBonuses = self.actors[0].worker.bonuspayment_set.count()
        self.assertEqual( numBonuses, 0 )


        data = {
            "favorite" : ["blue"],
            "acceptible" : ["red", "blue"]
        }
        self.actors[0].complete_assignment( assignment, data )

        # Assignment has been submitted and ready for review

        # Bonus can be awarded at this stage - so cool=
        resp = self.client.send_bonus(
            WorkerId = self.actors[0].worker.aws_id,
            BonusAmount = "1.00",
            AssignmentId = assignment.aws_id,
            Reason = "What a good job",
        )
        self.is_ok(resp)

        numBonuses = self.actors[0].worker.bonuspayment_set.count()
        self.assertEqual( numBonuses, 1 )

        # Check that the bonus function can't be used by other
        # Requester
        with self.assertRaises(RequestError):
            resp = requester.send_bonus(
                WorkerId = self.actors[0].worker.aws_id,
                BonusAmount = "1.00",
                AssignmentId = assignment.aws_id,
                Reason = "What a good job",
            )

        # Requester Approves the assignment
        resp = self.client.approve_assignment(
            AssignmentId = assignment.aws_id
        )
        self.is_ok(resp)

        # We should now be able to send a bonus to the worker
        resp = self.client.send_bonus(
            WorkerId = self.actors[0].worker.aws_id,
            BonusAmount = "1.00",
            AssignmentId = assignment.aws_id,
            Reason = "What a good job",
        )
        self.is_ok(resp)

        numBonuses = self.actors[0].worker.bonuspayment_set.count()
        self.assertEqual( numBonuses, 2 )

        # Check that another requester can't send a bonus
        with self.assertRaises(RequestError):
            resp = requester.send_bonus(
                WorkerId = self.actors[0].worker.aws_id,
                BonusAmount = "1.00",
                AssignmentId = assignment.aws_id,
                Reason = "What a good job",
            )

        # Check for send bonus on a worker/assignment
        # mismatch.
        with self.assertRaises(RequestError):
            resp = self.client.send_bonus(
                WorkerId = self.actors[1].worker.aws_id,
                BonusAmount = "1.00",
                AssignmentId = assignment.aws_id,
                Reason = "What a good job",
            )


    def test_worker_with_block(self):
        """
        Test that an assignment can't be accepted by a worker with
        a block
        """

        startTime = timezone.now()
        self.create_quals()
        self.create_workers()
        requester = self.create_new_client("req1")

        maxAssigns = 1
        lifetime = 10000
        assignDur = 1000
        reward = "0.13"
        title = "Create Task with Quals"
        desc = "Little bit of sugar"
        annot = "asdf"
        question = load_quesform(2)

        resp = self.client.create_hit(
            MaxAssignments = maxAssigns,
            LifetimeInSeconds = lifetime,
            AssignmentDurationInSeconds = assignDur,
            Reward = reward,
            Title = title,
            Description = desc,
            Question = question,
            RequesterAnnotation = annot,
            UniqueRequestToken="ureuw"
        )
        self.is_ok(resp)

        taskId = resp["HIT"]["HITId"]
        task = Task.objects.get(aws_id = taskId)


        # We are going to create a block for one of our
        # workers
        reason = "Because I don't like you"

        resp = self.client.create_worker_block(
            WorkerId = self.actors[0].worker.aws_id,
            Reason = reason
            )
        self.is_ok(resp)

        block = WorkerBlock.objects.get(
            worker = self.actors[0].worker
            )

        self.assertEqual( block.active, True )
        self.assertEqual( block.reason, reason )
        self.assertTrue( block.created > startTime )

        with self.assertRaises(WorkerBlockedError):
            assignment = self.actors[0].accept_task(task)

        # Delete the worker block
        reason = "Some mistake"
        resp = self.client.delete_worker_block(
            WorkerId = self.actors[0].worker.aws_id,
            Reason = reason
            )
        self.is_ok(resp)

        block = WorkerBlock.objects.get(
            worker = self.actors[0].worker
            )

        self.assertEqual( block.active, False )
        self.assertEqual( block.reason, reason )

        # Worker should now be able to access the
        # task.
        assignment = self.actors[0].accept_task(task)

    def test_access_limitations(self):
        """
        This test checks that other requesters can't access
        a requester's HITs and assignments, etc.
        """

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
        # Create a separate requester to test access constraints
        requester = self.create_new_client("req1")

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
        taskId = obj["HITId"]

        # Get the Task state so that we can see the stats change.
        resp = self.client.get_hit( HITId = taskId )
        self.is_ok(resp)

        # Check that an alternate requester can't get our hit
        RequestError = self.client._load_exceptions().RequestError
        with self.assertRaises(RequestError):
            resp = requester.get_hit( HITId = taskId)

        # Use workers to accept and complete the task.
        task = Task.objects.get( aws_id = taskId )
        assignment = self.actors[0].accept_task(task)

        # Submit data for the assignment to put assignment into
        # pending state.
        data = {
            "my_question_id": "Jimmy"
        }

        self.actors[0].complete_assignment(assignment, data)

        resp = self.client.get_assignment( AssignmentId = assignment.aws_id)
        self.is_ok(resp)

        # Check that another requester can't access our assignment.
        with self.assertRaises(RequestError):
            resp = requester.get_assignment(
                AssignmentId = assignment.aws_id
                )


        # Now we will have worker 2 take a look at the assignment
        assignment = self.actors[1].accept_task(task)

        # Submit data for the assignment to put assignment into
        # pending state.
        data = {
            "my_question_id": "Johns"
        }
        self.actors[1].complete_assignment(assignment, data)

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

        # Check that another requester can't view out reviewable hits
        with self.assertRaises( RequestError ):
            resp = requester.list_reviewable_hits(
                HITTypeId = taskTypeId,
                MaxResults = 10
            )

        # Check that another requester can't update the reviewable
        # hits to reviewing state

        with self.assertRaises( RequestError ):
            resp = requester.update_hit_review_status(HITId = taskId)

        # Transition this task from Reviewable to Reviewing.
        resp = self.client.update_hit_review_status(HITId = taskId)
        self.is_ok(resp)

        # Check that another requester can't see "Reviewing" state
        # HITs
        with self.assertRaises( RequestError ):
            resp = requester.list_reviewable_hits(
                HITTypeId = taskTypeId,
                Status="Reviewing",
                MaxResults = 10
            )
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

        # Check that another requester can't list assignments
        # associated with our HIT.
        with self.assertRaises(RequestError):
            requester.list_assignments_for_hit(
                HITId = taskId,
                AssignmentStatuses=["Approved", "Rejected"]
            )

        with self.assertRaises(RequestError):
            requester.list_assignments_for_hit(
                HITId = taskId,
                AssignmentStatuses=["Submitted"]
            )

        # Now let's review the assignments associated
        # with this task.

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


        # Check that another requester can't approve or reject
        # our assignments
        assignId = assignments[0]["AssignmentId"]

        with self.assertRaises(RequestError):
            requester.approve_assignment(
                AssignmentId = assignId
                )

        with self.assertRaises(RequestError):
            requester.reject_assignment(
                AssignmentId = assignId,
                RequesterFeedback = "Blarg"
                )

        resp = self.client.get_assignment( AssignmentId = assignId )
        self.is_ok(resp)

        obj = resp["Assignment"]
        self.assertEqual( obj["AssignmentId"], assignId )
        self.assertEqual( obj["AssignmentStatus"], "Submitted")

        # Approve first assignment

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
        with self.assertRaises(RequestError):
            resp = self.client.reject_assignment(
                AssignmentId = assignId,
                RequesterFeedback = "bs"
                )

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

        with self.assertRaises(RequestError):
            resp = requester.approve_assignment(
                AssignmentId = assignId,
                OverrideRejection = True
                )

        resp = self.client.get_assignment( AssignmentId = assignId )
        self.is_ok(resp)

        obj = resp["Assignment"]
        self.assertEqual( obj["AssignmentId"], assignId )
        self.assertEqual( obj["AssignmentStatus"], "Rejected")
