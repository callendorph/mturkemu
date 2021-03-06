# File: mturk/user.py
# Author: Carl Allendorph
#
# Description:
#  This file contains the implementation of some utilities for the
# mturk User object. This code relates to the creation of the
# worker or requester roles.
#

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from mturk.models import *


import logging
logger = logging.getLogger("mturk")

@receiver(post_save, sender=User, dispatch_uid="mturk_user_creation")
def create_mturk_roles(sender, instance, **kwargs):
    """
    This function creates a new set of worker and requester
    objects for each newly created user.
    """
    if ( not kwargs["created"] ):
        return
    user = instance
    worker = None
    requester = None
    try:
        if ( Requester.objects.filter( user = user ).exists() ):
            logger.error(
                "Requester Object Already exists for User: %s" %
                user.username
            )
        else:
            name = user.get_full_name()
            requester = Requester.objects.create(
                user=user,
                name=name,
                balance=10000.0
            )

        if ( Worker.objects.filter( user = user ).exists() ):
            logger.error(
                "Worker Object Already Exists for User: %s" % user.username
            )
        else:
            worker = Worker.objects.create(user = user)

        logger.info("Created Worker/Requester for User: %s" % user.username)
    except Exception as exc:
        # Cleanup
        if ( worker is not None ):
            worker.delete()
        if ( requester is not None ):
            requester.delete()
        logger.error(
            "Failed to Create Worker/Requester for user[%s]: %s" %
            ( user.username, str(exc))
        )


@receiver(post_save, sender=Worker, dispatch_uid="worker_qual_creation")
def create_worker_quals(sender, instance, **kwargs):
    """
    This method wil create the the system qualification grants for
    the user. These are grants generated by the mturk system
    and updated as the user completes tasks.
    """
    if ( not kwargs["created"] ):
        return

    worker = instance
    qualIds = [ getattr(SystemQualType, x)
                for x in dir(SystemQualType)
                if not x.startswith("_")]

    for qualId in qualIds:

        try:
            qual = Qualification.objects.get(aws_id = qualId, dispose=False)
        except Qualification.DoesNotExist:
            logger.error(
                "Unable to Find Qualification with Id: %s" % qualId
            )
            continue

        createParams = {
            "worker" : worker,
            "qualification" : qual,
            }
        if ( qual.auto_grant_locale is not None ):
            createParams["locale"] = qual.auto_grant_locale
        else:
            createParams["value"] = qual.auto_grant_value

        grant = QualificationGrant.objects.create( **createParams )
