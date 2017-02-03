MTurk Emulator
==============

This project contains a django web app that implements a mockup of the
mechanical turk website. The idea is to provide a means of doing
local testing without requiring access to the MTurk Sandbox. This provides
a mechanism to support local unit testing as well as better debug
support.

This project is a work in progress and is not feature complete yet.

IMPORTANT
=========

This project is not intended for production in any way, shape, or form.
It is only intended as a development tool for testing purposes. You would
have to be insane to put this on a public IP. I can't emphasize this enough.

Getting Started
===============

I suggest using pip in virtualenv but you could also install using
pip on your host:

    $> sudo apt-get install python3 virtualenv
    $> virtualenv -p python3 venv
    $> source ./venv/bin/activate
    $> pip install -r requirements.txt

Then setup django (form mturkemu directory):

     $> ./manage.py migrate
     $> ./manage.py createsuperuser
     $> ./manage.py InitMTurkData
     $> ./manage.py collectstatic
     $> ./manage.py runserver

Now you should be able to access the UI from http://localhost:8000/
in your web browser.

Next, to use the MTurk API via boto3, you will need to create an
account via the "Signup" page. Finally, you will need to create an
access credentials set in the "Requester Settings" page. This
credential set you will use the same way that you would use the IAM
credentials in AWS.

Notes when using the API:

- Make sure you set the endpoint_url="http://localhost:8000/" in your
    mturk boto3 client object
- Make sure to set "Verify=False" in your boto3 client because we are
    using http and not https
