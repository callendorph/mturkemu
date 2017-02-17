# File: mturk/errors.py
# Author: Carl Allendorph
#

class RequestError(Exception):
    """
    MTurk API Standard error type from service defintion
    """
    def __init__(self, message, code):
        self.msg = message
        self.code = code

    def serialize(self):
        return({
            "Message" : self.msg,
            "TurkErrorCode" : "%d" % self.code,
        })
