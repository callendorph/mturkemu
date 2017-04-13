# File: mturk/quesform.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the implementation of code
# to manage converting a QuestionForm xml object
# into an object that can be fed to the 'quesform' templates
#

from django import forms
from django.core.exceptions import ValidationError

from mturk.errors import *

from lxml import etree


class ContentType(object):
    """
    Overview Content Data from a QuestionForm
    """
    def __init__(self, elem):
        self.type = "ContentType"
        self.content = []
        self.parse(elem)

    def handle_list(self, elem):
        """
        """
        data = {
            "type" : tag.localname,
            "items" : []
        }
        for child in elem:
            data["items"].append(child.text)

        return(data)

    def parse(self, elem):
        """
        Parse the overview element
        """
        for i,child in enumerate(elem):
            tag = etree.QName(child.tag)

            if ( (tag.localname == "Title") or
                 (tag.localname == "Text" ) or
                 (tag.localname == "FormattedContent")
            ):
                self.content.append({
                    "type" : tag.localname,
                    "text" : child.text
                })
            elif ( tag.localname == "List" ):
                data = self.handle_list(child)
                self.content.append(data)
            elif ( tag.localname == "Binary" ):
                self.content.append({
                    "type" : tag.localname,
                })
            elif ( tag.localname == "Application" ):
                self.content.append({
                    "type" : tag.localname,
                })
            elif ( tag.localname == "EmbeddedBinary" ):
                self.content.append({
                    "type" : tag.localname,
                })
            else:
                raise InvalidTagError(tag)

class AnswerFormatRegex(object):
    def __init__(self, elem):
        self.regex = ""
        self.errorText = ""
        self.flags = ""

        self.parse(elem)

    def parse(self, elem):
        for attrName in elem.attrib.keys():
            if ( attrName == "regex" ):
                self.regex = elem.attrib[attrName]
            elif ( attrName == "errorText" ):
                self.errorText = elem.attrib[attrName]
            elif ( attrName == "flags" ):
                self.flags = elem.attrib[attrName]
            else:
                raise InvalidTagError(tag)


class Constraint(object):

    def __init__(self, elem):
        self.is_numeric = False
        self.bounds = {
            "min" : None,
            "max" : None,
            }
        self.length = None
        self.format_regex = None
        self.parse(elem)

    def parse(self, elem):
        for i,child in enumerate(elem):
            tag = etree.QName(child.tag)
            if ( tag.localname == "IsNumeric" ):
                self.is_numeric = (child.text == "true")
                try:
                    minVal = child.attrib["minValue"]
                    self.bounds["min"] = int(minVal)
                except KeyError:
                    pass
                try:
                    maxVal = child.attrib["maxValue"]
                    self.bounds["max"] = int(maxVal)
                except KeyError:
                    pass
            elif ( tag.localname == "Length" ):
                try:
                    minVal = child.attrib["minLength"]
                    self.bounds["min"] = int(minVal)
                except KeyError:
                    pass
                try:
                    maxVal = child.attrib["maxLength"]
                    self.bounds["max"] = int(maxVal)
                except KeyError:
                    pass
            elif ( tag.localname == "AnswerFormatRegex" ):
                self.format_regex = AnswerFormatRegex(child)
            else:
                raise Exception("Invalid Element: %s" % tag.localname)

class FreeTextAnswer(object):
    """
    Free Text Answer
    """
    def __init__(self, elem):
        self.constraint = None
        self.default = ""
        self.num_lines = 1

        self.parse(elem)

    def parse(self, elem):
        for i,child in enumerate(elem):
            tag = etree.QName(child.tag)
            if ( tag.localname == "Constraints" ):
                self.constraint = Constraint(child)
                pass
            elif ( tag.localname == "DefaultText" ):
                self.default = child.text
            elif ( tag.localname =="NumberOfLinesSuggestion" ):
                self.num_lines = int(child.text)
            else:
                raise InvalidTagError(tag)

    def create_fields(self):
        """
        Create the form fields for this answer spec
        """
        rules = self.constraint
        createParams = {}
        if ( rules.is_numeric ):
            if ( rules.bounds["min"] is not None ):
                createParams["min_value"] = rules.bounds["min"]
            if ( rules.bounds["max"] is not None ):
                createParams["max_value"] = rules.bounds["max"]
            field = forms.IntegerField(**createParams)
        elif ( rules.format_regex is not None ):
            if ( len(rules.format_regex.rules) > 0 ):
                raise NotImplementedError("Not Sure About Formatting")
            createParams["regex"] = rules.format_regex.regex
            if ( rules.bounds["min"] is not None ):
                createParams["min_length"] = rules.bounds["min"]
            if ( rules.bounds["max"] is not None ):
                createParams["max_length"] = rules.bounds["max"]
            field = forms.RegexField(**createParams)
        else:
            if ( rules.bounds["min"] is not None ):
                createParams["min_length"] = rules.bounds["min"]
            if ( rules.bounds["max"] is not None ):
                createParams["max_length"] = rules.bounds["max"]

            field = forms.CharField(**createParams)

        return([field])

class Selection(object):
    def __init__(self, elem):
        self.sel_id = ""
        self.data = None

        self.parse(elem)

    def parse(self, elem):
        for i,child in enumerate(elem):
            tag = etree.QName(child.tag)
            if ( tag.localname == "SelectionIdentifier" ):
                self.sel_id = child.text
            elif ( tag.localname == "Text" ):
                self.data = child.text
            elif ( tag.localname == "Binary" ):
                raise NotImplementedError()
            elif ( tag.localname == "FormattedContent" ):
                self.data = child.text
            else:
                raise Exception("Invalid Element: %s" % tag.localname)

class Selections(object):

    def __init__(self, elem):
        self.items = []
        self.other = None

        self.parse(elem)

    def parse(self, elem):
        for i,child in enumerate(elem):
            tag = etree.QName(child.tag)
            if ( tag.localname == "Selection" ):
                self.items.append(Selection(child))
            elif ( tag.localname == "OtherSelection" ):
                self.other = FreeTextAnswer(elem)
            else:
                raise InvalidTagError(tag)

class SelectionAnswer(object):
    """
    Selection from Set Answer
    """
    def __init__(self, elem):
        self.counts = {
            "min" : None,
            "max" : None
        }
        STYLE_TYPES = [
            "radiobutton",
            "checkbox",
            "list",
            "dropdown",
            "combobox",
            "multichooser"
        ]
        self.style = None
        self.selections = None

        self.parse(elem)

    def parse(self, elem):
        for i,child in enumerate(elem):
            tag = etree.QName(child.tag)
            if ( tag.localname == "MinSelectionCount" ):
                self.counts["min"] = int(child.text)
            elif ( tag.localname == "MaxSelectionCount" ):
                self.counts["max"] = int(child.text)
                pass
            elif ( tag.localname == "StyleSuggestion" ):
                self.style = child.text
            elif ( tag.localname == "Selections" ):
                self.selections = Selections( child )
            else:
                raise InvalidTagError(tag)

    def create_fields(self):
        # We are going to use either a "ChoiceField" or a
        # "MultipleChoice Filed depending on the number of
        #  items required.
        minValue = self.counts.get("min", 1)
        maxValue = self.counts.get("max", 1)
        # Set up the choices options
        choices = []
        for item in self.selections.items:
            choices.append( (item.sel_id,item.sel_id) )

        if ( minValue == 1 and maxValue == 1 ):
            field = forms.ChoiceField(choices=choices)
        else:
            field = forms.MultipleChoiceField(choices=choices)

        fields = [field]

        if ( self.selections.other is not None):
            otherFields = self.selections.other.create_fields()
            fields.extend(otherFields)

        return(fields)


class UploadFileAnswer(object):
    def __init__(self, elem):
        self.filesize={
            "max" : None,
            "min" : None,
        }
        self.parse(elem)

    def parse(self, elem):
        for i,child in enumerate(elem):
            tag = etree.QName(child.tag)
            if ( tag.localname == "MaxFileSizeInBytes" ):
                self.filesize["max"] = int( child.text )
            elif ( tag.localname == "MinFileSizeInBytes" ):
                self.filesize["min"] = int( child.text )
            else:
                raise InvalidTagError(tag)

    def create_fields(self):
        field = FileField()
        return( [field] )


class AnswerSpecification(object):
    """
    Answer Specification as part of a question in the QuestionForm
    """
    def __init__(self, elem):
        """
        """
        self.type = ""
        self.spec = None
        self.parse(elem)

    def parse(self, elem):
        for i,child in enumerate(elem):
            tag = etree.QName(child.tag)
            if ( tag.localname == "FreeTextAnswer" ):
                self.type = tag.localname
                self.spec = FreeTextAnswer(child)
            elif ( tag.localname == "SelectionAnswer" ):
                self.type = tag.localname
                self.spec = SelectionAnswer(child)
            elif ( tag.localname == "FileUploadAnswer" ):
                self.type = tag.localname
                self.spec = FileUploadAnswer(child)
            else:
                raise InvalidTagError(tag)

    def create_fields(self):
        """
        Create the fields for this answer specification
        """
        return(self.spec.create_fields())

class Question(object):
    """
    Question Object Data from a QuestionForm
    """
    def __init__(self, elem):
        self.type = "Question"
        self.ques_id = ""
        self.name = ""
        self.is_required = False
        self.content = None
        self.answer = None
        self.parse(elem)
        # Django Field Object
        self.fields = self.create_fields()

    def parse(self, elem):
        """
        Parse a Question object
        """
        for i,child in enumerate(elem):
            tag = etree.QName(child.tag)
            if ( tag.localname == "QuestionIdentifier" ):
                self.ques_id = child.text
            elif ( tag.localname == "DisplayName" ):
                self.name = child.text
            elif ( tag.localname == "IsRequired" ):
                self.is_required = (child.text == "true")
            elif ( tag.localname == "QuestionContent" ):
                obj = ContentType(child)
                self.content = obj
            elif ( tag.localname == "AnswerSpecification" ):
                self.answer = AnswerSpecification(child)
            else:
                raise InvalidTagError(tag)

    def create_fields(self):
        fields = self.answer.create_fields()
        for field in fields:
            if ( self.is_required ):
                field.required = self.is_required
                field.widget.is_required = self.is_required
            field.label = self.name
        ret = {
            self.ques_id : fields[0],
        }
        if ( len(fields) > 1 ):
            ret["other_" + self.ques_id] = fields[1]
        return(ret)


class QuestionForm(object):
    """
    XML QuestionForm object
    """
    def __init__(self, root):

        self.contents = []
        self.parse(root)

        self.cleaned_data = None
        self.errors = None

    def parse(self, root):
        for i,child in enumerate(root):
            tag = etree.QName(child.tag)
            if ( tag.localname == "Overview" ):
                self.contents.append( ContentType(child) )
            elif ( tag.localname == "Question"):
                self.contents.append( Question(child) )
            else:
                raise InvalidTagError(tag)

    def get_questions(self):
        return( [x for x in self.contents if x.type == "Question" ] )

    def get_fields(self):
        fields = {}
        for ques in self.get_questions():
            fields.update( ques.fields)
        return( fields )

    def process(self, data):
        """
        Process the POSTed data by validating all of the fields.
        """
        fields = self.get_fields()

        errors = {}
        cleaned_data = {}

        for name, field in fields.items():
            try:
                value = field.widget.value_from_datadict(data, [], name)
                value = field.clean(value)
                cleaned_data[name] = value
            except ValidationError as exc:
                namedErrors = errors.get(name, [])
                namedErrors.append(exc)
                errors[name] = namedErrors

        self.errors = errors

        self.cleaned_data = cleaned_data
        return(cleaned_data)

    def is_valid(self):
        if ( self.errors is not None ):
            return( len(self.errors.keys()) == 0 )
        else:
            raise Exception("Must call 'process' before invoking is_valid")

    def generate_worker_answer(self):
        """
        Generate the XML-based QuestionFormAnswers object from the
        data that was processed. This gets stored with the request.
        """
        questions = self.get_questions()

        root = etree.Element("QuestionFormAnswers", xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd")

        for question in questions:
            ans = etree.SubElement(root, "Answer")
            qId = etree.SubElement(ans, "QuestionIdentifier")
            qId.text = question.ques_id
            if ( question.answer.type == "FreeTextAnswer" ):
                ftext = etree.SubElement(ans, "FreeText")
                ftext.text = self.cleaned_data[question.ques_id]
            elif ( question.answer.type == "SelectionAnswer" ):
                selIds = self.cleaned_data[question.ques_id]
                other = self.cleaned_data.get("other_" + question.ques_id, None)
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

        # We now have a XML object for our QuestionFormAnswer

        content = etree.tostring(root)

        return(content.decode("utf-8"))
