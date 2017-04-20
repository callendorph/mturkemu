# File: mturk/taskviews.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the implementation of
# some classes for implementing the more complicated
# API methods related to HIT and HITType creation.

from mturk.models import *
from mturk.xml.questions import QuestionValidator
from mturk.errors import *

from datetime import timedelta

def parse_keyword_tags(keywordStr):
    """
    Parse a comma-separated string of keywords into two lists,
    the first is a list of existing @c KeywordTag objects and
    the second is a list of strings indicating new tags
    @return tuple consisting of (existingList, newList)
    """
    comps = [x.strip() for x in keywordStr.split(",")]
    kwds = [x.lower() for x in comps if len(x) > 0 ]

    if ( len(comps) > 0 ):

        # Attempt to find existing tags with these keywords,
        # and arrange two lists of existing and new keywords
        existing = []
        newTags = []
        for kwd in kwds:
            try:
                tag = KeywordTag.objects.get(value=kwd)
                existing.append(tag)
            except KeywordTag.DoesNotExist:
                newTags.append(kwd)
        return(existing, newTags)
    else:
        return([], [])

def create_keyword_tags( tags):
    """
    Create a set of new keywords
    @param tags list of strings
    """
    ret = []
    for tag in tags:
        keyword = KeywordTag.objects.create(value=tag)
        keyword.save()
        ret.append(keyword)
    return(ret)


class CreateTaskType(object):
    DEFAULT_AUTO_APPROVE = 2592000 # Seconds

    def __init__(self, request):
        self.request = request

        self.requester = request["EmuRequester"]

        # Common Parameters
        self.params = {
            "requester": self.requester,
            "assignment_duration": timedelta(
                seconds=int(request["AssignmentDurationInSeconds"])
            ),
            "reward": float(request["Reward"]),
            "title" : request["Title"],
            "description": request["Description"],
        }
        autoApprove = int(request.get(
            "AutoApprovalDelayInSeconds",
            CreateTaskType.DEFAULT_AUTO_APPROVE
        ))
        self.params["auto_approve"] = timedelta(seconds = autoApprove)

        self.existing, self.newTags = self._findKeywords()

        self.quals = self._parseQuals()

    def _parseQuals(self):
        """
        Return a list of QualificationRequirement objects
        """
        ret = []
        reqQuals = self.request.get("QualificationRequirements", [])
        for reqQual in reqQuals:
            compStr = reqQual["Comparator"]
            compId = QualComparatorField.convert_display_to_value(compStr)

            qualId = reqQual["QualificationTypeId"]

            qual = Qualification.objects.get(aws_id = qualId)
            if ( not qual.active ):
                raise RequestError(
                    "Qualification[%s] is not active" % qualId, 12
                )

            baseReqParams = {
                "comparator" : compId,
                "required_to_preview": reqQual.get("RequiredToPreview", False),
            }

            intList = reqQual.get("IntegerValues", "")
            if ( len(intList) > 0 ):
                intStr = ",".join([str(x) for x in intList])
                baseReqParams["int_values"] = intStr

            try:
                localeList = reqQual["LocaleValues"]
                raise NotImplementedError("Locale Query Not Implemented Yet")
                baseReqParams["locale_values"] = []
            except KeyError:
                pass

            # We now create a qualification requirement object if
            # one does not exist that matches these specifications
            queryParams = {
                "qualification__aws_id": qualId,
            }
            queryParams.update(baseReqParams)

            try:
                obj = QualificationRequirement.objects.get( **queryParams )
            except QualificationRequirement.DoesNotExist:
                createParams = {
                    "qualification" : qual,
                }
                createParams.update(baseReqParams)

                obj = QualificationRequirement.objects.create(**createParams)

            ret.append(obj)

        return(ret)



    def _findKeywords(self):
        try:
            keywordStr = self.request["Keywords"]
        except KeyError:
            return([],[])

        return(parse_keyword_tags(keywordStr))


    def find_existing(self):
        """
        Search the database to find a tasktype object that
        matches the parameters listed.
        @note - This query is definitely not optimal - there is
           probably a better way to do this but right now I'm not
           investing the time to make it better.
        """

        if ( len(self.newTags) > 0 ):
            raise Exception("New Tags in Keywords - Can't Match")

        objs = TaskType.objects.filter(**self.params)

        if ( objs.count() == 0 ):
            raise Exception("No Simple Match for TaskType objects")

        # Check these objects for a match to the existing keyword tags
        candidates = []
        existingSet = set([x.value for x in self.existing])
        for obj in objs:
            if ( obj.keywords.count() == len( self.existing ) ):
                valSet = set(obj.keywords.all().values_list("value", flat=True))
                if ( valSet == existingSet ):
                    candidates.append( obj )

        if ( len(candidates) == 0 ):
            raise Exception("No TaskType Object with matching Keywords")

        # Finally - we check the qualification requirements
        # We want to find the TaskType from our last query
        # for which all the qualifications match.

        expQualSet = set( [x.id for x in self.quals] )

        for obj in candidates:
            if ( obj.qualifications.count() != len(self.quals) ):
                continue

            objQualSet = set( [ x.id for x in obj.qualifications.all()] )
            if ( expQualSet == objQualSet ):
                return(obj)

        raise Exception("No Matching Qual Set")

    def create(self):
        """
        Create a new TaskType object (HIT Type). This is invoked after
        our other attempts to find an existing task type fail.
        """
        tt = TaskType.objects.create(**self.params)

        # Add the qualification req objects
        for qual in self.quals:
            tt.qualifications.add(qual)

        # Create new Tags and add to our existing list.
        self.existing.extend( create_keyword_tags(self.newTags) )
        # Setup the keywords
        for tag in self.existing:
            tt.keywords.add(tag)

        tt.save()

        return(tt)

class CreateTask(object):
    def __init__(self, request):
        self.request = request

    def create(self, taskType = None):

        # Args for Creating a HIT Type are a subset of
        # the args for Create HIT - so we reuse this
        # as a mechanism.
        if ( taskType is not None ):
            tt = taskType
        else:
            ttCreator = CreateTaskType(self.request)
            tt = ttCreator.create()

        createParams = {
            "requester": self.request["EmuRequester"],
            "tasktype": tt,
            "max_assignments": int(self.request["MaxAssignments"]),
        }

        # We setup the expiration datetime after creation
        # so that we can use the same "created" timestamp
        # as is generated when saved in the DB - but we need to
        # make sure it is present before trying to create the
        # object.
        lifeSeconds = int(self.request["LifetimeInSeconds"])
        if ( lifeSeconds < 30 or lifeSeconds > 31536000 ):
            raise ParameterValidationError(
                "CreateHITWithHITType", "LifetimeInSeconds",
                lifeSeconds, 30, 31536000
            )

        try:
            annot = self.request["RequesterAnnotation"]
            createParams["annotation"] = annot
        except KeyError:
            pass

        try:
            quesData = self.request["Question"]
            if ( len(quesData) > 65535 ):
                raise QuestionTooLongError()

            ques = QuestionValidator()
            validQuestionTypes = [
                "HTMLQuestion" , "ExternalQuestion", "QuestionForm"
            ]
            name = ques.determine_type(quesData)
            if ( name not in validQuestionTypes ):
                raise TaskQuestionInvalidError()

            ques.validate(name, quesData)
            createParams["question"] = quesData
        except KeyError:
            try:
                hitLayout = self.request["HITLayoutId"]
                raise NotImplementedError("HIT Layouts Not Implemented Yet")
                # @todo - when we get to this we will need these values
                hitLayoutParams = self.request["HITLayoutParameters"]
            except KeyError:
                raise MissingArgumentError("'Question' or 'HITLayoutId'")

        try:
            assignPolicy = self.request["AssignmentReviewPolicy"]
            raise NotImplementedError("Assignment Review Policy Management")
        except KeyError:
            pass

        try:
            hitPolicy = self.request["HITReviewPolicy"]
            raise NotImplementedError("HIT Review Policy Management")
        except KeyError:
            pass

        try:
            uniqToken = self.request["UniqueRequestToken"]
            if ( len(uniqToken) != 0 ):
                if ( Task.objects.filter(unique=uniqToken).exists() ):
                    raise DuplicateRequestError()
            createParams["unique"] = uniqToken
        except KeyError:
            pass

        task = Task.objects.create(**createParams)
        task.expires = task.created + timedelta(seconds=lifeSeconds)

        task.save()

        return(task)
