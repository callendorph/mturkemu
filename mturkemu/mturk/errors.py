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
            "TurkErrorCode" : self.code,
        })

ERROR_CODE_PREFIX = "AWS.MechanicalTurk"

class PermissionDenied(RequestError):
    def __init__(self):
        super().__init__(
            "Permission Denied",
            "%s.PermissionDenied" % ERROR_CODE_PREFIX
        )

class MissingArgumentError(RequestError):
    def __init__(self, arg):
        super().__init__(
            "Request is missing a required argument: %s" % arg,
            "%s.MissingArgument" % ERROR_CODE_PREFIX
        )

class ParameterValidationError(RequestError):
    def __init__(self, op, argName, val, minVal, maxVal):
        super().__init__(
            ("%s: Invalid Parameter '%s' with value %s. "
             "Valid values range from %s to %s") %
            (op, argName, str(val), str(minVal), str(maxVal)),
            "AWS.ParameterOutOfRange"
        )

class ValidationError(RequestError):
    """
    General Purpose error returned by mturk for checking input args -
    """
    def __init__(self, errors):
        errContent = ", ".join(errors)
        super().__init__(
            "Validation Error: %d errors: %s" % (len(errors), errContent),
            "%s.ValidationError" % ERROR_CODE_PREFIX
        )

class DuplicateRequestError(RequestError):
    """
    This exception is for the case when an object is created with
    a unique request token and is an actual duplicate.
    """
    def __init__(self):
        super().__init__(
            "Request containing a unique request token is a duplicate",
            "%s.DuplicateRequest" % ERROR_CODE_PREFIX
        )

class DoesNotExistError(RequestError):
    """
    When an object accessed by AWS ID does not exist.
    """
    def __init__(self, model, pk=""):
        super().__init__(
            "%s %s does not exist.",
            "%s.DoesNotExist" % ERROR_CODE_PREFIX
        )

class RequesterInsufficientFundsError(RequestError):
    def __init__(self):
        super().__init__(
            "Requester has insufficient funds in Account",
            "%s.InsufficientFunds" % ERROR_CODE_PREFIX
        )

class QuestionTooLongError(RequestError):
    def __init__(self):
        super().__init__(
            "Questions must be less than 65535 Bytes",
            "%s.QuestionTooLong" % ERROR_CODE_PREFIX
            )

class AnswerTooLongError(RequestError):
    def __init__(self):
        super().__init__(
            "Answer must be less than 65535 Bytes",
            "%s.AnswerTooLong" % ERROR_CODE_PREFIX
            )

# Qualification Errors
class QualificationTypeAlreadyExistsError(RequestError):
    def __init__(self):
        super().__init__(
            "You have already created a QualificationType with this name. A QualifcationType's name must be unique among all of the QualificationTypes created by the same user.",
            "%s.QualficationTypeAlreadyExists" % ERROR_CODE_PREFIX
            )

class QualTestInvalidError(RequestError):
    def __init__(self):
        super().__init__(
            "Qualification Test must be an XML object of type 'QuestionForm'",
            "%s.QualTestInvalid" % ERROR_CODE_PREFIX
            )

class QualAnswerInvalidError(RequestError):
    def __init__(self):
        super().__init__(
            "Qualification AnswerKey must be an XML object of type 'AnswerKey'",
            "%s.QualAnswerKeyInvalid" % ERROR_CODE_PREFIX
            )

class QualReqInvalidStateError(RequestError):
    def __init__(self):
        super().__init__(
            "Qualification Request Is in Invalid State for Operation",
            "%s.QualReqInvalidState" % ERROR_CODE_PREFIX
            )


# Assignment Errors

class AssignmentNotSubmittedError(RequestError):
    def __init__(self):
        super().__init__(
            "Request Attempts to access an Assignment that has not been submitted yet.",
            "%s.AssignmentNotSubmitted" % ERROR_CODE_PREFIX
        )

class AssignmentAlreadyApprovedError(RequestError):
    def __init__(self):
        super().__init__(
            "Request Attempts to reject an assignment that has already been approved which is not allowed.",
            "%s.AssignmentAlreadyApproved" % ERROR_CODE_PREFIX
        )

class AssignmentAlreadyRejectedError(RequestError):
    def __init__(self):
        super().__init__(
            "Request Attempts to approve an assignment that has already been rejected. Use the 'OverrideRejection' argument to allow.",
            "%s.AssignmentAlreadyRejected" % ERROR_CODE_PREFIX
        )

class AssignmentInvalidStateError(RequestError):
    def __init__(self, state):
        super().__init__(
            "Request Attempts to filter assignments using an invalid state: %s" % state,
            "%s.AssignmentInvalidStateFilter" % ERROR_CODE_PREFIX
        )

# Task Errors

class TaskInvalidAssignmentIncreaseError(RequestError):
    def __init__(self):
        super().__init__(
            "Request Attempts to increase the number of assignments in a task by an invalid amount.",
            "%s.InvalidMaximumAssignmentsIncrease" % ERROR_CODE_PREFIX
        )

class TaskQuestionInvalidError(RequestError):
    def __init__(self):
        super().__init__(
            "Task Question must be an XML object of type 'HTMLQuestion', 'ExternalQuestion', or 'QuestionForm'",
            "%s.QuestionInvalid" % ERROR_CODE_PREFIX
            )

class TaskNotDeletableError(RequestError):
    def __init__(self):
        super().__init__(
            "Task is not in a valid state to allow for deletion.",
            "%s.TaskNotDeletable" % ERROR_CODE_PREFIX
            )

class InvalidExpirationIncrementError(RequestError):
    def __init__(self, inc):
        super().__init__(
            "Invalid Expiration Increment %d - must be 60 to 31536000" % inc,
            "%s.InvalidExpirationIncrement" % ERROR_CODE_PREFIX
        )

################################
# Non-RequestError Exceptions
################################

# XML Processing Errors

class InvalidTagError(Exception):
    def __init__(self, tag):
        super().__init__("Invalid Tag: %s" % tag.localname)


class InvalidQuestionFormError(Exception):
    """
    """
    def __init__(self, form):
        super().__init__("Invalid Question Form Data - Fails Validation")
        self.form = form
