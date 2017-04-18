# File: mturk/models.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the models for the MTurk Emulator.
#

from django.db import models
from django.db.models import Q
from django.core.validators import validate_comma_separated_integer_list
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from mturk.fields import *
from mturk.xml.questions import *
from mturk.xml.quesformanswer import QFormAnswer

from datetime import timedelta
import random
import string

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

    # HIT Statistics

    returned_hits = models.IntegerField(default=0)

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

    @staticmethod
    def create_random_key(keylen):
        ret = ''.join([
            random.choice(string.ascii_uppercase + string.digits)
            for x in range(0,keylen)
        ])
        return(ret)

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
        kws = [x.value for x in self.keywords.all()]
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
            ret["Test"] = self.test
            ret["TestDurationInSeconds"] = int(self.test_duration.total_seconds())
        if ( len(self.answer) > 0):
            ret["AnswerKey"] = self.answer

        if ( self.auto_grant ):
            ret["AutoGrantedValue"] = self.auto_grant_value
        if ( self.retry_active ):
            ret["RetryDelayInSeconds"] = int(self.retry_delay.total_seconds())

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
    created = models.DateTimeField(auto_now=False, auto_now_add = True)

    last_request = models.DateTimeField()

    # The state of this request - indicates what actions the
    # worker/requester has completed in relation to this request.
    state = QualReqStatusField()

    # Answer contains the response data from the Worker when they
    # complete the Qualification test.
    answer = models.TextField(blank=True)
    last_submitted = models.DateTimeField(null=True)

    #rejected = models.BooleanField(default=False)
    # Rejection Reason String
    MAX_REASON_LEN = 256
    reason = models.CharField(max_length=MAX_REASON_LEN, blank=True)


    # Qual Request State methods
    def is_idle(self):
        return( self.state == QualReqStatusField.IDLE )

    def is_pending(self):
        return( self.state == QualReqStatusField.PENDING )

    def is_rejected(self):
        return( self.state == QualReqStatusField.REJECTED )

    def is_approved(self):
        return( self.state == QualReqStatusField.APPROVED )

    def serialize(self):
        ret = {
            "QualificationRequestId" : self.aws_id,
            "QualificationTypeId" : self.qualification.aws_id,
            "WorkerId" : self.worker.aws_id,
        }
        if ( len(self.answer) > 0 ):
            ret.update({
                "Test" : self.qualification.test,
                "Answer" : self.answer,
                "SubmitTime" : self.last_submitted,
                })
        return(ret)

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

class InvalidQualRequirementError(Exception):
    def __init__(self):
        super().__init__(
            "Invalid Qualification Requirement - must have int values or locales - has neither"
        )

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

    def get_values_display(self):
        vals = self.get_int_values()
        if ( len(vals) > 0 ):
            return(vals)
        else:
            ret = []
            for loc in self.locale_values:
                ret.append( str(loc) )
            return(ret)

    def is_not_exists(self):
        return( self.comparator == QualComparatorField.DOES_NOT_EXIST )

    def get_int_values(self):
        comps = self.int_values.split(",")
        comps = [ x.strip() for x in comps if len(x) > 0]
        return( [ int(x) for x in comps ] )

    def check_lt(self, grant):
        if ( grant is None ):
            return(False)
        vals = self.get_int_values()
        return( grant.value < vals[0] )

    def check_lte(self, grant):
        if ( grant is None ):
            return(False)
        vals = self.get_int_values()
        return( grant.value <= vals[0] )

    def check_gt(self, grant):
        if ( grant is None ):
            return(False)
        vals = self.get_int_values()
        return( grant.value > vals[0] )

    def check_gte(self, grant):
        if ( grant is None ):
            return(False)
        vals = self.get_int_values()
        return( grant.value >= vals[0] )

    def check_equal(self, grant):
        if ( grant is None ):
            return(False)
        vals = self.get_int_values()
        if ( len(vals) > 0 ):
            return( grant.value == vals[0] )
        else:
            if ( self.locale_values.all().count() == 0 ):
                raise InvalidQualRequirementError()

            if ( grant.locale is None ):
                raise Exception("Grant must have a locale!")

            loc = self.locale_values.all()[0]
            return ( grant.locale == loc )

    def check_not_equal(self, grant):
        if ( grant is None ):
            return(False)
        return( not self.check_equal(grant) )

    def check_exists(self, grant):
        return(grant is not None)

    def check_does_not_exist(self, grant):
        return( grant is None )

    def check_in_set(self, grant):
        if ( grant is None ):
            return(False)

        if ( self.locale_values.all().count() == 0 ):
            vals = self.get_int_values()
            if ( len(vals) == 0 ):
                raise InvalidQualRequirementError()

            valSet = set(vals)
            return( grant.value in valSet )
        else:
            return(
                self.locale_values.filter(
                    pk = grant.locale.id
                ).exists()
            )

    def check_not_in_set(self, grant):
        if ( grant is None ):
            return(False)

        return( not self.check_in_set(grant) )


    def check_grant(self, grant):
        """
        Check if a particular grant meets the specifications of this
        qual requirement.
        """
        check_methods = {
            QualComparatorField.LESS_THAN: self.check_lt,
            QualComparatorField.LESS_THAN_OR_EQUAL: self.check_lte,
            QualComparatorField.GREATER_THAN: self.check_gt,
            QualComparatorField.GREATER_THAN_OR_EQUAL: self.check_gte,
            QualComparatorField.EQUAL_TO: self.check_equal,
            QualComparatorField.NOT_EQUAL_TO: self.check_not_equal,
            QualComparatorField.EXISTS: self.check_exists,
            QualComparatorField.DOES_NOT_EXIST: self.check_does_not_exist,
            QualComparatorField.IN_SET: self.check_in_set,
            QualComparatorField.NOT_IN_SET: self.check_not_in_set,
        }

        method = check_methods[self.comparator]
        return( method(grant) )

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

    def has_quals(self):
        return(self.qualifications.all().exists())

    def active_task_count(self):
        activeTasks = self.task_set.filter(
            status = TaskStatusField.ASSIGNABLE,
            expires__gt = timezone.now()
        )
        return(activeTasks.count())

    def first_active_task(self):
        activeTasks = self.task_set.filter(
            status = TaskStatusField.ASSIGNABLE,
            expires__gt = timezone.now()
        )
        return(activeTasks[0])

    def serialize_qualifications(self):
        """
        Serialize this task's qualification requirements
        for sending the JSON API.
        """
        ret = []
        for qualreq in self.qualifications.all():
            q = {
                "QualificationTypeId" : qualreq.qualification.aws_id,
                "Comparator" : qualreq.get_comparator_display(),
                "RequiredToPreview": qualreq.required_to_preview,
            }
            if ( len(qualreq.int_values) > 0):
                q["IntegerValues"] = qualreq.int_values
            elif ( qualreq.locale_values.all().exists() ):
                locList = []
                for locale in qualreq.locale_values.all():
                    locList.append(locale.serialize())
                q["LocaleValues"] = locList
            else:
                raise Exception("Invalid Qual Requirement Data!")

            ret.append(q)

        return(ret)


    def human_duration(self):
        dur = self.assignment_duration
        # @todo - make this generate words that are easier to
        # understand for human.
        return(str(dur))

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

    def is_questionform(self):
        q = QuestionValidator()
        quesType = q.determine_type( self.question )
        return( quesType == "QuestionForm" )

    # Status Accessors
    def is_expired(self):
        return( timezone.now() > self.expires )

    def is_assignable(self):
        return(self.status == TaskStatusField.ASSIGNABLE )

    def is_unassignable(self):
        return(self.status == TaskStatusField.UNASSIGNABLE)

    def is_reviewable(self):
        return( self.status == TaskStatusField.REVIEWABLE )

    def is_reviewing(self):
        return( self.status == TaskStatusField.REVIEWING )

    def check_state_change(self):
        """
        This method checks the number of assignments for a task
        given its state and manages the state transitions
        @note - this method is invoked primarily in a post_save
          signal event on assignment save.
        """
        # @todo - we aren't handling task expiration especially
        #    well here yet.
        available, pending, completed, submitted = self.compute_assignment_stats()
        #print("State Change: %d/%d/%d/%d" % (available, pending, completed,submitted))
        if ( self.is_assignable() ):
            if ( available == 0 and submitted >= self.max_assignments):
                self.status = TaskStatusField.REVIEWABLE
                self.save()
            elif ( available == 0 ):
                self.status = TaskStatusField.UNASSIGNABLE
                self.save()

        elif ( self.is_unassignable() ):
            if ( available == 0 and submitted >= self.max_assignments ):
                self.status = TaskStatusField.REVIEWABLE
                self.save()
            elif ( available > 0 ):
                # Worker could have returned a task making it
                # assignable again.
                self.status = TaskStatusField.ASSIGNABLE
                self.save()

    def has_quals(self):
        return( self.tasktype.has_quals() )

    def worker_has_accepted(self, worker):
        hasAccepted = self.assignment_set.filter(
            dispose = False,
            worker = worker,
            status = AssignmentStatusField.ACCEPTED
        ).exists()
        return(hasAccepted)

    def has_assignment(self, worker):
        """
        Determine if a worker has submitted an assignment for this
        task.
        """
        return( self.assignment_set.filter(
            dispose = False,
            worker = worker
            ).exists() )

    def pending_assignments(self):
        q = (
            Q(dispose=False) &
            Q(status = AssignmentStatusField.ACCEPTED)
        )
        return( self.assignment_set.filter(q))

    def submitted_assignments(self):
        """
        Get a list of all assignments that have been submitted by
        workers but have not been approved/rejected yet.
        """

        ret = self.assignment_set.filter(
            dispose=False,
            status = AssignmentStatusField.SUBMITTED
        )

        return(ret)

    def completed_assignments(self):
        """
        Get a list of all the assignments that are completed, meaning
        that they were submitted by a worker and the requester
        has approved or rejected them.
        """
        q = (
            Q(dispose=False) &
            ( Q(status = AssignmentStatusField.APPROVED) |
              Q(status = AssignmentStatusField.REJECTED)
              )
            )
        ret = self.assignment_set.filter(q)
        return(ret)

    def prop_table(self):
        """
        Return key value pair objects for the 'property_table' template
        component.
        """
        ret = [
            {"label" : "AWS Id", "value": self.aws_id},
            {"label" : "Requester", "value": self.requester.user.get_full_name()},
            {"label" : "Status", "value": self.get_status_display()},
            {"label" : "Created", "value": self.created},
            {"label" : "Expires", "value": self.expires},
            {"label" : "Description", "value": self.tasktype.description},
            {"label" : "Duration", "value": self.tasktype.human_duration()},
            {"label" : "Reward", "value" : "$%s" % self.tasktype.reward},
            {"label" : "Max Assignments", "value" : self.max_assignments},
        ]
        return(ret)

    @property
    def completed_assignment_count(self):
        return(self.completed_assignments().count())

    @property
    def pending_assignment_count(self):
        return( self.pending_assignments().count() )

    @property
    def submitted_assignment_count(self):
        return( self.submitted_assignments().count())

    def compute_assignment_stats(self):
        completed = self.completed_assignment_count
        pending = self.pending_assignment_count
        submitted = self.submitted_assignment_count
        available = self.max_assignments - (completed + pending + submitted)
        if ( available < 0 ):
            available = 0

        return(available, pending, completed, submitted)

    @property
    def available_assignment_count(self):
        available,_,_,_ = self.compute_assignment_stats()
        return(available)

    def serialize_assignment_stats(self):

        available, pending, completed,_ = self.compute_assignment_stats()

        ret = {
            "NumberOfAssignmentsPending" : pending,
            "NumberOfAssignmentsAvailable" : available,
            "NumberOfAssignmentsCompleted" : completed,
        }
        return(ret)


    def serialize(self, includeAnnotation=False):
        ret = {
            "HITId" : self.aws_id,
            "HITTypeId" : self.tasktype.aws_id,
            #"HITGroupId" : "",
            #"HITLayoutId" : "",
            "CreationTime" : self.created,
            "Title" : self.tasktype.title,
            "Description" : self.tasktype.description,
            "Reward" : "%.02f" % self.tasktype.reward,
            "AutoApprovalDelayInSeconds" : int(self.tasktype.auto_approve.total_seconds()),
            "AssignmentDurationInSeconds" : int(self.tasktype.assignment_duration.total_seconds()),
            "Expiration" : self.expires,
            "Keywords" : self.tasktype.serialize_keywords(),
            "HITStatus" : self.get_status_display(),
            "MaxAssignments" : self.max_assignments,
            "QualificationRequirements" : self.tasktype.serialize_qualifications(),
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

    # QuestionFormAnswers object that encodes all
    #   of the data that a worker has submitted for a
    #   particular assignment.
    answer = models.TextField()

    # Need to  figure out how to store the answers to a
    # assignment
    MAX_FEEDBACK_LEN = 512
    feedback = models.CharField(max_length = MAX_FEEDBACK_LEN)

    # Flag indicating whether this object is "deleted" or not
    dispose = models.BooleanField(default=False)

    def is_accepted(self):
        return( self.status == AssignmentStatusField.ACCEPTED )

    def is_submitted(self):
        return( self.status == AssignmentStatusField.SUBMITTED )

    def approve(self, reason=""):
        self.approved = timezone.now()
        self.status = AssignmentStatusField.APPROVED
        self.feedback = reason

    def is_approved(self):
        return( self.status == AssignmentStatusField.APPROVED )

    def reject(self, reason=""):
        self.rejected = timezone.now()
        self.status = AssignmentStatusField.REJECTED
        self.feedback = reason

    def is_rejected(self):
        return( self.status == AssignmentStatusField.REJECTED )

    def is_decided(self):
        return( self.is_approved() or self.is_rejected() )

    def get_answer_display(self):
        """
        Parse the QuestionFormAnswer object if it exists and
        put together an object that can be used in the
        qformanswer_table template.
        @return list of dict objects, each being a set of
            key-value pairs for the question Id and submitted answer
        """
        ans = QFormAnswer()
        return(ans.parse(self.answer))

    def prop_table(self):
        """
        Generate a list of key value pairs for displaying in a
        property_table template component.
        """
        ret = [
            {"label" : "AWS Id", "value": self.aws_id},
            {"label" : "Worker", "value": self.worker.aws_id},
            {"label" : "Status", "value": self.get_status_display()},
            {"label" : "Accepted", "value" : self.accepted},
            {"label" : "Deadline", "value" : self.deadline},
        ]
        if ( self.submitted is not None ):
            ret.append({"label" : "Submitted", "value" : self.submitted})
        if ( self.approved is not None ):
            ret.append({"label" : "Approved", "value" : self.approved})
        if ( self.rejected is not None ):
            ret.append({"label" : "Rejected", "value" : self.rejected})
        if ( self.is_submitted() ):
            ret.append({"label" : "Auto Approve", "value" : self.auto_approve})
        return(ret)

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

        if ( self.submitted is not None ):
            ret["SubmitTime"] = self.submitted
            ret["Answer"] = self.answer
            ret["AutoApprovalTime"] = self.auto_approve

            if ( self.is_decided() ):
                ret["RequesterFeedback"] = self.feedback
                if ( self.approved is not None ):
                    ret["ApprovalTime"] = self.approved

                if ( self.rejected is not None ):
                    ret["RejectionTime"] = self.rejected


        return(ret)

    def __str__(self):
        return("<%s...,STAT=%s" % (self.aws_id[0:6], self.status))

@receiver(post_save, sender=Assignment, dispatch_uid="mturk_assignmt_save")
def task_state_update(sender, instance, **kwargs):
    """
    Check for state update of the task associated with an Assignment
    whenever an assignmnent is updated.
    """
    assignment = instance
    task = assignment.task
    task.check_state_change()

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
    created=models.DateTimeField(auto_now=False, auto_now_add = True)

    active = models.BooleanField(default=False)
    MAX_REASON_LEN = 256
    reason = models.CharField(max_length=MAX_REASON_LEN)

    def serialize(self):
        return({
            "WorkerId": self.worker.aws_id,
            "Reason" : self.reason
        })

from mturk.user import *
