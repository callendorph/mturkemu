# File: mturk/worker/views.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the implementation of the views associated with
# the worker UI.
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

from mturk.xml.questions import QuestionValidator
from mturk.worker.actor import WorkerActor

import logging
logger = logging.getLogger("mturk")
from lxml import etree
from urllib.parse import urlencode

class WorkerHomePage(LoginRequiredMixin, MTurkBaseView):
    """
    """

    def get(self, request):

        worker = self.get_worker(request)
        actor = WorkerActor(worker)

        cxt = {
            "active" : "home",
            "worker" : worker,
        }
        cxt.update( actor.get_statistics() )
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

class WorkerRequestQual(LoginRequiredMixin, MTurkBaseView):
    """
    """

    def get(self, request, qual_id):

        worker = self.get_worker(request)
        actor = WorkerActor(worker)

        qual_id = int(qual_id)
        qual = get_object_or_404(Qualification, pk = qual_id)

        try:
            req = actor.create_qual_request(qual)
        except Exception as exc:
            messages.error(request, str(exc))
            return(redirect( "worker-quals" ) )

        grant = actor.process_qual_request(qual, req)
        if grant:
            messages.info(
                request, "Qualification Granted for %s" % qual.aws_id
            )
        elif ( req.state == QualReqStatusField.PENDING ):
            messages.info(
                request, "Qualification Request has been created. The Requester will respond with a decision."
                )
        else:
            # This qualification has a test that the worker must
            # complete before the qualification will be granted.
            return(redirect("worker-qual-test", req_id = req.id))

        return(redirect( "worker-quals" ) )


class WorkerQualRequestsPage(LoginRequiredMixin, MTurkBaseView):
    def get(self, request):
        worker = self.get_worker(request)
        actor = WorkerActor(worker)
        offset, count = self.get_list_form(request)

        reqList = actor.list_qual_requests()

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
        actor = WorkerActor(worker)
        offset, count = self.get_list_form(request)

        grantList = actor.list_qual_grants()

        grantPage = self.create_page(offset, count, grantList)

        cxt = {
            "active" : "quals",
            "worker" : worker,
            "grants" : grantPage
        }
        return( render(request, "worker/qual_grants.html", cxt))

class WorkerCompleteQualTest(LoginRequiredMixin, MTurkBaseView):
    """
    Worker Qualification Test View

    """

    def get(self, request, req_id):
        """
        We need to pull the test out of the qualification, parse
        it and then generate the content that will be used in
        the test form.
        """

        worker = self.get_worker(request)
        actor = WorkerActor(worker)

        req_id = int(req_id)
        req = get_object_or_404(QualificationRequest, pk = req_id)

        try:
            actor.check_test_submittable(req)
        except Exception as exc:
            messages.error(
                request,
                "Qualification Not Testable: %s" % str(exc)
            )
            return( redirect( "worker-quals" ) )

        q = QuestionValidator()
        name,form = q.extract(req.qualification.test)
        if ( name != "QuestionForm" ):
            raise SuspiciousOperation("Invalid Qualification Question Object")

        url = reverse("worker-qual-test", kwargs={"req_id" : req_id})

        cxt = {
            "active" : "quals",
            "worker" : worker,
            "url" : url,
            "form" : form
        }

        return(render(request, "worker/qual_test.html", cxt))

    def post(self, request, req_id):
        """
        The worker submits the answer to the test via POST
        We need to then dynamically create a form object to
        validate the input and then compare against an
        answer key if available.
        if No answer key, then requester must manually approve
        if answer key, we can auto generate a qualification grant.
        """
        worker = self.get_worker(request)
        actor = WorkerActor(worker)

        req_id = int(req_id)
        req = get_object_or_404(QualificationRequest, pk = req_id)

        try:
            actor.submit_test_answer(req, request.POST)
        except InvalidQuestionFormError as exc:
            messages.error(
                request,
                "There was a problem with the form, please correct any issues below"
            )

            url = reverse("worker-qual-test", kwargs={"req_id" : req_id})
            cxt = {
                "active" : "quals",
                "worker" : worker,
                "form" : exc.form,
                "url" : url,
            }
            return(render(request, "worker/qual_test.html", cxt))

        except Exception as exc:
            messages.error(
                request,
                "Failed to process test answer for Qualification: %s" %
                str(exc)
            )
            return( redirect( "worker-quals" ) )

        if ( req.state == QualReqStatusField.APPROVED ):
            messages.info(
                request,
                "Successfully acquired a grant for Qualification '%s'" %
                req.qualification.name
            )
        elif ( req.state == QualReqStatusField.REJECTED ):
            message.error(
                request,
                "Failed to acquire Qualification '%s'" %
                req.qualification.name
            )
        elif ( req.state == QualReqStatusField.PENDING ):
            messages.info(
                request,
                "Test Answers for Qualification '%s' have been received. The requester will review your answers and grant or reject your qualification shortly." %
                req.qualification.name
            )


        return(redirect("worker-quals"))


class WorkerTasksPage(LoginRequiredMixin, MTurkBaseView):
    """
    """

    def get(self, request):
        worker = self.get_worker(request)
        actor = WorkerActor(worker)
        offset, count = self.get_list_form(request)

        taskTypeList = actor.list_task_groups()

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
            cxt["url"] = reverse("worker-task-submit", kwargs={"task_id": task_id})
            cxt["form"] = quesData
        elif ( quesType == "ExternalQuestion" ):
            submitUrl = reverse("worker-ext-submit")
            submitUrl = settings.BASE_URL + submitUrl
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
                    qualification = qualreq.qualification,
                    dispose=False
                )
            except:
                grant = None

            if not qualreq.check_grant(grant):
                return(False)

        return(True)

    def get(self, request, task_id):

        worker = self.get_worker(request)
        actor = WorkerActor(worker)

        task_id = int(task_id)
        task = get_object_or_404(Task, pk = task_id)

        try:
            actor.accept_task(task)
        except Exception as exc:
            messages.error(
                request,
                "Failed to Accept Task: %s" % str(exc)
            )

        return( redirect("worker-task-info", task_id = task_id))

class WorkerTaskReturn(LoginRequiredMixin, MTurkBaseView):

    def get(self, request, task_id):

        worker = self.get_worker(request)
        actor = WorkerActor(worker)

        task_id = int(task_id)
        task = get_object_or_404(Task, pk = task_id)

        try:
            actor.return_task(task)
            messages.info(
                request,
                "Successfully Returned Task: %s" % task.aws_id
            )
        except Exception as exc:
            messages.error(
                request,
                "Failed to Return Assignment for Task: %s" % str(exc)
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

        actor = WorkerActor(assignment.worker)
        actor.complete_assignment(assignment, request.POST)

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

        actor = WorkerActor(worker)
        try:
            actor.complete_assignment( assignment, request.POST )
        except InvalidQuestionFormError as exc:
            messages.error(
                request,
                "Invalid Form Submission: Please address the problems below"
                )
            cxt["assignment"] = assignment
            cxt["quesType"] = "QuestionForm"
            url = reverse(
                "worker-task-submit", kwargs={"task_id" : task_id}
            )
            cxt["url"] = url
            cxt["form"] = exc.form
            return( render(request, "worker/task_view.html", cxt ))

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
