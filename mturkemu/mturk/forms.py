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
    password = forms.CharField(label="Password")
