# File: mturk/forms.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the implementation of the forms for the
# mturk app

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from mturk.models import *

def check_user_exists(value):
    if ( User.objects.filter(username = value).exists() ):
        raise ValidationError("User with username[%s] already Exists!" % value)


class UserSignupForm(forms.Form):
    """
    Form for creating a new user
    """
    username = forms.CharField(max_length=150, label="Username", validators=[check_user_exists])
    email = forms.EmailField(required=False, label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput())

class QueryForm(forms.Form):
    """
    This form is for providing a search query for a list
    """
    MAX_QUERY_LEN = 256
    query = forms.CharField(max_length = MAX_QUERY_LEN, label="Query", required=False)

class ListViewForm(forms.Form):
    """
    This form is for allowing lists to be paginated in a template
    """
    offset = forms.IntegerField(min_value=1, required=False)
    count = forms.IntegerField(min_value=1, required=False)

class QualCreateForm(forms.Form):
    """
    This form is for allowing the requester to  make a basic qualification
    through the web interface
    """

    name = forms.CharField(max_length = Qualification.MAX_NAME_LEN, label="Name")
    description = forms.CharField(label="Description", widget=forms.Textarea(attrs={'rows': 4}))
