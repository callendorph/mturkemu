# File: CreateMTurkViews.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the implementation of a script to
# generate the views for the MTurk server API as a set of
# stubs. The idea is to parse the service definition file
# from botocore.
#

from django.core.management.base import BaseCommand, CommandError

from mturk.loader import Loader

import json
import sys
import os
import os.path
import logging

logger = logging.getLogger("commission")

fileHeader ="""# File: MTurkHandlers.py
# Author: Skeleton Autogenerated by CreateMTurkViews.py script
#
# Description:
#    This file contains the skeleton of all methods that need to be
# implemented for the MTurk mock.
#
#

class MTurkHandlers(object):
    def __init__(self):
        pass

    #######################
    # API Methods
    #######################

"""

methodTemplate = """    def %s(self, **kwargs):
        pass

"""

class Command(BaseCommand):
    """
    Create MTurk API Views
    """

    help="""
    Create the MTurk API views for emulating the MTurk service
    via this mockup.
    """

    def add_arguments(self, parser):
        group = parser.add_argument_group("Create MTurk Args")

        group.add_argument(
            "-o", "--out-file", dest="outfile", default="MTurkHandlers.py",type=str,
            help="Output the views to this file. Default is to create a file $(default)s in the local directory."
            )

        group.add_argument(
            "-i", "--input-file", dest="infile",
            default="", type=str,
            help="Use this as the input file for defining the API. By default, this command will search the site-packages for the botocore package and load the mturk service definition file from that package."
            )


    def handle(self, *args, **options):

        if ( len(options["infile"]) > 0 ):
            serviceFile = options["infile"]
        else:
            serviceFile = Loader.find_mturk_service_file()

        serviceDef = Loader.load_service_defs(serviceFile)

        version = serviceDef["version"]
        metadata = serviceDef["metadata"]
        operations = serviceDef["operations"]
        shapes = serviceDef["shapes"]

        try:
            with open(options["outfile"], "w") as f:
                f.write(fileHeader)

                for op in operations.keys():
                    f.write(methodTemplate % op)
        except KeyboardInterrupt:
            logger.info("User Interrupt")
            exit(1)

        logger.info("Handler Skeleton Generated")
