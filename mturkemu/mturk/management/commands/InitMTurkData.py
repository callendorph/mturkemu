# File: InitMTurkData.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the implementation of some code to
# do some data initialization at commissioning time.
#


from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User as db_User

from mturk.models import Worker as db_Worker, Requester as db_Requester, Qualification as db_Qualification, Locale as db_Locale
from mturk.models import SystemQualType

import time
import logging
logger = logging.getLogger("mturk")


def create_initial_data(User, Worker, Requester, Qualification, Locale):
    """
    General Purpose method for creating the initial mturk data.
    """

    # Create user called "MTurk" which is a superuser
    # This user will be used to reference system qualifications
    # and other commissioned structures

    try:
        mturk = User.objects.get(username = "mturk")
    except User.DoesNotExist:
        mturk = User.objects.create_user(
            username="mturk",
            password="mturk",
            first_name="MTurk",
            last_name="Emulator"
        )


    # MTurk System will not be allowed to be a worker
    worker = None
    while ( True ):
        try:
            worker = Worker.objects.get(user__username = "mturk")
            break
        except Worker.DoesNotExist:
            time.sleep(1)

    worker.active = False
    worker.save()

    # Find the MTurk Requester
    requester = Requester.objects.get(user = mturk)

    # Now Let's Create the System Qualification Types

    qualDefs = [
        {
            "name" : "HIT submission rate (%)",
            "description" : "This Qualification is generated automatically and reflects the percentage of HITs for which you have submitted answers divided by the total number of HITs you have accepted. Your score is a value between 0 and 100. A score of 100 indicates that you have submitted an answer for every HIT you have accepted.",
            "aws_id" : SystemQualType.PERC_SUBMIT_RATE,
            "default" : 0,
        },
        {
            "name" : "HIT abandonment rate (%)",
            "description" : "This Qualification is generated automatically and reflects the percentage of HITs which you have accepted but which have expired before you submitted an answer divided by the total number of HITs you have accepted. Your score is a value between 0 and 100. A score of 0 indicates that you have not allowed any HITs to expire before you have submitted an answer for them.",
            "aws_id" : SystemQualType.PERC_ABANDON_RATE,
            "default" : 0,
        },
        {
            "name" : "HIT approval rate (%)",
            "description" : "This Qualification is generated automatically and reflects the percentage of HITs for which you have submitted an answer that has been approved divided by the total number of HITs that have been approved or rejected. Your score is a value between 0 and 100. A score of 100 indicates that every HIT you have submitted has been approved.",
            "aws_id" : SystemQualType.PERC_APPROVE_RATE,
            "default" : 0,
        },
        {
            "name" : "HIT rejection rate (%)",
            "description" : "	This Qualification is generated automatically and reflects the percentage of HITs for which you have submitted an answer that has been rejected divided by the total number of HITs that have been approved or rejected. Your score is a value between 0 and 100. A score of 0 indicates that none of the HITs you have submitted has been rejected.",
            "aws_id" : SystemQualType.PERC_REJECT_RATE,
            "default" : 0,
        },
        {
            "name" : "HIT return rate (%)",
            "description" : "This Qualification is generated automatically and reflects the percentage of HITs which you have accepted and then returned unanswered divided by the total number of HITs you have accepted. Your score is a value between 0 and 100. A score of 0 indicates that you have not returned any HITs.",
            "aws_id" : SystemQualType.PERC_RETURN_RATE,
            "default" : 0,
        },
        {
            "name" : "Total approved HITs",
            "description" : "This Qualification is generated automatically and reflects the number of HITs which you have submitted an answer that has been approved. Your score is a value greater than or equal to 0.",
            "aws_id" : SystemQualType.NUM_HITS_APPROVED,
            "default" : 0,
        },
        {
            "name" : "Adult",
            "description" : "This Qualification is generated automatically and reflects that the worker is an adult 18 years of age or older and is willing to see adult content. Boolean value, where 1 = true, 0 = false.",
            "aws_id" : SystemQualType.ADULT,
            "default" : 0,
        },
        {
            "name" : "Sandbox Master",
            "description" : "The qualification indicates that the worker has achieved the rank of master. This is the ID for the sandbox environment only and will not work in the production environment.",
            "aws_id" : SystemQualType.SANDBOX_MASTER,
            "default" : 0,
        },
        {
            "name" : "Production Master",
            "description" : "The qualification indicates that the worker has achieved the rank of master. This is the ID for the production environment only and will not work in the sandbox environment.",
            "aws_id" : SystemQualType.PROD_MASTER,
            "default" : 0,
        }
    ]

    for qualDef in qualDefs:

        q = Qualification.objects.create(
            aws_id = qualDef["aws_id"],
            requester = requester,
            name = qualDef["name"],
            description = qualDef["description"],
            auto_grant = True,
            auto_grant_value = qualDef["default"],
            requestable = False,
            retry_active = False
        )
        logger.info("Created Qualification: %s" % q.name)

    # Special Case - Generate the Locale Qualification
    localeDef = {
        "name" : "Location",
        "description" : "The Location Qualification represents the location you specified with your mailing address. Some HITs may only be available to residents of particular countries, states, provinces or cities.",
        "aws_id" : SystemQualType.LOCALE,
        "default" : {
            "Country" : "US",
            "Subdivision" : "CA"
        },
    }

    locale = Locale.objects.create(
        country = localeDef["default"]["Country"],
        subdivision = localeDef["default"]["Subdivision"]
    )

    q = Qualification.objects.create(
        aws_id = localeDef["aws_id"],
        requester = requester,
        name = localeDef["name"],
        description = localeDef["description"],
        auto_grant = True,
        auto_grant_locale = locale,
        requestable = False,
        retry_active = False
    )

    logger.info("Created Qualification: %s" % q.name)


class Command(BaseCommand):
    """
    Initialize MTurk Commissioning Data
    """
    help="Initialize the MTurk Data for an Empty Database. NOTE: This command is automatically invoked during migration so if you followed the normal route, then calling this method manually should be unnecessary"

    def add_arguments(self, parser):
        # @todo - arguments ?
        pass

    def handle(self, *args, **options):

        models = {
            "User": db_User,
            "Worker": db_Worker,
            "Requester": db_Requester,
            "Qualification" : db_Qualification,
            "Locale" : db_Locale,
        }
        create_initial_data(**models)
