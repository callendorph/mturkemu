# File: mturk/worker/TasksActor.py
# Author: Carl Allendorph
#
# Description
#   This file contains the implementation of methods that handle
# how a worker interacts with the tasks in the system.

from django.utils import timezone

from mturk.models import *
from mturk.fields import *
from mturk.errors import InvalidQuestionFormError
from mturk.xml.quesformanswer import QFormAnswer

class AssignmentAlreadyAccepted(Exception):
    def __init__(self):
        super().__init__("Worker has Already Accepted this Assignment")

class TaskAlreadyHasAssignment(Exception):
    def __init__(self):
        super().__init__("Worker has Already Submitted an Assignment for this Task")


class TaskPrereqError(Exception):
    def __init__(self):
        super().__init__("Worker does not have qualification grants to meet all of the necessary qualifications for this task.")

class TaskNotAvailableError(Exception):
    def __init__(self):
        super().__init__("This task is not available to be assigned")

class TasksActor(object):

    def __init__(self, worker):
        self.worker = worker

    def list_task_groups(self):
        """
        Generate a queryset for available task groups that the
        worker can view and begin interacting with.
        """
        # We want to filter for tasks of a particular tasktype
        # because then we can allow the worker to process tasks from
        # that group. So we want tasks in a unique tasktype grouping
        # Note that this is not easy and requires a couple of database
        # transactions.

        tasktypeIdList = Task.objects.filter(
            status = TaskStatusField.ASSIGNABLE,
            expires__gt = timezone.now()
            ).order_by(
                "expires"
            ).values_list("tasktype", flat=True).distinct()

        taskTypeList = TaskType.objects.filter(
            pk__in = tasktypeIdList
            )

        # @todo - this should also filter out tasks that the
        #    worker has already submitted an assignment for
        #    currently - we don't handle this well.

        return(taskTypeList)


    def check_prerequisite_quals(self, tasktype):
        """
        Check if the worker has the necessary qualification grants
        that are required for this task.
        """
        for qualreq in tasktype.qualifications.all():
            try:
                grant = self.worker.qualificationgrant_set.get(
                    active = True,
                    qualification = qualreq.qualification
                )
            except:
                grant = None

            if not qualreq.check_grant(grant):
                return(False)
        return(True)


    def accept_task(self, task):
        """
        Worker accepts an assignment for a particular task.
        If this method is unsuccessful, an exception is raised.
        """

        try:
            assignment = task.assignment_set.get(
                worker = self.worker,
                dispose = False
            )

            if ( assignment.status == AssignmentStatusField.ACCEPTED ):
                raise AssignmentAlreadyAccepted()
            else:
                raise TaskAlreadyHasAssignment()

        except Assignment.DoesNotExist:
            if ( not self.check_prerequisite_quals(task.tasktype) ):
                raise TaskPrereqError()
            elif ( task.status != TaskStatusField.ASSIGNABLE ):
                raise TaskNotAvailableError()
            else:
                acceptTime = timezone.now()
                deadlineTime = acceptTime + task.tasktype.assignment_duration
                assignment = Assignment.objects.create(
                    task = task,
                    worker = self.worker,
                    accepted = acceptTime,
                    deadline = deadlineTime
                )
                return(assignment)

    def return_task(self, task):
        """
        Worker returns an assignment for particular task. This is like
        the worker deciding that they don't want to do this task
        after all.
        """

        assignment = task.assignment_set.get(
            worker = self.worker,
            status = AssignmentStatusField.ACCEPTED,
            dispose = False,
        )
        assignment.dispose = True
        assignment.save()

        self.worker.returned_hits += 1
        self.worker.save()


    def complete_assignment(self, assignment, data):
        """
        Complete a task assignment by submitting data that answers
        the questions of the task.
        @param assignment the task assignment that this data is
            intended to complete
        @param data dict-like object or a QuestionForm object that
            contains the values submitted by the worker
        """

        if ( assignment.status != AssignmentStatusField.ACCEPTED or assignment.dispose):
            raise InvalidAssignmentStateError()

        ans = QFormAnswer()

        q = QuestionValidator()
        name, form = q.extract(assignment.task.question)
        if ( name == "QuestionForm" ):
            form.process(data)
            if ( not form.is_valid() ):
                raise InvalidQuestionFormError(form)

            ansStr = ans.encode(form)
        else:
            ansStr = ans.encode(data)

        assignment.answer = ansStr
        assignment.status = AssignmentStatusField.SUBMITTED
        assignment.submitted = timezone.now()
        # Set the auto approve time
        aaTS = assignment.submitted + assignment.task.tasktype.auto_approve
        assignment.auto_approve = aaTS

        assignment.save()
