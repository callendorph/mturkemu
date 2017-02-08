# File: mturk/loader.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the implementation of a loader for
# importing the botocore service model for mturk.
#

import sys
import os
import os.path
import json

DEFAULT_SERVICE_JSON="botocore/data/mturk/2017-01-17/service-2.json"

class Loader(object):

    @staticmethod
    def find_mturk_service_file():
        """
        Search the current python path for the
        botocore module and extract the mturk service file
        """
        for path in sys.path:
            if ( len(path) == 0 ):
                continue
            try:
                subdirs = os.listdir(path)
                for subdir in subdirs:
                    if ( "botocore" in subdir ):
                        ret = os.path.join(path, DEFAULT_SERVICE_JSON)
                        return(ret)
            except Exception as exc:
                pass
        return(None)

    @staticmethod
    def load_service_defs(service_file):
        """
        @returns dict object containing the service schema model
        """
        with open(service_file, "r") as f:
            content = f.read()
            service = json.loads(content)
            # Check for a valide service model
            # We expect at least a "operations" and "shapes"
            expKeySet = set(["operations", "shapes", "metadata", "version"])
            obsKeySet = set(service.keys())
            remainder = expKeySet - obsKeySet
            if ( len(remainder) > 0 ):
                raise Exception("Malformed Service File: Could not find keys: %s" % str(remainder))
            return(service)
