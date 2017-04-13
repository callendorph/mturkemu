# File: mturk/xml/questions.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the implementation of code to parse
# the various content that is passed to the CreateHIT method to
# create questions. The idea is to validate the content before
# storage.
#

from django.conf import settings

from mturk.errors import *
from mturk.xml.quesform import *

from lxml import etree

try:
    SCHEMA_FILES = settings.SCHEMAS
except:
    raise Exception("SCHEMAS Dict is not Defined in Settings")


# Load the schemas and cache locally at startup so that
# we can have good response time later

def cache_schemas():
    """
    Parse and cache the XML schemas for the
    various object types.
    """
    ret = {}
    for name in SCHEMA_FILES.keys():
        filepath = SCHEMA_FILES[name]
        with open(filepath, "rb") as f:
            schemaXml = etree.parse(f)
            schema = etree.XMLSchema(schemaXml)
            ret[name] = etree.XMLParser(schema=schema)
    return(ret)

SCHEMAS = cache_schemas()


class HTMLQuestion(object):
    """
    HTMLQuestion XML object for HIT questions.
    """
    def __init__(self, root):

        self.html = ""
        self.height = 0

        self.parse(root)

    def parse(self, root):
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "HTMLContent" ):
                # XML CDATA section is seemless transferred to
                # the child.text
                self.html = child.text
            elif ( tag.localname == "FrameHeight" ):
                self.height = int(child.text)
            else:
                raise InvalidTagError(tag)

class ExternalQuestion(object):
    """
    ExternalQuestion XML object for questions in HITs
    """
    def __init__(self, root):
        self.url = ""
        self.height = 0

        self.parse(root)


    def parse(self, root):
        for child in root:
            tag = etree.QName(child.tag)
            if ( tag.localname == "ExternalURL" ):
                self.url = child.text
            elif ( tag.localname == "FrameHeight" ):
                self.height = int(child.text)
            else:
                raise InvalidTagError(tag)


class QuestionValidator(object):
    """
    """

    def get_root_element_name(self, content):
        # @todo - I want to replace this with a sax parser
        #   so that we don't have to parse the tree twice
        #   to determine the root node name
        root = etree.fromstring(content)
        tag = etree.QName(root.tag)
        return(tag.localname)

    def determine_type(self, content):
        name = self.get_root_element_name(content)
        if ( name not in SCHEMAS.keys() ):
            raise Exception("Unknown Question Type: %s" % name)
        return(name)

    def parse(self, name, content):
        """
        """
        parser = SCHEMAS[name]
        root = etree.fromstring(content, parser)
        return(root)

    def _validate(self, name, content):
        root = self.parse(name, content)
        if ( name == "QuestionForm" ):
            # We need to be a little careful and make sure that the
            # user hasn't tried to insert a key that might clash
            # with our internal form field names.
            ForbiddenKeys = ["csrfmiddlewaretoken"]
            for child in root:
                tag = etree.QName(child.tag)
                if ( tag.localname == "Question" ):
                    for c in child:
                        tag = etree.QName(child.tag)
                        if ( tag.localname == "QuestionIdentifier" ):
                            ques_id = child.text
                            if ( ques_id in ForbiddenKeys ):
                                raise Exception("Invalid Question Identifier: Forbidden Value")
        return( name )

    def validate(self, name, content):
        """
        Validate a question content XML object against
        known schemas and return the name of the xml object.
        Throws an exception is validation fails.
        """
        try:
            name = self._validate(name,content)
        except Exception as exc:
            raise ValidationError(["Invalid XML: %s" % str(exc)])

    def extract(self, content):
        name = self.determine_type(content)
        root = self.parse(name, content)

        if ( name == "ExternalQuestion" ):
            ret = ExternalQuestion(root)
        elif ( name == "HTMLQuestion" ):
            ret = HTMLQuestion(root)
        elif ( name == "QuestionForm" ):
            ret = QuestionForm(root)
        else:
            raise Exception("Unknown XML Object")

        return(name, ret)
