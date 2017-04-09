# File: mturk/workers.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the implementation of the views associated
# with the worker UI.
#

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.db.models import Q
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse

from mturk.models import *
from mturk.utils import MTurkBaseView
from mturk.fields import *
from mturk.questions import QuestionValidator

import logging
logger = logging.getLogger("mturk")
from lxml import etree
from urllib.parse import urlencode

class WorkerHomePage(LoginRequiredMixin, MTurkBaseView):
    """
    """

    def get(self, request):

        worker = self.get_worker(request)

        cxt = {
            "active" : "home",
            "worker" : worker,
            "earnings" : {
                "tasks" : 0.00,
                "bonuses" : 0.00,
                "total" : 0.00,
            },
            "tasks" : {
                "submitted" : {
                    "count" : 0,
                },
                "approved" : {
                    "count" : 0,
                    "rate" : "0%",
                },
                "rejected" : {
                    "count" : 0,
                    "rate" : "0%",
                },
                "pending" : {
                    "count" : 0,
                }
            },
        }
        return( render(request, "worker/home.html", cxt) )

class WorkerQualsPage(LoginRequiredMixin, MTurkBaseView):
    """
    """
    def get(self, request):

        worker = self.get_worker(request)

        offset, count = self.get_list_form(request)

        qualsList = Qualification.objects.filter(
            dispose=False
        ).order_by("-created")

        qualsPage = self.create_page(offset, count, qualsList)

        cxt = {
            "active" : "quals",
            "worker" : worker,
            "quals" : qualsPage,
        }
        return( render(request, "worker/quals.html", cxt) )


class WorkerQualInfoPage(LoginRequiredMixin, MTurkBaseView):
    """
    """
    def get(self, request, qual_id):

        worker = self.get_worker(request)

        qual_id = int(qual_id)
        qual = get_object_or_404(Qualification, pk = qual_id)

        cxt = {
            "active" : "quals",
            "worker" : worker,
            "qual" : qual,
        }
        return( render(request, "worker/qual_info.html", cxt) )

class QualPermanentDenial(Exception):
    def __init__(self):
        super().__init__(
            "You have already requested this Qualification and been denied. This qualification does not allow multiple attempts to request a qualification."
        )

class QualTemporaryDenial(Exception):
    def __init__(self, nextReqTime):
        super().__init__(
            "You have already requested this qualification and been denied. You have to wait until %s before you can request again" % nextReqTime
        )

class QualHasActiveRequest(Exception):
    def __init__(self):
        super().__init__(
            "You already have an active request for this qualification"
        )

class QualHasActiveGrant(Exception):
    def __init__(self):
        super().__init__(
            "You already have an active grant for this qualification"
        )

class QualPermamentGrantBlock(Exception):
    def __init__(self):
        super().__init__(
            "Your grant for this qualification has been revoked and this qualification does not allow multiple attempts to request it. Contact the Requester if you think this is in error"
            )

class WorkerRequestQual(LoginRequiredMixin, MTurkBaseView):
    """
    """

    def handle_requests(self, worker, qual):
        rejects = qual.qualificationrequest_set.filter(
            worker = worker,
            state = QualReqStatusField.REJECTED
            ).order_by("-last_request")
        if ( rejects.exists() ):
            if ( qual.retry_active ):
                req = rejects[0]
                nextReqTime = req.last_request + qual.retry_delay
                timestamp = timezone.now()
                if ( timestamp > nextReqTime ):
                    # Worker is allowed to re-request now
                    req.last_request = timestamp
                    # @todo - fix state here
                    # req.rejected = False
                    req.answer = ""
                    req.reason = ""
                    req.save()
                    return(req)
                else:
                    raise QualTemporaryDenial(nextReqTime)
            else:
                raise QualPermanentDenial()

        # There are no rejected requests present -
        # Let's see if there are any active requests present
        reqs = qual.qualificationrequest_set.filter(
            Q( worker = worker ) &
            ~ Q( state = QualReqStatusField.REJECTED )
        )

        if ( reqs.exists() ):
            raise QualHasActiveRequest()

        # Ok - we need to make an request for this user.
        req = QualificationRequest.objects.create(
            worker = worker,
            qualification = qual,
            last_request = timezone.now()
            )

        return(req)

    def handle_grants(self, worker, qual):
        activeGrants = qual.qualificationgrant_set.filter(
            worker = worker,
            active = True
            )
        if ( activeGrants.exists() ):
            raise QualHasActiveGrant()

        blockedGrants = qual.qualificationgrant_set.filter(
            worker = worker,
            active = False
            )

        if ( blockedGrants.exists() ):
            if ( not qual.retry_active ):
                raise QualPermamentGrantBlock()
            else:
                # Otherwise, we want to let the handle_requests
                # part of this view handle validation of existing
                # requests and timeouts
                pass

    def get(self, request, qual_id):

        worker = self.get_worker(request)

        qual_id = int(qual_id)
        qual = get_object_or_404(Qualification, pk = qual_id)

        try:
            if ( not qual.requestable ):
                raise Exception(
                    "Qualification %s is not Requestable" %
                    qual.aws_id
                )
            self.handle_grants(worker, qual)
            req = self.handle_requests(worker, qual)
        except Exception as exc:
            messages.error(request, str(exc))
            return(redirect( "worker-quals" ) )

        # We have create a request for this qualification
        # now lets figure out how to respond
        if ( qual.auto_grant ):
            # This is easy -  we can just grant the qualification
            # immediately.
            createParams = {
                "worker" : worker,
                "qualification" : qual,
            }
            if ( qual.auto_grant_locale is not None ):
                createParams["locale"] = qual.auto_grant_locale
            else:
                createParams["value"] = qual.auto_grant_value

            grant = QualificationGrant.objects.create( **createParams )

            req.state = QualReqStatusField.APPROVED
            req.save()

            messages.info(
                request, "Qualification Granted for %s" % qual.aws_id
            )
        elif ( qual.has_test ):
            # This qualification has a test that the worker must
            # complete before the qualification will be granted.
            return(redirect("worker-qual-test", req_id = req.id))
        else:
            req.state = QualReqStatusField.PENDING
            req.save()
            messages.info(
                request, "Qualification Request has been created. The Requester will respond with a decision."
                )

        return(redirect( "worker-quals" ) )


class WorkerQualRequestsPage(LoginRequiredMixin, MTurkBaseView):
    def get(self, request):
        worker = self.get_worker(request)

        offset, count = self.get_list_form(request)

        reqList = QualificationRequest.objects.filter(
            worker = worker
        ).order_by("-last_request")

        reqsPage = self.create_page(offset, count, reqList)

        cxt = {
            "active" : "quals",
            "worker" : worker,
            "requests" : reqsPage,
        }
        return( render(request, "worker/qual_reqs.html", cxt))

class WorkerQualGrantsPage(LoginRequiredMixin, MTurkBaseView):
    def get(self, request):
        worker = self.get_worker(request)

        offset, count = self.get_list_form(request)

        grantList = QualificationGrant.objects.filter(
            worker = worker
        ).order_by("-granted")

        grantPage = self.create_page(offset, count, grantList)

        cxt = {
            "active" : "quals",
            "worker" : worker,
            "grants" : grantPage
        }
        return( render(request, "worker/qual_grants.html", cxt))


class WorkerTasksPage(LoginRequiredMixin, MTurkBaseView):
    """
    """
    def get_task_groups(self):
        """
        Return a list of assignable, non-expired task objects which
        have a unique TaskType. Unfortunately, this this is not
        as trivial as it in theory should be because 'distinct' is
        not general purpose enough to work on explicit fields in all
        database types I want to use.
        """
        tasktypeList = Task.objects.filter(
            status = TaskStatusField.ASSIGNABLE,
            expires__gt = timezone.now()
            ).values("tasktype").distinct()

    def get(self, request):
        worker = self.get_worker(request)

        offset, count = self.get_list_form(request)

        # We want to filter for tasks of a particular tasktype
        # because then we can allow the worker to process tasks from
        # that group. So we want tasks in a unique tasktype grouping
        # Note that this is not easy and requires a couple of database
        # transactions.

        # First I'm going to filter for active tasks and then
        # pull out the distinct tasktypes object
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

        taskTypePage = self.create_page(offset, count, taskTypeList)

        cxt = {
            "active" : "tasks",
            "worker" : worker,
            "taskTypes" : taskTypePage,
        }

        return( render(request, "worker/tasks.html", cxt) )


class WorkerTaskInfoPage(LoginRequiredMixin, MTurkBaseView):

    def get(self, request, task_id):

        worker = self.get_worker(request)

        task_id = int(task_id)
        task = get_object_or_404(Task, pk = task_id)

        try:
            assignment = task.assignment_set.get(
                worker = worker,
                status = AssignmentStatusField.ACCEPTED,
                dispose=False,
                )
        except:
            assignment = None

        cxt = {
            "active" : "tasks",
            "worker" : worker,
            "task" : task,
            "assignment" : assignment,
        }

        q = QuestionValidator()
        quesType,quesData = q.extract( task.question )

        assignId = "ASSIGNMENT_ID_NOT_AVAILABLE"
        if ( assignment is not None ):
            assignId = assignment.aws_id

        cxt["quesType"] = quesType
        if ( quesType == "QuestionForm" ):
            url = reverse("worker-task-submit", kwargs={"task_id": task_id})
            cxt["form"] = QuestionForm(url, quesData)
        elif ( quesType == "ExternalQuestion" ):
            submitUrl = reverse("worker-ext-submit")
            urlArgs = urlencode({
                "assignmentId" : assignId,
                "hitId" : task.aws_id,
                "turkSubmitTo": submitUrl,
                "workerId" : worker.aws_id,
                })
            cxt["ext"] = {
                "url" : "%s?%s" % (quesData.url,urlArgs),
                "height" : quesData.height
                }

        elif ( quesType == "HTMLQuestion" ):
            submitUrl = reverse("worker-ext-submit")
            contentUrl = reverse("worker-html-ques")
            urlArgs = urlencode({
                "assignmentId" : assignId,
                "hitId" : task.aws_id,
                "turkSubmitTo": submitUrl,
                "workerId" : worker.aws_id,
                })

            cxt["ext"] = {
                "url" : "%s?%s" % (contentUrl, urlArgs),
                "height" : quesData.height
            }


        return( render(request, "worker/task_view.html", cxt) )

class WorkerHTMLQuestionContent(View):
    """
    This page hosts content for the HTMLQuestion form of mturk
    tasks. The idea here is that this content is loaded in an iframe
    that is pointing back to the same mturk origin with arguments
    in the same way that the external question points to another site.

    @note - this view is not login protected - like the external
       question.
    """

    def get(self, request):

        form = ExternalQuestionForm(request.GET)
        if ( not form.is_valid() ):
            raise SuspiciousOperation("Invalid Form Data: %s" % form.errors.as_data())

        # We will check all the IDs passed in the form to confirm that
        # this isn't some aberrant request.
        assignment = get_object_or_404(Assignment, aws_id=form.assignmentId)
        worker = get_object_or_404(Worker, aws_id=form.workerId)
        task = get_object_or_404(Task, aws_id=form.hitId)

        if ( (assignment.worker != worker)
             (assignment.task != task)
        ):
            raise SuspiciousOperation("Assignment, Worker, and Task do not Match!")

        # Pull the task question data
        q = QuestionValidator()
        quesType,quesData = q.extract( task.question )

        if ( quesType != "HTMLQuestion" ):
            raise SuspiciousOperation("Attempt to use HTMLQuestion Op on Non HTMLQuestion Task")

        resp = HttpResponse()
        resp.write( quesData.html )

        return(resp)


class WorkerTaskAccept(LoginRequiredMixin, MTurkBaseView):

    def check_quals(self, task, worker ):
        """
        Check if the worker meets all of the qualifications for
        this task.
        """
        # @todo - it may be a good idea to include information
        #   here that signals to the user what they failed
        #   qualify for.
        for qualreq in task.tasktype.qualifications.all():
            try:
                grant = worker.qualificationgrant_set.get(
                    active = True,
                    qualification = qualreq.qualification
                )
            except:
                grant = None

            if not qualreq.check_grant(grant):
                return(False)

        return(True)

    def get(self, request, task_id):

        worker = self.get_worker(request)

        task_id = int(task_id)
        task = get_object_or_404(Task, pk = task_id)

        # Check to make sure that the worker has not already
        # submitted an assignment
        try:
            # Get any assignment associated with the worker
            # regardless of status
            assignment = task.assignment_set.get(
                worker = worker,
                dispose = False
                )
            # The worker has already processed some part of this task
            # so they cannot accept it again.
            if ( assignment.status == AssignmentStatusField.ACCEPTED ):
                messages.info(
                    request, "You have already accepted this task"
                    )
            else:
                messages.warning(
                    request,
                    "You have already completed an assignment for this task"
                    )
        except:
            # Check if the worker meets all of the qualifications
            # necessary to accept this qualification
            if ( not self.check_quals(task, worker) ):
                messages.error(
                    request,
                    "You do not meet all the qualifications for this task"
                )
            elif ( not (task.available_assignment_count > 0) ):
                messages.error(
                    request,
                    "No Available Assignment Slots at this Time"
                )
            else:
                # Create an assignment
                acceptTime = timezone.now()
                deadlineTime = acceptTime + task.tasktype.assignment_duration
                assignment = Assignment.objects.create(
                    task = task,
                    worker = worker,
                    accepted = acceptTime,
                    deadline = deadlineTime
                )

                task.check_state_change()

        # Redirect to the task view.
        return( redirect("worker-task-info", task_id = task_id))

class WorkerTaskReturn(LoginRequiredMixin, MTurkBaseView):

    def get(self, request, task_id):

        worker = self.get_worker(request)

        task_id = int(task_id)
        task = get_object_or_404(Task, pk = task_id)

        try:
            assignment = task.assignment_set.get(
                worker = worker,
                status = AssignmentStatusField.ACCEPTED,
                dispose = False,
                )
            assignment.dispose = True
            assignment.save()

            worker.returned_hits += 1
            worker.save()
            messages.info(
                request,
                "Successfully Returned HIT: %s" % task.aws_id
            )
        except Exception as exc:
            logger.error("Worker[%s] Return Fails on Task[%s]: %s" % worker.aws_id, task.aws_id, str(exc))
            messages.error(
                request,
                "Failed to Return Assignment for Task: %s" % task.aws_id
            )

        return( redirect( "worker-tasks") )

class WorkerExternalSubmit(View):
    """
    This view is for receiving the results of a task
    completed by a worker through the HTMLQuestion or
    ExternalQuestion mode.
    @note - this view is not protected by a login because
      it can't be.
    """

    def encode_answer(self, request):

        root = etree.Element(
            "QuestionFormAnswers",
            xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd"
            )
        data = {}
        for name,value in request.POST.items():
            if ( name == "assignmentId" ):
                continue

            ans = etree.SubElement(root, "Answer")
            qId = etree.SubElement(ans, "QuestionIdentifier")
            qId.text = name

            content = etree.SubElement(ans, "FreeTextAnswer")
            content.text = value

        answerStr = etree.tostring(root)
        return(answerStr.decode("utf-8"))


    def post(self, request):
        """
        """
        # We will pull the assignment ID from the request
        assignmentId = request.POST.get("assignmentId", None)
        if ( assignmentId == None ):
            raise PermissionDenied()

        try:
            assignment = Assignment.objects.get(
                aws_id = assignmentId
                )
        except:
            raise SuspiciousOperation("Invalid Assignment ID: %s" % assignmentId)

        if ( assignment.status != AssignmentStatusField.ACCEPTED ):
            raise SuspiciousOperation("Invalid Assignment State: %s" % assignmentId)

        answer = self.encode_answer(request)
        assignment.answer = answer
        assignment.status = AssignmentStatusField.SUBMITTED
        assignment.submitted = timezone.now()

        if ( assignment.task.tasktype.auto_approve is None ):
            # We automatically approve the task because there
            # is not delay - ?
            # @todo - confirm how the service actually responds
            pass

        assignment.save()

        assignment.task.check_state_change()

        return( render(request, "worker/extques_response.html", {} ) )

class WorkerTaskSubmit(LoginRequiredMixin, MTurkBaseView):
    """
    Handle the worker submission of answers for QuestionForm
    type objects. This does not handle External or HTMLQuestion
    type tasks.
    """
    def post(self, request, task_id):
        worker = self.get_worker(request)

        task_id = int(task_id)
        task = get_object_or_404(Task, pk = task_id)

        cxt = {
            "active" : "tasks",
            "worker" : worker,
            "task" : task,
            "assignment" : None,
        }

        q = QuestionValidator()
        name, quesRoot = q.extract(task.question)
        if ( name != "QuestionForm" ):
            raise SuspiciousOperation("Invalid Task Question for Submittal")

        try:
            assignment = task.assignment_set.get(
                worker = worker,
                status = AssignmentStatusField.ACCEPTED,
                dispose = False
                )
        except:
            # There is no assignment available for this
            # user.
            messages.error(request, "No Accepted Assignment for Task!")
            return( redirect( "worker-task-info", task_id=task_id) )


        # The user has provided a schemat that we can validate the
        # answers against
        url = reverse("worker-task-submit", kwargs={"task_id" : task_id})
        form = QuestionForm( url, quesRoot )

        form.process(request.POST)
        if ( not form.is_valid() ):
            messages.error(
                request,
                "Invalid Form Submission: Please address the problems below"
                )
            cxt["assignment"] = assignment
            cxt["quesType"] = "QuestionForm"
            cxt["form"] = form
            return( render(request, "worker/task_view.html", cxt ))

        # Handle Question Form Here
        assignment.answer = form.generate_worker_answer()
        assignment.status = AssignmentStatusField.SUBMITTED
        assignment.submitted = timezone.now()
        assignment.save()

        task.check_state_changed()

        # Get the next task in this task group that the
        # worker can work on

        taskList = task.tasktype.task_set.filter(
            dispose = False,
            status = TaskStatusField.ASSIGNABLE,
            expires__gt = timezone.now(),
            )
        # Make sure that we present a task that the worker
        # has not submitted an assignment for already -
        # @note This is kind of a hack - there must be a better
        #  way to make this DB query.
        newTask = None
        for task in taskList:
            if not task.has_assignment(worker):
                newTask = task
                break

        if ( newTask is not None ):
            return( redirect("worker-task-info", task_id=newTask.id) )
        else:
            # This worker has completed all assignments in this
            # group - we redirect back to the main task list view
            return( redirect("worker-tasks") )


class WorkerSettingsPage(LoginRequiredMixin, MTurkBaseView):
    """
    """
    def get(self, request):

        cxt = {
            "active" : "settings"
        }

        return( render(request, "worker/settings.html", cxt) )
