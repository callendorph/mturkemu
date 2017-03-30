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
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin

from mturk.models import *
from mturk.utils import MTurkBaseView
from mturk.fields import *

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


class WorkerTasksPage(LoginRequiredMixin, View):
    """
    """
    def get(self, request):

        cxt = {
            "active" : "tasks"
        }

        return( render(request, "worker/tasks.html", cxt) )


class WorkerSettingsPage(LoginRequiredMixin, View):
    """
    """
    def get(self, request):

        cxt = {
            "active" : "settings"
        }

        return( render(request, "worker/settings.html", cxt) )
