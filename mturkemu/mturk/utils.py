# File: mturk/utils.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the implementation of some utilties for
# the mturk code base.

from django.views import View
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from mturk.models import *
from mturk.forms import *

class MTurkBaseView(View):
    """
    Base View Class - contains some utility method for working
    with views in the mturk app
    """

    def get_worker(self, request):
        return( get_object_or_404(Worker, user = request.user ))

    def get_requester(self, request):
        return( get_object_or_404(Requester, user = request.user ) )

    def create_page(self, offset, count, allData):
        pmaker = Paginator(allData, count)
        try:
            respList = pmaker.page(offset)
        except PageNotAnInteger:
            offset = 1
            respList = pmaker.page(offset)
        except EmptyPage:
            offset = pmaker.num_pages
            respList = pmaker.page(offset)

        return({
            "offset" : offset,
            "total" : pmaker.num_pages,
            "list" : respList
        })

    def get_list_form(self, request):
        DEF_OFFSET = 1
        DEF_COUNT = 10
        form = ListViewForm(request.GET)
        if ( not form.is_valid() ):
            offset = DEF_OFFSET
            count = DEF_COUNT
        else:
            offset = form.cleaned_data.get("offset")
            if ( offset is None ):
                offset = DEF_OFFSET
            count = form.cleaned_data.get("count")
            if ( count is None ):
                count = DEF_COUNT

        return( offset, count )

    def get_query_form(self, request):
        form = QueryForm(request.GET)
        if ( not form.is_valid() ):
            query = form.cleaned_data.get("query")
            return(query)
        else:
            return(None)
