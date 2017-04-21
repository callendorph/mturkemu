# File: mturk/worker/QualsActor.py
# Author: Carl Allendorph
#
# Descripion:
#   This file contains the implementation of the worker actor
# code that implements the appropriate behavior for interacting
# with worker qualifications.
#

from mturk.models import *
from mturk.xml.questions import *
from mturk.xml.answerkey import AnswerKey
from mturk.xml.quesformanswer import QFormAnswer
from mturk.errors import InvalidQuestionFormError

import traceback

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

class InvalidQualificationTypeError(Exception):
    def __init__(self):
        super().__init__(
            "Qualification does not have a test for the worker to complete"
            )

class InvalidQualRequestStateError(Exception):
    def __init__(self):
        super().__init__(
            "Qualification Request is invalid state to allow worker to submit answers to a qualification test"
            )


class QualsActor(object):
    """
    This class handles implementing the code that allows a worker
    to request qualifications, and interact with qualifications.
    """
    def __init__(self, worker):
        self.worker = worker

    def list_qual_requests(self):
        reqList = QualificationRequest.objects.filter(
            worker = self.worker
        ).order_by("-last_request")
        return(reqList)

    def list_qual_grants(self):
        grantList = QualificationGrant.objects.filter(
            worker = self.worker,
            dispose=False
        ).order_by("-granted")
        return(grantList)

    def check_test_submittable(self, req):
        if ( not req.qualification.is_active() ):
            raise InvalidQualStateError(req.qualification.aws_id)

        if ( not req.qualification.has_test):
            raise InvalidQualificationTypeError()

        if ( not req.is_idle() ):
            raise InvalidQualRequestStateError()

    def submit_test_answer(self, req, data):
        """
        Submit answers to a qualification request test in order to
        attempt to acquire a grant for that qualifcation.
        @param req QualificationRequest object for the qualification
           that the worker is attempting to acquire
        @param data dict-like object containing the form submission
           data.
        """

        self.check_test_submittable(req)

        q = QuestionValidator()
        name,form = q.extract(req.qualification.test)
        if ( name != "QuestionForm" ):
            raise Exception("Internal Error: Qualification test is not of proper Type")

        form.process(data)
        if ( not form.is_valid() ):
            raise InvalidQuestionFormError(form)

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

            if ( grantQual ):
                logger.info("Qualification Test Scored: %d" % grantScore)

                grant = QualificationGrant.objects.create(
                    worker = self.worker,
                    qualification = req.qualification,
                    value = grantScore,
                )

        else:
            # There was no answer key - so the requester must manually
            # approve
            req.state = QualReqStatusField.PENDING

        # Save the Worker's answer
        ans = QFormAnswer()
        req.answer = ans.encode(form)
        req.last_submitted = timezone.now()
        req.save()


    def process_qual_request(self, qual, req):
        """
        For the QualificationRequest object returned by the
        'create_qual_request' method, handle transitioning the request
        into the appropriate state and generating a grant if necessary.
        """
        if ( qual.auto_grant ):
            # This is easy -  we can just grant the qualification
            # immediately.
            createParams = {
                "worker" : self.worker,
                "qualification" : qual,
            }
            if ( qual.auto_grant_locale is not None ):
                createParams["locale"] = qual.auto_grant_locale
            else:
                createParams["value"] = qual.auto_grant_value

            grant = QualificationGrant.objects.create( **createParams )

            req.state = QualReqStatusField.APPROVED
            req.save()

            return(grant)
        elif ( qual.has_test ):
            # worker must take a test in order to acquire
            # the qualification grant.
            return(None)
        else:
            # No Test - which means that the grant must be
            # manually approved by the requester
            req.state = QualReqStatusField.PENDING
            req.save()
            return(None)

    def create_qual_request(self, qual):
        """
        Get/Create either the existing qualification request object for this
        worker for the passed 'qual' object or throw an exception.
        """
        if ( not qual.requestable ):
            raise Exception(
                "Qualification %s is not Requestable" %
                qual.aws_id
            )

        if ( not qual.is_active() ):
            raise Exception(
                "Qualification %s is not Active" %
                qual.aws_id
            )

        self.check_existing_grants(self.worker, qual)
        req = self.check_existing_requests(self.worker, qual)

        return(req)


    def check_existing_requests(self, worker, qual):
        """
        Check for existing qualification requests and
        validate that request if it exists.
        This method either raises an error or returns
        a valid QualificationRequest object.
        """
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
                    # The 'process' method above will handle
                    # transition the request into the appropriate
                    # new state.
                    req.state = QualReqStatusField.IDLE
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
            req = reqs[0]
            if ( req.state == QualReqStatusField.IDLE and req.qualification.has_test):
                return(req)

            # Otherwise there is an actve request
            raise QualHasActiveRequest()

        # Ok - we need to make an request for this user.
        req = QualificationRequest.objects.create(
            worker = worker,
            qualification = qual,
            last_request = timezone.now()
            )

        return(req)


    def check_existing_grants(self, worker, qual):
        """
        Check if the worker has an active grant for the
        qualification or if the worker's grant has been
        deactivated.
        """
        activeGrants = qual.qualificationgrant_set.filter(
            worker = worker,
            active = True,
            dispose = False,
            )
        if ( activeGrants.exists() ):
            raise QualHasActiveGrant()

        blockedGrants = qual.qualificationgrant_set.filter(
            worker = worker,
            active = False,
            dispose = False
            )

        if ( blockedGrants.exists() ):
            if ( not qual.retry_active ):
                raise QualPermamentGrantBlock()
            else:
                # Otherwise, we want to let the handle_requests
                # part of this view handle validation of existing
                # requests and timeouts
                pass
