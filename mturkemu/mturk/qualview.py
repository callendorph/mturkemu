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

        req_id = int(req_id)
        req = get_object_or_404(QualificationRequest, pk = req_id)

        if ( not req.qualification.has_test):
            messages.error(
                request,
                "Qualification[%s] does not have a test for you to complete." % req.qualification.aws_id
            )
            return( redirect( "worker-quals" ) )

        if ( not req.is_idle() ):
            messages.error(
                request,
                "QualificationRequest[%d] is not in a valid state for allowing the worker to test." % req.id
            )
            return( redirect( "worker-quals" ) )


        url = reverse("worker-qual-test", kwargs={"req_id" : req_id})

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

        req_id = int(req_id)
        req = get_object_or_404(QualificationRequest, pk = req_id)

        if ( not req.qualification.has_test):
            messages.error(
                request,
                "Qualification[%s] does not have a test for you to complete." % req.qualification.aws_id
            )
            return( redirect( "worker-quals" ) )

        if ( not req.is_idle() ):
            messages.error(
                request,
                "QualificationRequest[%d] is not in a valid state for allowing the worker to test." % req.id
            )
            return( redirect( "worker-quals" ) )

        url = reverse("worker-qual-test", kwargs={"req_id" : req_id})

        q = QuestionValidator()
        name = q.determine_type(req.qualification.test)
        if ( name != "QuestionForm" ):
            raise SuspiciousOperation("Invalid Qualification Question Object")
        quesRoot = self.parse(name, req.qualification.test)

        form = QuestionForm( url, quesRoot )

        form.process(request.POST)
        if ( not form.is_valid() ):
            logger.error(
                "Failed to process Question Form Answer Data: %s" %
                pformat(form.errors)
            )
            cxt = {
                "active" : "quals",
                "worker" : worker,
                "form" : form
            }

            return(render(request, "worker/qual_test.html", cxt))

        # Now let's score the answer from the worker if there is an
        # answer key.
        if ( len(req.qualification.answer) > 0 ):
            ans = AnswerKey(req.qualification.answer)

            grantQual = False
            grantScore = 0

            try:
                grantScore = ans.score(form)
                grantQual = True
                req.state = QualReqStatusField.APPROVED
            except Exception as exc:
                # The form Answer was incorrect
                # we must reject the qualification request
                # for this worker
                logger.error("Qualifcation Test Scoring Fails: %s" % str(exc))
                logger.error("Traceback: %s" % traceback.format_exc() )

                req.state = QualReqStatusField.REJECTED
                message.error(
                    request,
                    "Failed to acquire Qualification '%s': %s" %
                    (req.qualification.name, str(exc))
                    )

            if ( grantQual ):
                logger.info("Qualification Test Scored: %d" % grantScore)

                grant = QualificationGrant.objects.create(
                    worker = worker,
                    qualification = req.qualification,
                    value = grantScore,
                )

                messages.info(
                    request,
                    "Successfully acquired a grant for Qualification '%s'" %
                    req.qualification.name
                )
        else:
            # There was no answer key - so the requester must manually
            # approve
            req.state = QualReqStatusField.PENDING

        # Save the Worker's answer
        req.answer = form.generate_worker_answer()
        req.last_submitted = timezone.now()
        req.save()

        return(redirect("worker-quals"))
