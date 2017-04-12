# File: mturk/handlers.py
# Author: Skeleton Autogenerated by CreateMTurkViews.py script
#
# Description:
#    This file contains the skeleton of all methods that need to be
# implemented for the MTurk mock.
#
#

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils import timezone

from mturk.models import *
from mturk.taskviews import CreateTaskType, CreateTask
from mturk.errors import *
from mturk.questions import QuestionValidator
from mturk.fields import *

from datetime import timedelta
import re

def get_object_or_throw(model, **kwargs):
    """
    Similar to the 'get_object_or_404' but for throwing a
    RequestError
    """
    try:
        obj = model.objects.get(**kwargs)
        return(obj)
    except ObjectDoesNotExist:
        raise DoesNotExistError(model)

class MTurkHandlers(object):

    # The "MaxResults" key in the list operations is not required - so
    #    we need a default to use.
    #  @todo - Check the amazon service to determine what the default
    #    behavior is. Max is 100 - so I don't think it can be
    #    just return ALL the objects in the list. This would also
    #    be a DoS capable vulnerability.
    DEF_NUM_RESULTS = 10

    def gen_next_token(self, offset):
        """
        The next token in the AWS service is a string token but
        this attempts to simplify this by just setting a offset
        index encoded in the token string that we can parse to
        determine the next position to respond with in a list API
        method.
        """
        return( "A%010d" % offset )

    def get_offset_from_token(self, token):
        """
        Utility to extract the offset in a query from the next
        token submitted in a list request.
        """
        tokenRegex = re.compile("A(\d+)")
        m = tokenRegex.match(token)
        if m:
            offsetStr = m.group(1)
            offset = int(offsetStr)
            return(offset)
        else:
            raise ValidationError(["Invalid Next Token Format: %s" % token])

    def get_list_args(self, kwargs):
        results = kwargs.get("MaxResults", MTurkHandlers.DEF_NUM_RESULTS)
        try:
            token = kwargs["NextToken"]
            offset = self.get_offset_from_token(token)
        except KeyError:
            offset = 0
        return(results, offset)

    def prepare_list_response(self, name, offset, dataList, **kwargs):
        """
        Generate the standard list response for a set of
        data items.
        """
        cnt = dataList.count()
        resp = {
            "NumResults" : cnt,
            name : [ datum.serialize(**kwargs) for datum in dataList ]
        }
        if ( cnt > 0 ):
            nextToken = self.gen_next_token( offset + cnt )
            resp["NextToken"] = nextToken
        return(resp)


    #######################
    # API Methods
    #######################

    def ApproveAssignment(self, **kwargs):
        requester = kwargs["EmuRequester"]
        assignId = kwargs["AssignmentId"]

        overrideReject = kwargs.get("OverrideRejection", False)

        assign = get_object_or_throw(
            Assignment,
            aws_id = assignId
            )

        if ( assign.task.requester != requester ):
            raise PermissionDenied()

        if ( assign.is_accepted()):
            raise AssignmentNotSubmittedError()

        if ( assign.is_rejected() and not overrideReject ):
            raise AssignmentAlreadyRejectedError()

        if ( assign.is_approved() ):
            # @note - check what AWS actually does here
            raise RequestError("Assignment already Approved", 17)

        assign.status = AssignmentStatusField.APPROVED
        assign.approved = timezone.now()

        try:
            feedback = kwargs["RequesterFeedback"]
            assign.feedback = feedback
        except KeyError:
            pass

        assign.save()

        return({})

    def ListWorkersWithQualificationType(self, **kwargs):
        requester = kwargs["EmuRequester"]
        qualId = kwargs["QualificationTypeId"]

        stat = kwargs.get("Status", None)

        numResults,offset = self.get_list_args(kwargs)

        q = Q( qualification__aws_id = qualId )
        if ( stat == "Granted" ):
            q &= Q( active = True )
        elif ( stat == "Revoked" ):
            q &= Q( active = False )

        grants = QualificationGrant.objects.filter(q).order_by(
            "-granted"
        )[offset:(offset+numResults)]

        resp = self.prepare_list_response("Qualifications", offset, grants)

        return(resp)

    def ListAssignmentsForHIT(self, **kwargs):
        requester = kwargs["EmuRequester"]
        taskId = kwargs["HITId"]

        task = get_object_or_throw(Task, aws_id = taskId)
        if ( task.requester != requester ):
            raise PermissionDenied()

        assignStats = kwargs["AssignmentStatuses"]
        buildQuery = Q(dispose=False)
        selQuery = Q()
        for stat in assignStats:
            if ( stat == "Submitted" ):
                selQuery |= Q(status = AssignmentStatusField.SUBMITTED)
            elif ( stat == "Approved" ):
                selQuery |= Q(status = AssignmentStatusField.APPROVED)
            elif ( stat == "Rejected" ):
                selQuery |= Q(status = AssignmentStatusField.REJECTED)
            else:
                raise AssignmentInvalidStateError()

        buildQuery &= selQuery

        numResults,offset = self.get_list_args(kwargs)
        # @note - I'm ordering by accepted because this should always
        #   be available no matter the state of the assignment.
        assignments = task.assignment_set.filter(
            buildQuery
        ).order_by("-accepted")[offset:(offset + numResults)]

        resp = self.prepare_list_response("Assignments", offset, assignments)

        return(resp)

    def ListWorkerBlocks(self, **kwargs):
        requester = kwargs["EmuRequester"]

        numResults,offset = self.get_list_args(kwargs)

        blocks = WorkerBlock.objects.filter(
            requester = requester,
            active = True
            ).order_by("-created")[offset:(offset+numResults)]

        resp = self.prepare_list_response("WorkerBlocks", offset, blocks)
        return(resp)

    def CreateAdditionalAssignmentsForHIT(self, **kwargs):
        requester = kwargs["EmuRequester"]
        taskId = kwargs["HITId"]
        addAssigns = kwargs["NumberOfAdditionalAssignments"]

        task = get_object_or_throw(Task, aws_id = taskId)
        if ( task.requester != requester ):
            raise PermissionDenied()

        newAssignsCount = task.max_assignments + addAssigns
        if ( task.max_assignments < 10 and newAssignCount >= 10 ):
            raise TaskInvalidAssignmentIncreaseError()

        task.max_assignments = newAssignsCount
        try:
            unique = kwargs["UniqueRequestToken"]
            if ( len(unique) > 0 ):
                if ( task.unique == unique ):
                    # @note - No SAVE Op called yet so max_assignments
                    # will revert
                    raise DuplicateRequestError()

            task.unique = unique
        except KeyError:
            pass

        task.save()

        return({})

    def CreateWorkerBlock(self, **kwargs):
        requester = kwargs["EmuRequester"]
        workerId = kwargs["WorkerId"]
        worker = get_object_or_throw(
            Worker,
            aws_id = workerId
            )

        try:
            block = WorkerBlock.objects.get(
                worker = worker,
                requester = requester
                )
        except WorkerBlock.DoesNotExist:
            block = WorkerBlock.objects.create(
                worker = worker,
                requester = requester
                )
        block.active = True
        try:
            reason = kwargs["Reason"]
            block.reason = reason
        except KeyError:
            pass
        block.save()
        return({})

    def GetQualificationScore(self, **kwargs):
        requester = kwargs["EmuRequester"]
        qualId = kwargs["QualificationId"]
        workerId = kwargs["WorkerId"]

        qual = get_object_or_throw(Qualification, aws_id = qualId)
        if ( qual.requester != requester ):
            raise PermissionDenied()

        qualGrant = get_object_or_throw(
            QualificationGrant,
            worker__aws_id = workerId,
            qualification = qual
            )

        return({
            "Qualification" : qualGrant.serialize()
            })


    def UpdateHITTypeOfHIT(self, **kwargs):
        # @note - I'm not totally sure how this
        #    method should be implemented - very low
        #    on details in the docs
        #
        # Need to do some experimentation in the
        # sandbox to determine functionality.
        raise NotImplementedError("Confusing Docs")

    def NotifyWorkers(self, **kwargs):
        raise NotImplementedError("No Notifications Yet")

    def ListQualificationTypes(self, **kwargs):
        requester = kwargs["EmuRequester"]

        requestable = kwargs["MustBeRequestable"]
        ownedByRequester = kwargs.get("MustBeOwnedByCaller", False)
        query = kwargs.get("Query", None)

        numResults,offset = self.get_list_args(kwargs)

        # Build the query
        q = Q(requestable = requestable) & Q(dispose=False)
        if ( ownedByRequester ):
            q &= Q(requester = requester)

        if ( query is not None ):
            searchQuery = (
                Q(name__contains=query) |
                Q(description__contains=query) |
                Q(keywords__value__contains=query)
            )
            q &= searchQuery


        quals =Qualification.objects.filter(q).order_by(
            "-created"
        )[offset:(offset+numResults)]

        resp = self.prepare_list_response("QualificationTypes", offset, quals)
        return(resp)

    def UpdateHITReviewStatus(self, **kwargs):
        requester = kwargs["EmuRequester"]
        taskId = kwargs["HITId"]
        revert = kwargs.get("Revert", False)

        task = get_object_or_throw(Task, aws_id = taskId)
        if ( task.requester != requester ):
            raise PermissionDenied()

        if ( task.is_reviewable() ):
            task.state = TaskStatusField.REVIEWING
        elif ( task.is_reviewing() and revert ):
            task.state = TaskStatusField.REVIEWABLE

        task.save()

        return({})

    def CreateHITWithHITType(self, **kwargs):
        requester = kwargs["EmuRequester"]
        typeId = kwargs["HITTypeId"]

        taskType = get_object_or_throw(
            TaskType,
            requester = requester,
            aws_id = typeId
            )

        proc = CreateTask(kwargs)
        task = proc.create(taskType = taskType)

        return({
            "HIT": task.serialize()
        })


    def DeleteHIT(self, **kwargs):
        requester = kwargs["EmuRequester"]
        HITId = kwargs["HITId"]
        task = get_object_or_throw(
            Task,
            requester = requester,
            aws_id = HITId
            )
        task.dispose = True
        task.save()
        return({})

    def CreateQualificationType(self, **kwargs):
        requester = kwargs["EmuRequester"]

        name = kwargs["Name"]
        try:
            qual = Qualification.objects.get(
                requester = requester,
                name=name,
                dispose=False,
            )
            raise QualificationTypeAlreadyExistsError()
        except Qualification.DoesNotExist:
            pass

        createParams = {
            "requester" : requester,
            "name": name,
            "description" : kwargs["Description"],
        }

        status = kwargs["QualificationTypeStatus"]
        createParams["active"] = (status == "Active")

        try:
            retry_delay = int(kwargs["RetryDelayInSeconds"])
            createParams["retry_active"] = True
            createParams["retry_delay"] = timedelta(seconds=retry_delay)
        except KeyError:
            createParams["retry_active"] = False

        q = QuestionValidator()
        try:
            test = kwargs["Test"]
            if ( len(test) > 65535 ):
                raise QuestionTooLongError()

            if ( "TestDurationInSeconds" not in kwargs):
                raise MissingArgumentError("TestDurationInSeconds")

            testDuration = int(kwargs["TestDurationInSeconds"])
            if ( "AutoGranted" in kwargs ):
                if ( kwargs["AutoGranted"] ):
                    raise ValidationError(
                        ["Qualification cannot have AutoGranted 'True' and have a Test QuestionForm"]
                    )

            name = q.determine_type(test)
            if ( name not in ["QuestionForm"]):
                raise QualTestInvalidError()

            q.validate(name, test)
            createParams["test"] = test
            createParams["test_duration"] = timedelta(seconds=testDuration)
        except KeyError:
            pass

        try:
            answerKey = kwargs["AnswerKey"]
            if ( len(answerKey) > 65535 ):
                raise AnswerTooLongError()

            name = q.determine_type(answerKey)
            if ( name not in ["AnswerKey"]):
                raise QualAnswerInvalidError()

            q.validate(name, answerKey)
            createParams["answer"] = answerKey

        except KeyError:
            # Not required even with a test - just means requester
            # must manually accept.
            pass

        try:
            autoGranted = kwargs["AutoGranted"]
            createParams["auto_grant"] = autoGranted
            try:
                autoGrantValue = int(kwargs["AutoGrantedValue"])
                createParams["auto_grant_value"] = autoGrantValue
            except KeyError:
                pass
        except KeyError:
            pass


        qual = Qualification.objects.create(**createParams)
        qual.save()

        resp = {
           "QualificationType" : qual.serialize()
        }
        return(resp)

    def GetFileUploadURL(self, **kwargs):
        raise NotImplementedError("File Upload Not Implemented Yet")

    def ListQualificationRequests(self, **kwargs):
        requester = kwargs["EmuRequester"]
        qualId = kwargs.get("QualificationTypeId", None)
        if ( qualId is not None ):
            qual = get_object_or_throw(Qualification, aws_id = qualId)
            if ( qual.requester != requester ):
                raise PermissionDenied()

        numResults,offset = self.get_list_args(kwargs)

        if (qualId is not None):
            q = Q( qualification__aws_id = qualId )
        else:
            q = Q( qualification__requester=requester )

        reqs = QualificationRequest.objects.filter(q).order_by(
            "-created"
        )[offset:(offset+numResults)]

        resp = self.prepare_list_response("QualificationRequests", offset, reqs)
        return(resp)

    def GetHIT(self, **kwargs):
        HITId = kwargs["HITId"]
        task = get_object_or_throw(Task, aws_id = HITId)

        return({
            "HIT" : task.serialize()
            })

    def SendTestEventNotification(self, **kwargs):
        # @note - Not Implementing Notifications Yet
        raise NotImplementedError()


    def DeleteWorkerBlock(self, **kwargs):
        requester = kwargs["EmuRequester"]
        workerId = kwargs["WorkerId"]

        worker = get_object_or_throw(
            Worker,
            aws_id = workerId
            )

        try:
            block = WorkerBlock.objects.get(
                worker = worker,
                requester = requester
                )
            block.active = False
            try:
                reason = kwargs["Reason"]
                block.reason = reason
            except KeyError:
                pass
            block.save()

        except WorkerBlock.DoesNotExist:
            # @todo - do we need to raise an error if there
            # was not workerblock to remove?
            pass

        return({})


    def CreateHITType(self, **kwargs):

        proc = CreateTaskType(kwargs)

        try:
            tt = proc.find_existing()
        except:
            tt = proc.create()

        return({
            "HITTypeId" : tt.aws_id,
        })


    def RejectAssignment(self, **kwargs):
        requester = kwargs["EmuRequester"]
        assignId = kwargs["AssignmentId"]

        assign = get_object_or_throw(
            Assignment,
            aws_id = assignId
            )

        if ( assign.task.requester != requester ):
            raise PermissionDenied()

        if ( not assign.is_submitted() ):
            raise AssignmentNotSubmittedError()

        # @todo - need to check if the service throws an error
        # if the assignment has already been approved.

        assign.status = AssignmntStatusField.REJECTED
        assign.rejected = timezone.now()
        try:
            feedback = kwargs["RequesterFeedback"]
            # @todo - I need to filter feedback and throw an error
            #    Needs to be less than 1024 chars and
            #    needs to filter ASCII 0-8,11,12, 14-31,
            assign.feedback = feedback
        except KeyError:
            pass

        assign.save()

        return({})

    def ListReviewableHITs(self, **kwargs):
        requester = kwargs["EmuRequester"]

        taskTypeId = kwargs.get("HITTypeId", None)
        stat = kwargs.get("Status", "Reviewable")

        numResults,offset = self.get_list_args(kwargs)

        q = Q(requester = requester) & Q(dispose=False)
        if ( taskTypeId is not None ):
            q &= Q(tasktype__aws_id = taskTypeId)

        if ( stat == "Reviewable" ):
            q &= Q(status = TaskStatusField.REVIEWABLE)
        else:
            q &= Q(status = TaskStatusField.REVIEWING)

        tasks = Task.objects.filter(q).order_by(
            "-created"
        )[offset:(offset+numResults)]

        resp = self.prepare_list_response(
            "HITs", offset, tasks, includeAnnotation=True
        )
        return(resp)

    def ListHITs(self, **kwargs):
        requester = kwargs["EmuRequester"]
        numResults,offset = self.get_list_args(kwargs)

        tasks = Task.objects.filter(
            requester = requester,
            dispose=False,
            ).order_by("-created")[offset:(offset+numResults)]

        resp = self.prepare_list_response(
            "HITs", offset, tasks, includeAnnotation=True
        )

        return(resp)

    def UpdateExpirationForHIT(self, **kwargs):
        requester = kwargs["EmuRequester"]

        taskId = kwargs["HITId"]
        expireAt = kwargs["ExpireAt"]

        task = get_object_or_throw(Task, aws_id = taskId)
        if ( task.requester != requester ):
            raise PermissionDenied()

        currTime = timezone.now()
        if ( expireAt < currTime ):
            # Immediately Expire the Task
            # @todo - I need to test this on the sandbox
            #   to confirm this is the right behavior
            task.state = TaskStatusField.UNASSIGNABLE
        else:
            task.expires = expireAt

        task.save()
        return({})


    def RejectQualificationRequest(self, **kwargs):
        requester = kwargs["EmuRequester"]
        reqId = kwargs["QualificationRequestId"]

        req = get_object_or_throw(
            QualificationRequester,
            aws_id = reqId
            )

        if ( req.qualification.requester != requester ):
            raise PermissionDenied()

        if ( not req.is_pending() ):
            # @todo - check if the server responds like this when
            #    the request is idle or already approved/rejected
            raise QualReqInvalidStateError()

        req.state = QualReqStatusField.REJECTED
        req.reason = kwargs.get("Reason", "")

        req.save()

        return({})

    def AssociateQualificationWithWorker(self, **kwargs):
        requester = kwargs["EmuRequester"]
        qualId = kwargs["QualificationTypeId"]
        workerId = kwargs["WorkerId"]

        value = kwargs.get("IntegerValue", 1)

        try:
            sendNotif = kwargs["SendNotification"]
            if ( sendNotif ):
                logger.warn("SendNotification = True: Not Implemented Yet")
        except KeyError:
            sendNotif = False

        qual = get_object_or_throw(
            Qualification,
            requester = requester,
            aws_id = qualId
            )

        worker = get_object_or_throw(Worker, aws_id = workerId)

        # First check if a worker qualification grant already exists
        try:
            grant = QualificationGrant.objects.get(
                worker = worker,
                qualification = qualification,
                )
            grant.value = value
            grant.active = True
        except QualificationGrant.DoesNotExist:
            grant = QualificationGrant.objects.create(
                worker = worker,
                qualification = qualification,
                value = value
                )

        grant.save()

        return({})


    def UpdateQualificationType(self, **kwargs):
        requester = kwargs["EmuRequester"]
        qualId = kwargs["QualificationTypeId"]

        qual = get_object_or_throw(Qualification, aws_id = qualId)
        if ( qual.requester != requester ):
            raise PermissionDenied()

        # @todo Update parameters of the Qualification based on
        # available data
        try:
            desc = kwargs["Description"]
            if ( len(desc) > 0 ):
                qual.description = desc
        except KeyError:
            pass

        try:
            stat = kwargs["QualificationTypeStatus"]
            qual.active = ( stat == "Active" )
        except KeyError:
            pass


        try:
            retry = kwargs["RetryDelayInSeconds"]
            # @todo - handle me
        except KeyError:
            pass

        # Need to check create qual type because I think there is
        # some code that can be reused.
        #Test='string',
        #AnswerKey='string',
        #TestDurationInSeconds=123,
        #AutoGranted=True|False,
        #AutoGrantedValue=123

        return({
            "QualificationType": qual.serialize()
        })

    def GetAccountBalance(self, **kwargs):
        requester = kwargs["EmuRequester"]

        return({
            "AvailableBalance" : requester.get_balance()
            })

    def SendBonus(self, **kwargs):
        requester = kwargs["EmuRequester"]
        workerId = kwargs["WorkerId"]
        assignId = kwargs["AssignmentId"]

        worker = get_object_or_throw(Worker, aws_id = workerId)
        assign = get_object_or_throw(Assignment, aws_id = assignId)

        if ( assign.worker != worker or assign.task.requester != requester):
            raise PermissionDenied()

        createParams = {
            "worker" : worker,
            "assignment" : assign,
            }

        try:
            reason = kwargs["Reason"]
            createParams["reason"] = reason
        except KeyError:
            pass

        try:
            unique = kwargs["UniqueRequestToken"]
            if ( len(unique) > 0 ):
                hasExisting = BonusPayment.objects.filter(
                    worker = worker,
                    assignment = assign,
                    unique = unique
                ).exists()

                if ( hasExisting ):
                    raise DuplicateRequestError()

            createParams["unique"] = unique
        except KeyError:
            pass

        amount = float(kwargs["BonusAmount"])
        if ( requester.balance < amount ):
            raise RequesterInsufficientFundsError()

        createParam["amount"] = amount

        bp = BonusPayment.objects.create(**createParams)
        bp.save()

        return({})

    def GetAssignment(self, **kwargs):
        requester = kwargs["EmuRequester"]
        assignId = kwargs["AssignmentId"]

        assign = get_object_or_throw(Assignment, aws_id = assignId)

        if ( assign.requester.id != requester.id ):
            raise PermissionDenied()

        ret = {
            "Assignment" : assign.serialize(),
            "HIT" : assign.task.serialize(),
        }
        return(ret)

    def DeleteQualificationType(self, **kwargs):
        requester = kwargs["EmuRequester"]
        qualId = kwargs["QualificationTypeId"]

        q = get_object_or_throw(
            Qualification,
            requester = requester,
            aws_id = qualId
            )

        q.active = False
        q.dispose = True
        q.save()

        return({})


    def CreateHIT(self, **kwargs):

        proc = CreateTask(kwargs)
        task = proc.create()

        return({
            "HIT": task.serialize()
        })

    def ListBonusPayments(self, **kwargs):
        requester = kwargs["EmuRequester"]
        HITId = kwargs.get("HITId", None)
        AssignId = kwargs.get("AssignmentId", None)
        if ( HITId is None and AssignId is None ):
            raise ValidationError(["Missing required argument of either 'HITId' or 'AssignmentId'"])

        if ( HITId is not None and AssignId is not None ):
            # @todo - check that this is the appropriate behavior with
            #   the sandbox
            raise ValidationError(["Request must have either 'HITId' or 'AssignmentId', not both."])

        numResults,offset = self.get_list_args(kwargs)

        if ( HITId is not None ):
            # Check that the HIT is owned by the requester
            task = get_object_or_throw(Task, aws_id = HITId )
            if ( task.requester != requester ):
                raise PermissionDenied()
            bonusQSet = BonusPayment.objects.filter(assignment__task = task)
        else:
            assignment = get_object_or_throw(Assignment, aws_id = AssignId)
            if ( assignment.task.requester != requester ):
                raise PermissionDenied()
            bonusQSet = BonusPayment.objects.filter(assignment = assignment)

        respList = bonusQSet.order_by("-created")[offset:(offset+numResults)]

        resp = self.prepare_list_response(
            "BonusPayments", offset, respList
        )
        return(resp)

    def UpdateNotificationSettings(self, **kwargs):
        raise NotImplementedError("No Notifications Yet")

    def DisassociateQualificationFromWorker(self, **kwargs):
        requester = kwargs["EmuRequester"]
        workerId = kwargs["WorkerId"]
        qualid = kwargs["QualificationTypeId"]

        worker = get_object_or_throw(Worker, aws_id = workerId)
        qual = get_object_or_throw(Qualification, aws_id = qualId)

        if ( qual.requester != requester ):
            raise PermissionDenied()

        grant = get_object_or_throw(
            QualificationGrant,
            worker = worker,
            qualification = qual
        )

        # @todo - check how AWS responds if the grant
        #   has already been revoked.
        if ( grant.active ):
            grant.active = False

            try:
                reason = kwargs["Reason"]
                grant.reason = reason
            except KeyError:
                pass
            grant.save()

        return({})

    def GetQualificationType(self, **kwargs):
        qualId = kwargs["QualificationTypeId"]

        qual = get_object_or_throw(Qualification, aws_id = qualId)
        return({
            "QualificationType": qual.serialize()
        })

    def AcceptQualificationRequest(self, **kwargs):
        requester = kwargs["EmuRequester"]
        reqId = kwargs["QualificationRequestId"]
        value = kwargs["IntegerValue"]

        req = get_object_or_throw(QualificationRequest, aws_id = reqId)

        if ( req.qualification.requester != requester ):
            raise PermissionDenied()

        if ( req.state != QualReqStatusField.PENDING ):
            raise QualReqInvalidStateError()

        # First check if there is a qualification grant for this
        # worker with these parameters, if so we will update it

        try:
            grant = QualificationGrant.objects.get(
                worker = req.worker,
                qualification = req.qualification,
            )
            grant.value = value
            grant.active = True
        except QualificationGrant.DoesNotExist:
            grant = QualificationGrant.objects.create(
                worker = req.worker,
                qualification = req.qualification,
                value = value
            )

        grant.save()

        req.state = ReqQualStatusField.APPROVED
        req.save()

        return({})


    def ListReviewPolicyResultsForHIT(self, **kwargs):
        raise NotImplementedError("Review Policies Are Not Implemented Yet")

    def ListHITsForQualificationType(self, **kwargs):
        requester = kwargs["EmuRequester"]
        qualId = kwargs["QualificationTypeId"]

        qual = get_object_or_throw(Qualification, aws_id=qualId)

        numResults,offset = self.get_list_args(kwargs)
        tasks = Task.objects.filter(
            tasktype__qualifications__qualification = qual,
            dispose=False,
        ).order_by("-created")[offset:(offset+numResults)]

        includeAnnots = (qual.requester == requester)

        resp = self.prepare_list_response(
            "HITs", offset, respList, includeAnnotation=includeAnnots
        )

        return(resp)
