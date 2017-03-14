# File: mturk/questions.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the implementation of code to parse
# the various content that is passed to the CreateHIT method to
# create questions. The idea is to validate the content before
# storage.
#

from django.conf import settings
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

    def validate(self, name, content):
        """
        Validate a question content XML object against
        known schemas and return the name of the xml object.
        Throws an exception is validation fails.
        """
        parser = SCHEMAS[name]
        root = etree.fromstring(content, parser)
        return( name )
