
from django.conf import settings
from django.shortcuts import render, redirect
from django.core.exceptions import MultipleObjectsReturned, PermissionDenied, SuspiciousOperation
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages

from mturk.loader import Loader
#try:
from mturk.handlers import MTurkHandlers
#except:
#    pass

from mturk.models import *
from mturk.forms import UserSignupForm

import re
import json
import uuid
import traceback
from botocore.model import ServiceModel
from botocore.validate import validate_parameters
import logging
logger = logging.getLogger("mturk")

EXPECT_CONTENT_TYPE = "application/x-amz-json-1.1"

class MTurkMockAPI(View):

    def __init__(self, **kwargs):
        """
        """
        super().__init__(**kwargs)

        # Load the mturk services model here.
        serviceFile = None
        try:
            serviceFile = settings.MTURK_SERVICE_FILE
        except:
            serviceFile = Loader.find_mturk_service_file()

        self._serviceDef = Loader.load_service_defs(serviceFile)
        self._targetPrefix = self._serviceDef["metadata"]["targetPrefix"]
        self._model = ServiceModel( self._serviceDef, "mturk" )

        self._handlers = MTurkHandlers()


    def get_target(self, request):
        targetRaw = request.META["HTTP_X_AMZ_TARGET"]
        content = targetRaw.split(".")
        return( content[0], content[1] )

    def parseAuthHeader(self, authHeader):
        comps = filter( lambda x: len(x)>0, re.split(r"[ ,]", authHeader))
        # Some of the components are key value pairs, others arent
        params = {}
        for comp in comps:
            m = re.match(r"([^=]+)=([^,=])", comp)
            if m:
                key = m.group(1)
                val = m.group(2)
                params[key] = val
            else:
                m = re.match(r"([^-]+)-([^-]+)-([^, ]+)", comp)
                if m:
                    params["ALGO"] = comp

        return(params)

    def parseCredentials(self, cred):
        comps = filter(lambda x: len(x) > 0, re.split(r"[/]", cred))
        if ( len(comps) < 3 ):
            raise Exception("Credential Parameter Is missing Components")

        access_key = comps[0]
        access_date = comps[1]
        region = comps[2]
        return( access_key, access_date, region )

    def get_requester(self, request):
        authHeader = request.META["HTTP_AUTHORIZATION"]
        params = self.parseAuthHeader(authHeader)

        credStr = params["Credential"]
        access_key,_,_ = self.parseCredentials(credStr)

        try:
            cred = Credential.objects.get( access_key = access_key )
            # @todo - we are going to use the credential but
            #    right now I'm not going to verify the signing.
            #    it isn't particularly necessary for what I'm trying to
            #    accomplish with the mock right now.

            return(cred.requester)
        except Credential.DoesNotExist:
            raise PermissionDenied()
        except MultipleObjectsReturned:
            raise SuspiciousOperation("Multiple Credentials with Access Key: %s" % access_key)

    def get(self, request):
        """
        Redirect to the index page for the web application
        """
        return(
            render(request, "index.html", context={})
        )

    def post(self, request):
        """
        POST to this endpoint is processed as an API method
        """

        requester = self.get_requester(request)
        if ( not requester.active ):
            raise PermissionDenied()

        # First let's pull out some of the HTTP header data
        # that we need to process the request.
        prefix,target = self.get_target(request)
        if ( prefix != self._targetPrefix ):
            raise Exception(
                "Invalid Service Prefix: received='%s', expected='%s'" %
                (prefix, self._targetPrefix)
            )
        amzDate = request.META["HTTP_X_AMZ_DATE"]
        contentType = request.META["CONTENT_TYPE"]
        if ( contentType != EXPECT_CONTENT_TYPE ):
            raise Exception(
                "Invalid Content Type: received='%s', expected='%s'" %
                (contentType, EXPECT_CONTENT_TYPE)
            )

        if ( target not in self._model.operation_names ):
            raise Exception(
                "Invalid Target Method: Unknown Target '%s'" % target
            )

        # Get the request body and decode it
        body = str(request.body, "utf-8")
        reqParams = json.loads(body)

        # Check the inputs into the method
        opModel = self._model.operation_model(target)
        inShape = opModel.input_shape

        validate_parameters(reqParams, inShape)

        # Insert the requester object into the
        #  params that we will pass to the handler method.
        reqParams["EmuRequester"] = requester

        method = getattr(self._handlers, target)
        respParams = method(**reqParams)

        outShape = opModel.output_shape
        validate_parameters(respParams, outShape)

        resp = JsonResponse(respParams)
        resp["x-amzn-requestid"] = uuid.uuid1()
        resp["content-type"] = EXPECT_CONTENT_TYPE
        return(resp)


class MTurkCreateUser(View):
    """
    Create a new MTurk Emulator User with a requester
    and worker object.
    """

    def get(self, request):

        signupForm = UserSignupForm()
        return( render(request, "signup.html", {"form": signupForm}) )

    def post(self, request):

        signupForm = UserSignupForm(request.POST)

        if ( signupForm.is_valid() ):
            username = signupForm.cleaned_data["username"]
            password = signupForm.cleaned_data["password"]
            email = signupForm.cleaned_data.get("email", None)

            userCreate = {
                "username" : username,
                "password" : password,
            }
            if (email is not None ):
                userCreate["email"] = email

            user = None
            try:
                user = User.objects.create_user(**userCreate)
            except Exception as exc:

                msg = "Failed to Create New User: %s" % str(exc)

                signupForm.add_error(None, msg)

                logger.error(msg)
                logger.error("Traceback: %s" % traceback.format_exc())

                return(render(request, "signup.html", {"form": signupForm}))

            messages.info(
                request,
                "Successfully Created New User: %s" % username
            )

            return(redirect("index"))

        else:
            return(render(request, "signup.html", {"form": signupForm}))
