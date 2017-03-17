# File: mturk/requester.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the implementation of views for the
# requester interface.
#

from django.conf import settings
from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin

from mturk.models import *
from mturk.utils import *
from mturk.fields import *

import random
import string

class RequesterHomePage(LoginRequiredMixin, MTurkBaseView):
    """
    """

    def get(self, request):

        requester = self.get_requester(request)
        cxt = {
            "active": "home",
            "requester": requester,
        }
        return( render(request, "requester/home.html", cxt) )

class RequesterQualsPage(LoginRequiredMixin, MTurkBaseView):
    """
    """

    def get(self, request):

        requester = self.get_requester(request)

        offset, count = self.get_list_form(request)

        quals = Qualification.objects.filter(
            requester = requester,
            dispose = False
            ).order_by("-created")

        qualsPage = self.create_page(offset, count, quals)

        cxt = {
            "active": "quals",
            "requester": requester,
            "quals" : qualsPage,
        }
        return( render(request, "requester/quals.html", cxt) )

class RequesterQualRequestsPage(LoginRequiredMixin, MTurkBaseView):

    def get(self, request):

        requester = self.get_requester(request)

        offset, count = self.get_list_form(request)

        reqList = QualificationRequest.objects.filter(
            Q(qualification__requester = requester) &
            ~Q(state = QualReqStatusField.REJECTED)
        ).order_by("-last_request")

        reqsPage = self.create_page(offset, count, reqList)

        cxt = {
            "active": "quals",
            "requester": requester,
            "requests" : reqsPage,
        }
        return( render( request, "requester/qual_requests.html", cxt) )

class RequesterQualRequestApprove(LoginRequiredMixin, MTurkBaseView):

    def get(self, request, req_id):
        requester = self.get_requester(request)

        req_id = int(req_id)
        req = get_object_or_404(QualificationRequest, pk=req_id)

        # Create a Grant with just a default value of 1

        grant = QualificationGrant.objects.create(
            worker = req.worker,
            qualification = req.qualification,
            value = 1
        )

        # Remove the qual request
        req.delete()

        return( redirect("requester-qual-requests") )

class RequesterQualRequestReject(LoginRequiredMixin, MTurkBaseView):

    def get(self, request, req_id):
        requester = self.get_requester(request)

        req_id = int(req_id)
        req = get_object_or_404(QualificationRequest, pk=req_id)

        req.state = QualReqStatusField.REJECTED
        req.reason = "Rejected via Website"
        req.save()

        return( redirect("requester-qual-requests") )


class RequesterQualGrantsPage(LoginRequiredMixin, MTurkBaseView):

    def get(self, request):
        requester = self.get_requester(request)

        offset, count = self.get_list_form(request)

        grants = QualificationGrant.objects.filter(
            qualification__requester = requester,
            active = True
            )

        grantsPage = self.create_page(offset, count, grants)

        cxt = {
            "active": "quals",
            "requester": requester,
            "grants" : grantsPage,
        }
        return( render( request, "requester/qual_grants.html", cxt) )

class RequesterQualsCreate(LoginRequiredMixin, MTurkBaseView):
    def get(self, request):
        requester = self.get_requester(request)

        cxt = {
            "active": "quals",
            "requester": requester,
            "form" : QualCreateForm()
        }
        return( render( request, "requester/qual_create.html", cxt) )

    def post(self, request):
        requester = self.get_requester(request)
        cxt = {
            "active": "quals",
            "requester": requester,
        }

        form = QualCreateForm(request.POST)
        if ( not form.is_valid() ):
            cxt["form"] = form
            return( render( request, "requester/qual_create.html", cxt) )

        # Process the request
        name = form.cleaned_data["name"]
        desc = form.cleaned_data["description"]

        has_duplicate = Qualification.objects.filter(
            requester = requester,
            name = name
        ).exists()

        if ( has_duplicate ):
            raise Exception("Requester already has Qualification with Name: %s" % name)

        qual = Qualification.objects.create(
            requester = requester,
            name = name,
            description = desc,
            auto_grant = False,
        )

        return( redirect("requester-quals") )


class RequesterQualInfo(LoginRequiredMixin, MTurkBaseView):
    """
    """

    def prepare_qual_info(self, qual):
        ret = [
            { "label" : "AWS Id", "value" : qual.aws_id, },
            { "label" : "Name", "value" : qual.name, },
            { "label" : "Description", "value" : qual.description, },
            { "label" : "Auto-Grant?", "value" : qual.auto_grant, },
        ]
        if ( qual.auto_grant_locale is None ):
            ret.append(
                { "label" : "Auto-Grant Value", "value" : qual.auto_grant_value, }
            )
        else:
            ret.append(
                {
                    "label" : "Auto-Grant Locale",
                    "value" : str(qual.auto_grante_locale)
                }
            )

        ret.append( { "label" : "Can Retry?", "value" : qual.retry_active})
        if ( qual.retry_active ):
            ret.append( { "label" : "Retry Period", "value" : qual.retry_delay })

        ret.append( { "label" : "Has Test?", "value" : qual.has_test } )
        if ( qual.has_test ):
            ret.extend([
                {"label" : "Test", "value" : qual.test },
                {"label" : "Answer", "value" : qual.answer },
                {"label" : "Test Duration", "value" : qual.test_duration},
                ])

        ret.append( {"label" : "Deleted?", "value" : qual.dispose } )

        return(ret)

    def get(self, request, qual_id):
        requester = self.get_requester(request)
        qual_id = int(qual_id)
        qual = get_object_or_404(Qualification, pk = qual_id)

        qual_info = self.prepare_qual_info(qual)

        cxt = {
            "active": "quals",
            "requester": requester,
            "qual" : qual,
            "qual_info" : qual_info
        }
        return( render(request, "requester/qual_info.html", cxt) )

class RequesterQualRemove(LoginRequiredMixin, MTurkBaseView):
    """
    Allow a requester to remove a qualification that they have
    created
    """

    def get(self, request, qual_id):
        # @todo - we may want to add a means of
        #   using the ListViewForm in the GET request so that
        #   when we redirect, the user sees the appropriate page
        #   in the qualifications list.

        requester = self.get_requester(request)
        qual_id = int(qual_id)
        qual = get_object_or_404(Qualification, pk = qual_id)

        if ( qual.requester != requester ):
            raise PermissionDenied()

        qual.dispose = True
        qual.save()

        return( redirect("requester-quals"))

class RequesterTasksPage(LoginRequiredMixin, MTurkBaseView):
    """
    """

    def get(self, request):

        requester = self.get_requester(request)

        offset, count = self.get_list_form(request)

        tasks = Task.objects.filter(
            requester = requester,
            dispose = False
            ).order_by("-created")

        tasksPage = self.create_page(offset, count, tasks)

        cxt = {
            "active": "tasks",
            "requester": requester,
            "tasks" : tasksPage,
        }
        return( render(request, "requester/tasks.html", cxt) )

class RequesterWorkersPage(LoginRequiredMixin, MTurkBaseView):
    """
    """

    def get(self, request):

        requester = self.get_requester(request)



        workerIdList = Assignment.objects.filter(
            task__requester = requester
            ).values("worker__pk").distinct()

        cxt = {
            "active": "workers",
            "requester": requester,
            "workers" : {
                "offset" : 1,
                "total" : 1,
                "list": [
                ]
            },
        }
        return( render(request, "requester/workers.html", cxt) )




class RequesterSettingsPage(LoginRequiredMixin, View):
    """
    """

    def get(self, request):
        requester = get_object_or_404(
            Requester,
            user = request.user
            )

        credList = Credential.objects.filter(
            requester = requester,
            active = True
            )

        cxt = {
            "active": "settings",
            "requester": requester,
            "access_list" : credList,
        }
        return(render(
            request, "requester/settings.html", cxt
        ))


class RequesterCreateCredential(LoginRequiredMixin, View):
    """
    """
    def get(self, request):

        requester = get_object_or_404(Requester, user=request.user)

        aLen = 20
        sLen = 24
        accessKey = ''.join(
            [random.choice(string.ascii_uppercase + string.digits) for x in range(0,aLen)]
        )
        secretKey = ''.join(
            [random.choice(string.ascii_uppercase + string.digits) for x in range(0,aLen)]
        )

        cred = Credential.objects.create(
            requester = requester,
            access_key = accessKey,
            secret_key = secretKey
            )
        cred.save()

        return( redirect("requester-settings") )

class RequesterRemoveCredential(LoginRequiredMixin, View):
    """
    Remove a credential from the requester - note that
    we don't actually delete it, we just mark it not active.
    """

    def get(self, request, cred_id):

        requester = get_object_or_404(Requester, user=request.user)

        cred_id = int(cred_id)
        cred = get_object_or_404(
            Credential,
            requester = requester,
            pk = cred_id
        )

        cred.active = False
        cred.save()

        return( redirect("requester-settings") )
