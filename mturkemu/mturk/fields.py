# File: mturk/fields.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the implementation of some custom fields
# for the mturk app's models
#

from django.db import models

import hashlib
import base64

class RemoveKeysMixin(object):
    def removeKeys(self, kwargs):
        for key in ["default", "choices", "max_length"]:
            try:
                kwargs.pop(key)
            except:
                pass

class CustomerIdField(models.CharField, RemoveKeysMixin):
    """
    AWS uses 32 character strings as the ID for
    objects in the database. This field will auto generate
    this value when the associated model is added to its
    table.
    @note CustomerId is the nomenclature used by AWS in
    their documentation.
    """
    def __init__(self, *args, **kwargs):
        self.removeKeys(kwargs)
        #super().__init__(max_length=64, unique=True, blank=True)
        super().__init__(max_length=64, blank=True)

    @staticmethod
    def generate_id(model_instance):
        h = hashlib.md5()
        content = bytearray(
            "%s.%d" % (model_instance._meta.model_name, model_instance.id),
            "utf-8"
            )
        h.update(content)
        dig= h.digest()
        value = base64.b32encode(dig).decode("utf-8")
        value = value.split("=", maxsplit=1)[0]
        value = "A" + value
        return(value)


class TaskStatusField(models.CharField, RemoveKeysMixin):
    """
    Task status
    """

    ASSIGNABLE="A"
    UNASSIGNABLE="U"
    REVIEWABLE="R"
    REVIEWING="G"
    DISPOSED="D"

    STATES = (
        (ASSIGNABLE, "Assignable"),
        (UNASSIGNABLE, "Unassignable"),
        (REVIEWABLE, "Reviewable"),
        (REVIEWING, "Reviewing"),
        (DISPOSED, "Disposed")
    )

    def __init__(self, *args, **kwargs):

        self.removeKeys(kwargs)

        super().__init__(
            max_length=1,
            choices = TaskStatusField.STATES,
            default=TaskStatusField.ASSIGNABLE
            )

class TaskReviewStatusField(models.CharField, RemoveKeysMixin):
    """
    Task under Review Status
    """

    NOT_REVIEWED = "N"
    MARKED_FOR_REVIEW = "M"
    REVIEWED_APPROPRIATE = "A"
    REVIEWED_INAPPROPRIATE = "I"

    STATES = (
        (NOT_REVIEWED, "NotReviewed"),
        (MARKED_FOR_REVIEW, "MarkedForReview"),
        (REVIEWED_APPROPRIATE, "ReviewedAppropriate"),
        (REVIEWED_INAPPROPRIATE, "ReviewedInappropriate"),
    )

    def __init__(self, *args, **kwargs):

        self.removeKeys(kwargs)
        super().__init__(
            max_length = 1,
            choices = TaskReviewStatusField.STATES,
            default = TaskReviewStatusField.NOT_REVIEWED
            )

class QualStatusField(models.CharField, RemoveKeysMixin):
    """
    Qualification State - This indicates the state of a
    qualification. This is primarily interesting for the
    "Disposing" state where the qualification isn't deleted
    until the all tasks utilizing this qual are deleted.
    """

    ACTIVE = "A"
    INACTIVE = "I"
    DISPOSING = "D"

    STATES = (
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
        (DISPOSING, "Disposing"),
    )

    def __init__(self, *args, **kwargs):
        self.removeKeys(kwargs)
        super().__init__(
            max_length = 1,
            choices = QualStatusField.STATES,
            default = QualStatusField.ACTIVE
            )


class QualReqStatusField(models.CharField, RemoveKeysMixin):
    """
    Qualification Request Status - This indicates the state of
    a request from a worker for a qualification.
    """
    IDLE = "I"
    PENDING = "P"
    APPROVED = "A"
    REJECTED = "R"

    STATES = (
        (IDLE, "Idle"),
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected")
    )

    def __init__(self, *args, **kwargs):
        self.removeKeys(kwargs)
        super().__init__(
            max_length = 1,
            choices = QualReqStatusField.STATES,
            default = QualReqStatusField.IDLE
            )

class AssignmentStatusField(models.CharField, RemoveKeysMixin):
    """
    Asignment Status Field
    """

    ACCEPTED = "C"
    SUBMITTED = "S"
    APPROVED = "A"
    REJECTED = "R"

    STATES = (
        (ACCEPTED, "Accepted"),
        (SUBMITTED, "Submitted"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    )

    def __init__(self, *args, **kwargs):
        self.removeKeys(kwargs)
        super().__init__(
            max_length = 1,
            choices = AssignmentStatusField.STATES,
            default = AssignmentStatusField.ACCEPTED
            )

class QualComparatorField(models.CharField, RemoveKeysMixin):
    """
    """
    LESS_THAN = "L"
    LESS_THAN_OR_EQUAL = "K"
    GREATER_THAN = "G"
    GREATER_THAN_OR_EQUAL = "H"
    EQUAL_TO = "E"
    NOT_EQUAL_TO = "N"
    EXISTS="S"
    DOES_NOT_EXIST="D"
    IN_SET="I"
    NOT_IN_SET="J"

    STATES = (
        (LESS_THAN, "LessThan"),
        (LESS_THAN_OR_EQUAL, "LessThanOrEqualTo"),
        (GREATER_THAN, "GreaterThan"),
        (GREATER_THAN_OR_EQUAL, "GreaterThanOrEqualTo"),
        (EQUAL_TO, "EqualTo"),
        (NOT_EQUAL_TO, "NotEqualTo"),
        (EXISTS, "Exists"),
        (DOES_NOT_EXIST, "DoesNotExist"),
        (IN_SET, "In"),
        (NOT_IN_SET, "NotIn"),
    )

    def __init__(self, *args, **kwargs):
        self.removeKeys(kwargs)
        super().__init__(
            max_length=1,
            choices = QualComparatorField.STATES
        )


    @staticmethod
    def convert_display_to_value(compStr):
        compId = [x[0] for x in QualComparatorField.STATES if x[1] == compStr]
        if ( len(compId) != 1 ):
            raise Exception("Invalid Comparator Display String Value: %s" % compStr)

        return( compId[0] )
