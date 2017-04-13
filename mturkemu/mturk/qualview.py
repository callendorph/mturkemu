# File: mturk/qualview.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the implementation of the worker qualification
# test/answer view. This view allows the worker to acquire a
# qualification by taking a test.
#
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone

from mturk.models import *
from mturk.utils import MTurkBaseView
from mturk.questions import QuestionValidator
from mturk.quesform import QuestionForm
from mturk.answerkey import AnswerKey
from mturk.fields import *
from mturk.worker.actor import WorkerActor

from pprint import pformat
import traceback
import logging
logger = logging.getLogger("mturk")

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
