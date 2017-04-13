# File: mturk/worker/actor.py
# Author: Carl Allendorph
#
# Description:
#    This file contains the implementation of an object that
# encapsulates the actions that a worker actor can take.
#

from mturk.models import *

from mturk.worker.QualsActor import QualsActor
from mturk.worker.TasksActor import TasksActor


class WorkerActor(QualsActor, TasksActor):

    def __init__(self, worker):
        super().__init__(worker)

    # QualsActor and TasksActor define the methods
    # associated with qualifications and tasks, respectively.
    # Below are general purpose Worker methods.

    def get_statistics(self):
        """
        """
        return({
            "earnings" : {
                "tasks" : 0.00,
                "bonuses" : 0.00,
                "total" : 0.00,
            },
            "tasks" : {
                "submitted" : {
                    "count" : 0,
                },
                "approved" : {
                    "count" : 0,
                    "rate" : "0%",
                },
                "rejected" : {
                    "count" : 0,
                    "rate" : "0%",
                },
                "pending" : {
                    "count" : 0,
                }
            },
        })
