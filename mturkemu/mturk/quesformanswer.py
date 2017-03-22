# File: mturk/quesformanswer.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the implementation of the code to parse
# a QuestionFormAnswer object from XML into a format
# more easily processed in python.

from mturk.questions import QuestionValidator
from mturk.errors import InvalidTagError

from lxml import etree


class QFormAnswer(object):
    def __init__(self, content):

        self.rawContent = content

        q = QuestionValidator()
        testType = etree.QName(q.get_root_element_name(content))
        root = q.parse(testType.localname, content)

        self.answers = self.parse(root)

    def parse_answer(self, root):
        ret = {}
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "UploadedFileSizeInBytes" ):
                ret[tag.localname] = int(child.text)
            else:
                ret[tag.localname] = child.text

        return(ret)

    def parse(self, root):
        answers = []
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "Answer"):
                answer = self.parse_answer(child)
                answers.append(answer)
            else:
                raise InvalidTagError(tag)

        return(answers)
