# File: mturk/urls.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the implementation of the urls
# for the worker and requester areas of the site.
#
from django.conf.urls import url

from mturk.workers import *
from mturk.qualview import *

workerPatterns = [
    url('^home/$', WorkerHomePage.as_view(), name="worker-home"),
    url('^quals/$', WorkerQualsPage.as_view(), name="worker-quals"),
    url('^quals/(?P<qual_id>[0-9]+)/$', WorkerQualInfoPage.as_view(), name="worker-qual-info"),
    url('^quals/(?P<qual_id>[0-9]+)/request/$', WorkerRequestQual.as_view(), name="worker-qual-request"),
    url('^quals/reqs/$', WorkerQualRequestsPage.as_view()),
    url('^quals/reqs/(?P<req_id>[0-9]+)/test/$', WorkerCompleteQualTest.as_view(), name="worker-qual-test"),
    url('^quals/grants/$', WorkerQualGrantsPage.as_view()),
    url('^tasks/$', WorkerTasksPage.as_view(), name="worker-tasks"),
    url('^settings/$', WorkerSettingsPage.as_view(), name="worker-settings"),
]

from mturk.requesters import *

requesterPatterns = [
    url('^home/$', RequesterHomePage.as_view(), name="requester-home"),
    url('^quals/$', RequesterQualsPage.as_view(), name="requester-quals"),
    url('^quals/reqs/$', RequesterQualRequestsPage.as_view(), name="requester-qual-requests"),
    url('^quals/reqs/(?P<req_id>[0-9]+)/approve/$', RequesterQualRequestApprove.as_view(), name="requester-qual-request-approve"),
    url('^quals/reqs/(?P<req_id>[0-9]+)/reject/$', RequesterQualRequestReject.as_view(), name="requester-qual-request-reject"),

    url('^quals/grants/$', RequesterQualGrantsPage.as_view(), name="requester-qual-grants"),

    url('^quals/create/$', RequesterQualsCreate.as_view(), name="requester-qual-create"),
    url('^quals/(?P<qual_id>[0-9]+)/$', RequesterQualInfo.as_view()),
    url('^quals/(?P<qual_id>[0-9]+)/remove/$', RequesterQualRemove.as_view()),

    url('^tasks/$', RequesterTasksPage.as_view()),
    url('^workers/$', RequesterWorkersPage.as_view()),
    url('^settings/$', RequesterSettingsPage.as_view(), name="requester-settings"),


    # Access Token methods
    url('^access/create/$', RequesterCreateCredential.as_view()),
    url('^access/(?P<cred_id>[0-9]+)/remove/$', RequesterRemoveCredential.as_view()),

]
