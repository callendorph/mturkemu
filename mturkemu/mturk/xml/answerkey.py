# File: mturk/xml/answerkey.py
# Author: Carl Allendorph
# Description:
#    This file contains the implementation of code to
# parse the answer key XML object into a format that
# is more easily usable in python.


from mturk.xml.questions import QuestionValidator
from mturk.errors import *
from lxml import etree

class AnswerOption(object):
    """
    """
    def __init__(self, root):

        self.sel_id_list = []
        self.score = 0

        self.parse(root)

    def parse(self, root):
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "SelectionIdentifier" ):
                self.sel_id_list.append(child.text)
            elif ( tag.localname == "AnswerScore" ):
                self.score = int(child.text)
            else:
                raise InvalidTagError(tag)

class QuestionAnswer(object):
    """
    """
    def __init__(self, root):

        self.ques_id = ""
        self.opts = []
        self.defaultScore = 0

        self.parse(root)

    def parse(self, root):

        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "QuestionIdentifier" ):
                self.ques_id = child.text
            elif ( tag.localname == "AnswerOption"):
                self.opts.append( AnswerOption(child) )
            elif ( tag.localname == "DefaultScore" ):
                self.defaultScore = int(child.text)
            else:
                raise InvalidTagError(tag)

class PercMapping(object):
    def __init__(self, root):
        self.max_score = 0

        self.parse(root)

    def parse(self, root):
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "MaximumSummedScore" ):
                self.max_score = int(child.text)
            else:
                raise InvalidTagError(tag)

    def map_score(self, total):
        return( int((total / float(self.max_score)) * 100.0) )

class ScaleMapping(object):
    def __init__(self, root):
        self.multiplier = 1.0
        self.parse(root)

    def parse(self, root):
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "SummedScoreMultiplier" ):
                self.multiplier = float(child.text)
            else:
                raise InvalidTagError(tag)

    def map_score(self, total):
        return( int(total * self.multiplier) )

class SummedScoreRange(object):
    def __init__(self, root):
        self.lowerBound = 0
        self.upperBound = 0
        self.qualValue = 0
        self.parse(root)

    def parse(self, root):
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "InclusiveLowerBound" ):
                self.lowerBound = int(child.text)
            elif ( tag.localname == "InclusiveUpperBound" ):
                self.upperBound = int(child.text)
            elif ( tag.localname == "QualificationValue" ):
                self.qualValue = int(child.text)
            else:
                raise InvalidTagError(tag)

class RangeMapping(object):
    def __init__(self, root):
        self.ranges = []
        self.outofrange = 0

        self.parse(root)

    def parse(self, root):
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "SummedScoreRange" ):
                self.ranges.append(SummedScoreRange(child))
            elif ( tag.localname == "OutOfRangeQualificationValue"):
                self.outofrange = int(child.text)
            else:
                raise InvalidTagError(tag)

    def map_score(self, total):
        for r in self.ranges:
            if ( total <= r.upperBound and total >= r.lowerBound ):
                return( r.qualValue )

        return( self.outofrange )


class QualMapping(object):
    def __init__(self, root):
        self.type = ""
        self.spec = None
        self.parse(root)

    def parse(self, root):
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "PercentageMapping" ):
                self.type = tag.localname
                self.spec = PercMapping(child)
            elif ( tag.localname == "ScaleMapping" ):
                self.type = tag.localname
                self.spec = ScaleMapping(child)
            elif ( tag.localname == "RangeMapping" ):
                self.type = tag.localname
                self.spec = RangeMapping(child)
            else:
                raise InvalidTagError(tag)

    def map_score(self, total):
        return( self.spec.map_score(total) )

class AnswerKey(object):

    def __init__(self, rawContent):
        self.rawContent = rawContent

        self.answers = []
        self.qualmap = None

        q = QuestionValidator()
        testType = etree.QName(q.get_root_element_name(rawContent))
        root = q.parse(testType.localname, rawContent)

        self.parse(root)


    def parse(self, root):

        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "Question" ):
                self.answers.append( QuestionAnswer(child) )
            elif ( tag.localname == "QualificationValueMapping" ):
                self.qualmap = QualMapping(child)
            else:
                raise InvalidTagError(tag)

    def score(self, form):
        """
        Compare the answers submitted by a worker with the
        answer and score it with a qualification value.
        """
        total = 0
        for answer in self.answers:
            try:
                obsVal = form.cleaned_data[answer.ques_id]
                print("Ques[%s]: Answer: %s" % (answer.ques_id, obsVal))
            except KeyError:
                raise Exception("Missing Answer for Question: %s" % answer.ques_id)
            hasMatch = False
            obsSet = set(obsVal)
            for opt in answer.opts:
                expSet = set(opt.sel_id_list)
                if ( expSet == obsSet ):
                    total += opt.score
                    hasMatch = True

            if ( not hasMatch ):
                total += answer.defaultScore

        # Now determine if we need to do a mapping of the score
        if ( self.qualmap is not None ):
            total = self.qualmap.map_score(total)

        return(total)
