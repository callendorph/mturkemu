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

- Make sure you set the 'endpoint_url="http://localhost:8000/"' arg in your
    mturk boto3 client object
- Make sure to set "verify=False" in your boto3 client because we are
    using http and not https

Example:

```
$> python
>>> import boto3
>>> client = boto3.client(
...   "mturk",
...   aws_access_key_id = ACCESSKEY,
...   aws_secret_access_key = SECRET,
...   verify = False,
...   region_name = "us-east-1",
...   endpoint_url = "http://localhost:8000/"
... )
>>> m.client.get_account_balance()
/.../urllib3/connectionpool.py:768: InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.org/en/latest/security.html
  InsecureRequestWarning)
{
  'ResponseMetadata': {
    'RequestId': '8b1e8e9b-2492-11e7-af9d-875217948510',
    'HTTPStatusCode': 200,
    'RetryAttempts': 0,
    'HTTPHeaders': {
      'content-length': '31',
      'x-amzn-requestid': '8b1e8e9b-2492-11e7-af9d-875217948510',
      'date': 'Tue, 18 Apr 2017 23:55:46 GMT',
      'content-type': 'application/x-amz-json-1.1'
    }
  },
  'AvailableBalance': '10000.00'
}
```

Notes
=======

1.  The 'NextToken' in the list methods for the mturk API is generally
    not the same as the mturk implementation at all. It is actually just
    being used as an offset into the query results. I'm assuming that
    noone who is using the API are using the value of the 'NextToken' for
    anything other than paging.
2.  Currently, the credentials are not being using to authenticate
    requests. They are only used as a weak username.
3.  Notifications via email to workers are not implemented at this point.
4.  I've tested the UI on Chrome in Linux and not much else. Your mileage
    may vary. Currently, the qualifications and tasks management parts
    of the UI are functional for the most part.
5.  A separate API for workers is in the works that would leverage the
    same botocore base with a different service json definition.


Contributing
============

If you would like to contribute, please keep the following in mind:

1.  I'm a human being.
1.  This project is a WIP, so not everything here is going
    to be perfect. The code style is currently not Pep8, there is no
    CI, etc. Try to leave things better than you found them.
2.  This project is intended to fill a need for unit testing and is not
    intended for deployment as a product. As such, I may find a particular
    feature is out of scope for this project. I reserve the sole right to
    make that determination. If in doubt, start a discussion in 'Issues'.
3.  There are unit tests defined in the mturk app to cover the API.
    For new features, unit tests coverage is required. For bug fixes,
    please add a unit test that is labeled to a particular github
    Issue.
4.  Make a pull request. Please reference a github Issue if there is an
    applicable one available. Please use `git rebase` to keep your changes
    at the top of master.
