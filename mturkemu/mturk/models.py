# File: mturk/models.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the models for the MTurk Emulator.
#

from django.db import models
from django.core.validators import validate_comma_separated_integer_list
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from mturk.fields import *

from datetime import timedelta


@receiver(post_save, dispatch_uid="aws_id_creation")
def create_aws_id(sender, instance, **kwargs):
    """
    Create the AWS ID for objects that have this field
    This method is called post object save, and will
    cause a second save operation only on creation.
    @note - I think there may be a nicer way to do this with
       a model manager that applies to all objects of a particular
       abstract base type including the AWS ID - but for now
       this works even if it has a slight performance penalty.
    """
    # Applies only to objects with an
    # AWS Id parameter
    try:
        aws_id = instance.aws_id
    except:
        return

    if ( len(aws_id) == 0 ):
        instance.aws_id = CustomerIdField.generate_id(instance)
        instance.save()

class Worker(models.Model):
    """
    Workers implement the tasks created by Requesters
    """
    aws_id = CustomerIdField()
    active = models.BooleanField(default=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now=False, auto_now_add = True)

    def __str__(self):
        return("<%s, %s...>" % (self.user.username, self.aws_id[0:5]))

class Requester(models.Model):
    """
    Requesters create tasks that are implemented by Workers
    """
    aws_id = CustomerIdField()
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    MAX_NAME_LEN = 256
    name = models.CharField(max_length = MAX_NAME_LEN, blank=True)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now=False, auto_now_add = True)
    balance = models.DecimalField(max_digits=8, decimal_places=2)

    def get_balance(self):
        return("%.02f" % self.balance)

    def __str__(self):
        return("<%s, %s...>" % (self.user.username, self.aws_id[0:5]))

class Credential(models.Model):
    """
    Credentials for a requester to make API requests to the
    server.
    """
    requester = models.ForeignKey(Requester, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)

    MAX_ACCESS_KEY_LEN = 32
    access_key = models.CharField(max_length=MAX_ACCESS_KEY_LEN)

    MAX_SECRET_KEY_LEN = 64
    secret_key = models.CharField(max_length=MAX_SECRET_KEY_LEN)


class KeywordTag(models.Model):
    """
    Keywords are used to provide easily searchable terms describing
    a qualification or task.
    """
    MAX_VALUE_LEN = 128
    value = models.CharField(max_length=MAX_VALUE_LEN)

    def __str__(self):
        return("<tag=%s>" % self.value)

class KeywordMixinModel(models.Model):
    """
    Abstract base for Models that have a set of keywords
    associated with them.
    """
    class Meta:
        abstract = True

    keywords = models.ManyToManyField(KeywordTag, blank=True)

    def serialize_keywords(self):
        # Convert to a comma separate string of keywords.
        kws = list(self.keywords.all())
        return(",".join(kws))

class SystemQualType(object):
    ######################
    # System Qualification ID Definitions
    ######################
    # Certain Qualifications are defined by the MTurk system
    # and are manages independently from the requesters
    SANDBOX_MASTER = "2ARFPLSP75KLA8M8DH1HTEQVJT3SY6"
    PROD_MASTER = "2F1QJWKUDD8XADTFD2Q0G6UTO95ALH"

    NUM_HITS_APPROVED = "00000000000000000040"
    LOCALE = "00000000000000000071"
    ADULT = "00000000000000000060"

    # @todo - CHECK these system qualification IDs
    #    because they may not be correct
    PERC_APPROVE_RATE = "000000000000000000L0"
    PERC_SUBMIT_RATE = "000000000000000000L1"
    PERC_RETURN_RATE = "000000000000000000L2"
    PERC_REJECT_RATE = "000000000000000000L3"
    PERC_ABANDON_RATE = "000000000000000000L4"
    ######################

class Locale(models.Model):
    """
    Utility class - Strings are ISO 3166 country codes.
    """
    MAX_COUNTRY_LEN = 16
    country = models.CharField(max_length=MAX_COUNTRY_LEN)
    MAX_SUBDIV_LEN = 16
    subdivision = models.CharField(max_length = MAX_SUBDIV_LEN)

    def serialize(self):
        return({
            "Country" : self.country,
            "Subdivision" : self.subdivision
            })

    def __str__(self):
        return("<%s,%s>" % (self.country, self.subdivision))

class Qualification(KeywordMixinModel):
    """
    Qualifications are used to restrict which workers can work
    on what tasks.
    """

    aws_id = CustomerIdField()
    requester = models.ForeignKey(Requester, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now=False, auto_now_add = True)

    MAX_NAME_LEN = 256
    name = models.CharField(max_length=MAX_NAME_LEN)
    description=models.TextField()

    active = models.BooleanField(default=True)

    auto_grant = models.BooleanField(default=False)
    auto_grant_value = models.IntegerField(default=1)
    auto_grant_locale = models.ForeignKey(Locale, on_delete=models.PROTECT, null=True)

    requestable = models.BooleanField(default=True)

    retry_active = models.BooleanField(default=False)
    retry_delay = models.DurationField(null=True)

    # We store the text QuestionForm and answer answerKey objects
    # in string format so that they can be read and parsed later when
    # they are needed.
    test = models.TextField(blank=True)
    answer = models.TextField(blank=True)
    test_duration = models.DurationField(null=True)

    # Dispose is a flag indicating that this object needs to
    # be deleted when there are no more outstanding HITs that
    # rely on this qualification.
    dispose = models.BooleanField(default=False)

    @property
    def has_test(self):
        return( len(self.test) > 0 )

    @property
    def total_grants(self):
        ret = QualificationGrant.objects.filter(
            qualification = self,
            active = True
            ).count()
        return(ret)

    def serialize(self):
        ret = {
            "QualificationTypeId" : self.aws_id,
            "CreationTime" : self.created,
            "Name" : self.name,
            "Description" : self.description,
            "Keywords" : self.serialize_keywords(),
            "QualificationTypeStatus" : "Active" if self.active else "Inactive",
            "IsRequestable" : self.requestable,
            "AutoGranted" : self.auto_grant,
        }
        if ( len(self.test) > 0):
            ret["Test"] = self.test.serialize()
            ret["TestDurationInSeconds"] = self.test_duration.total_seconds()
        if ( len(self.answer) > 0):
            ret["AnswerKey"] = self.answer

        if ( self.auto_grant ):
            ret["AutoGrantedValue"] = self.auto_grant_value
        if ( self.retry_active ):
            ret["RetryDelayInSeconds"] = self.retry_delay.total_seconds()

        return(ret)

    def __str__(self):
        return("<%s...>" % self.aws_id[0:6])

class QualificationRequest(models.Model):
    """
    Qualification Requests are created when a worker makes a
    request to receive a particular qualification.
    """
    aws_id = CustomerIdField()
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    qualification = models.ForeignKey(Qualification, on_delete=models.CASCADE)

    last_request = models.DateTimeField()
    rejected = models.BooleanField(default=False)
    MAX_REASON_LEN = 256
    reason = models.CharField(max_length=MAX_REASON_LEN, blank=True)

    def __str__(self):
        return("<%s...>" % self.aws_id[0:6])

class QualificationGrant(models.Model):
    """
    """
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    qualification = models.ForeignKey(Qualification, on_delete=models.CASCADE)

    granted = models.DateTimeField(auto_now=False, auto_now_add = True)
    value = models.IntegerField(default=0)
    # Locale is optional for certain types of qualifications
    locale = models.ForeignKey(Locale, on_delete=models.PROTECT, null=True)

    active = models.BooleanField(default=True)

    MAX_REASON_LEN = 256
    reason = models.CharField(max_length = MAX_REASON_LEN, blank=True)

    @property
    def task_count(self):
        """
        Determine the number of tasks that are dependent on this
        qualification.
        """
        return(0)

    def serialize(self):
        ret = {
            "WorkerId" : self.worker.aws_id,
            "QualificationTypeId" : self.qualification.aws_id,
            "GrantTime" : self.granted,
            "Status" : "Granted" if self.active else "Revoked"
        }
        if ( self.locale is None ):
            ret["IntegerValue"] = self.value
        else:
            ret["LocaleValue"] = self.locale.serialize()
        return(ret)

    def __str__(self):
        return("<worker=%s,qual=%s>" % (self.worker, self.qualification))

class QualificationRequirement(models.Model):
    """
    Qualification Requirements are used to control the constraints
    on workers that can access the tasks. They are defined in
    HITTypes and HITs.
    """
    qualification = models.ForeignKey(Qualification, on_delete=models.CASCADE)
    comparator = QualComparatorField()

    int_values = models.CharField(
        max_length=256,
        validators=[validate_comma_separated_integer_list],
        blank=True
    )
    locale_values = models.ManyToManyField(Locale, blank=True)

    required_to_preview = models.BooleanField(default=False)

class TaskType(KeywordMixinModel):
    """
    TaskTypes make it easier to create a particular Task with common
    features. When creating a hit directly, a new TaskType is created
    """
    aws_id = CustomerIdField()

    requester = models.ForeignKey(Requester, on_delete=models.CASCADE)

    auto_approve = models.DurationField(default=timedelta(seconds=0), null=True)
    assignment_duration = models.DurationField()
    reward = models.DecimalField(max_digits=8, decimal_places=2)
    MAX_TITLE_LEN = 256
    title=models.CharField(max_length = MAX_TITLE_LEN)
    description=models.TextField()
    qualifications = models.ManyToManyField(QualificationRequirement, blank=True)

    def __str__(self):
        return("<%s...>" % self.aws_id[0:6])

class Task(models.Model):
    """
    Task is a sequence of steps completed by one or more workers.
    """
    aws_id = CustomerIdField()
    requester = models.ForeignKey(Requester, on_delete=models.CASCADE)

    tasktype = models.ForeignKey(TaskType, on_delete=models.CASCADE)
    status = TaskStatusField()

    max_assignments = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now=False, auto_now_add = True)
    expires = models.DateTimeField(null=True)

    MAX_ANNOTATION_LEN = 256
    annotation = models.CharField(max_length=MAX_ANNOTATION_LEN)

    # Unique Token is used to reduce the likelihood of creating
    # duplicate Tasks. Note that in MTurk this unique token expires
    # after 24 hours but currently, we are just keeping them
    MAX_UNIQUE_LEN = 64
    unique=models.CharField(max_length=MAX_UNIQUE_LEN, blank=True)

    # Note: question is an XML string field containing the
    #   content that will be presented to the worker. This XML is
    #   validated before creation, but it is not parsed or acted
    #   upon until shown to the worker.
    question = models.TextField()

    reviewstatus = TaskReviewStatusField()

    # @todo - assignment policy
    # @todo - hit policy
    # @todo - HITLayoutId handling.

    # For Delete Operation
    dispose = models.BooleanField(default=False)

    def is_reviewable(self):
        return( self.state == TaskStatusField.REVIEWABLE )

    def is_reviewing(self):
        return( self.state == TaskStatusField.REVIEWING )

    def serialize_qualifications(self):
        ret = []
        return(ret)

    @property
    def completed_assignment_count(self):

        q = (
            Q(status = AssignmentStatusField.APPROVED) |
            Q(status = AssignmentStatusField.REJECTED)
        )
        return(self.assignment_set.filter(q).count())

    @property
    def pending_assignment_count(self):
        q = Q(status = AssignmentStatusField.SUBMITTED)
        return( self.assignment_set.filter(q).count())

    def compute_assignment_stats(self):
        completed = self.completed_assignment_count
        pending = self.pending_assignment_count
        available = self.max_assignments - (completed + pending)
        if ( available < 0 ):
            available = 0

        return(available, pending, completed)

    def serialize_assignment_stats(self):

        available, pending, completed = self.compute_assignment_stats()

        ret = {
            "NumberOfAssignmentsPending" : pending,
            "NumberOfAssignmentsAvailable" : available,
            "NumberOfAssignmentsCompleted" : completed,
        }
        return(ret)


    def serialize(self, includeAnnotiation=False):
        ret = {
            "HITId" : self.aws_id,
            "HITTypeId" : self.tasktype.aws_id,
            "HITGroupId" : "",
            "HITLayoutId" : "",
            "CreationTime" : self.created,
            "Title" : self.tasktype.title,
            "Description" : self.tasktype.description,
            "Reward" : "%.02f" % self.tasktype.reward,
            "AutoApprovalDelayInSeconds" : self.tasktype.auto_approve.total_seconds(),
            "AssignmentDurationInSeconds" : self.tasktype.assignment_duration.total_seconds(),
            "Expiration" : self.expires,
            "Keywords" : self.serialize_keywords(),
            "HITStatus" : self.get_status_display(),
            "MaxAssignments" : self.max_assignments,
            "QualificationRequirements" : self.serialize_qualifications(),
            "HITReviewStatus" : self.get_reviewstatus_display(),
        }
        if ( len(self.question) > 0 ):
            ret["Question"] = self.question
        if ( includeAnnotation and len(self.annotation) > 0 ):
            ret["RequesterAnnotation"] = self.annotation

        # @todo - HITLayout needs to be managed here.
        stats = self.serialize_assignment_stats()
        ret.update(stats)

        return(ret)

    def __str__(self):
        return("<%s...>" % self.aws_id[0:6])

class Assignment(models.Model):
    """
    Assignments are completed instances of a task by a particular worker
    """
    aws_id = CustomerIdField()
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT)

    status = AssignmentStatusField()

    # @todo - we need to think carefully about this when we
    #   implement the assignment creation.
    auto_approve = models.DateTimeField(null=True)
    accepted = models.DateTimeField(null=True)
    submitted = models.DateTimeField(null=True)
    approved=models.DateTimeField(null=True)
    rejected=models.DateTimeField(null=True)
    deadline=models.DateTimeField(null=True)

    # Need to  figure out how to store the answers to a
    # assignment
    MAX_FEEDBACK_LEN = 512
    feedback = models.CharField(max_length = MAX_FEEDBACK_LEN)

    def is_accepted(self):
        return( self.status == AssignmentStatusField.ACCEPTED )

    def is_submitted(self):
        return( self.status == AssignmentStatusField.SUBMITTED )

    def is_approved(self):
        return( self.status == AssignmentStatusField.APPROVED )

    def is_rejected(self):
        return( self.status == AssignmentStatusField.REJECTED )

    def is_decided(self):
        return( self.is_approved() or self.is_rejected() )

    def serialize(self):
        ret = {
            "AssignmentId" : self.aws_id,
            "WorkerId" : self.worker.aws_id,
            "HITId" : self.task.aws_id,
            "AcceptTime" : self.accepted,
            "Deadline" : self.deadline,
        }

        if ( not self.is_accepted() ):
            ret["AssignmentStatus"] = self.get_status_display()

        if ( self.is_submitted() ):
            ret["AutoApprovalTime"] = self.auto_approve
            ret["SubmitTime"] = self.submitted
            # @todo - figure this out.
            #ret["Answer"] = self.answer.serialize()

        if ( self.is_approved() ):
            ret["ApprovalTime"] = self.approved

        if ( self.is_rejected() ):
            ret["RejectionTime"] = self.rejected

        if ( self.is_decided() ):
            ret["RequesterFeedback"] = self.feedback

        return(ret)

    def __str__(self):
        return("<%s...,STAT=%s" % (self.aws_id[0:6], self.status))

class BonusPayment(models.Model):
    """
    State for a payment made to a worker as a bonus for completing a
    task.
    """
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    MAX_REASON_LEN=256
    reason=models.CharField(max_length=MAX_REASON_LEN,blank=True)
    created=models.DateTimeField(auto_now=False, auto_now_add = True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    MAX_UNIQUE_LEN=64
    unique = models.CharField(max_length = MAX_UNIQUE_LEN, blank=True)

    def serialize(self):
        ret = {
            "WorkerId": self.worker.awd_id,
            "BonusAmount" : "%.02f" % self.amount,
            "AssignmentId" : self.assignment.aws_id,
            "GrantTime" : self.created
        }
        if ( len(self.reason) > 0 ):
            ret["Reason"] = self.reason
        return(ret)

class WorkerBlock(models.Model):
    """
    Create a block so that a worker can't work on tasks associated
    with a particular requester account
    """

    worker=models.ForeignKey(Worker, on_delete=models.CASCADE)
    requester = models.ForeignKey(Requester, on_delete=models.CASCADE)

    active = models.BooleanField(default=False)
    MAX_REASON_LEN = 256
    reason = models.CharField(max_length=MAX_REASON_LEN)

    def serialize(self):
        return({
            "WorkerId": self.worker.aws_id,
            "Reason" : self.reason
        })

from mturk.user import *
