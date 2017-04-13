# File: mturk/quesformanswer.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the implementation of the code to parse
# a QuestionFormAnswer object from XML into a format
# more easily processed in python.

from mturk.xml.questions import QuestionValidator
from mturk.xml.quesform import QuestionForm
from mturk.errors import InvalidTagError

from lxml import etree


class QFormAnswer(object):
    def __init__(self):
        self.answers = None

    def parse_answer(self, root):
        ret = {}
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "SelectionIdentifier" ):
                selList = ret.get(tag.localname, [])
                selList.append(child.text)
                ret[tag.localname] = selList
            elif ( tag.localname == "UploadedFileSizeInBytes" ):
                ret[tag.localname] = int(child.text)
            else:
                ret[tag.localname] = child.text

        if ( "SelectionIdentifier" in ret.keys() ):
            selList = ret["SelectionIdentifier"]
            selStr = " ".join(selList)
            ret["SelectionIdentifier"] = selStr
        return(ret)

    def parse(self, content):

        q = QuestionValidator()
        testType = etree.QName(q.get_root_element_name(content))
        root = q.parse(testType.localname, content)

        answers = []
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "Answer"):
                answer = self.parse_answer(child)
                answers.append(answer)
            else:
                raise InvalidTagError(tag)

        self.answers = answers
        return(answers)

    def encode(self, data):
        """
        Encode an object as an XML QuestionFormAnswer object.
        """
        if ( type(data) == dict ):
            root = self.encode_freetext(data)
        elif ( type(data) == QuestionForm ):
            root = self.encode_quesform(data)
        else:
            raise Exception("Invalid Data Object for Answer Encoding")

        return( self.xml_to_string(root) )

    def xml_to_string(self, root):
        content = etree.tostring(root)
        return(content.decode("utf-8"))

    def encode_freetext(self, data):
        """
        Encode an answer object with simple freetext answers
        only.
        """
        root = etree.Element(
            "QuestionFormAnswers",
            xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd"
            )
        data = {}
        for name,value in data.items():
            if ( name == "assignmentId" ):
                continue

            ans = etree.SubElement(root, "Answer")
            qId = etree.SubElement(ans, "QuestionIdentifier")
            qId.text = name

            content = etree.SubElement(ans, "FreeTextAnswer")
            content.text = value

        return(root)

    def encode_quesform(self, qform):
        """
        Encode the Answers from a question for object.
        """
        questions = qform.get_questions()

        root = etree.Element("QuestionFormAnswers", xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd")

        for question in questions:
            ans = etree.SubElement(root, "Answer")
            qId = etree.SubElement(ans, "QuestionIdentifier")
            qId.text = question.ques_id
            if ( question.answer.type == "FreeTextAnswer" ):
                ftext = etree.SubElement(ans, "FreeText")
                ftext.text = qform.cleaned_data[question.ques_id]
            elif ( question.answer.type == "SelectionAnswer" ):
                selIds = qform.cleaned_data[question.ques_id]
                other = qform.cleaned_data.get("other_" + question.ques_id, None)
                for selId in selIds:
                    selElem = etree.SubElement(ans, "SelectionIdentifier")
                    selElem.text = selId
                if other is not None:
                    otherElem = etree.SubElement(ans, "OtherSelectionText")
                    otherElem.text = other
            elif ( question.answer.type == "FileUploadAnswer" ):
                sizeElem = etree.SubElement(ans, "UploadedFileSizeInBytes")
                sizeElem.text = "0"
                fileKey = etree.SubElement(ans, "UploadedFileKey")
                fileKey.text = "NotImplemented"
            else:
                raise Exception("Invalid Answer Type: %s" % question.answer.type)

        return(root)
