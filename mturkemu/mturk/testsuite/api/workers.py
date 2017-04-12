# File: mturk/testsuite/workers.py
# Author: Carl Allendorph
#
# Description:
#   This file contains the implementation of unit tests for the
# worker related API calls.

from mturk.models import *
from mturk.testsuite.utils import RequesterLiveTestCase

class WorkerTests(RequesterLiveTestCase):

    def check_block_list(self, expWorkers, reasons, obsBlocks):
        """
        """
        workerSet = set(expWorkers)

        for block in obsBlocks:
            workerId = block["WorkerId"]
            self.assertTrue( workerId in workerSet )
            expReason = reasons[workerId]
            self.assertEqual(block["Reason"], expReason)
            workerSet.remove(workerId)

        self.assertEqual( len(workerSet), 0 )

    def test_list_blocks(self):

        worker1_client = self.create_new_client("test2")
        worker1 = Worker.objects.get(user__username = "test2")
        worker2_client = self.create_new_client("test3")
        worker2 = Worker.objects.get(user__username = "test3")

        resp = self.client.list_worker_blocks()

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 0)
        blocks = resp["WorkerBlocks"]
        self.assertEqual(len(blocks), 0)

        reasons = {
            worker1.aws_id: "Blarg",
            worker2.aws_id: "Boogy Boogy Boo",
            }

        reason = reasons[worker1.aws_id]
        resp = self.client.create_worker_block(
            WorkerId = worker1.aws_id,
            Reason = reason
            )

        self.is_ok(resp)

        # Check that the block exists.
        resp = self.client.list_worker_blocks()

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 1)
        blocks = resp["WorkerBlocks"]
        self.assertEqual(len(blocks), 1)

        self.check_block_list(
            [ worker1.aws_id ], reasons, blocks
            )

        # Add Worker2 block in

        reason = reasons[worker2.aws_id]
        resp = self.client.create_worker_block(
            WorkerId = worker2.aws_id,
            Reason = reason
            )

        self.is_ok(resp)

        # Check the blocks exist
        resp = self.client.list_worker_blocks()

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 2)
        blocks = resp["WorkerBlocks"]
        self.assertEqual(len(blocks), 2)

        self.check_block_list(
            [ worker1.aws_id, worker2.aws_id ], reasons,
            blocks
            )

        # Attempt to remove the block for worker 1
        resp = self.client.delete_worker_block(
            WorkerId = worker1.aws_id,
            Reason = "Removal of Block"
            )

        self.is_ok(resp)

        # List the blocks looking for worker 2 only
        resp = self.client.list_worker_blocks()

        self.is_ok(resp)

        numResults = resp["NumResults"]
        self.assertEqual(numResults, 1)
        blocks = resp["WorkerBlocks"]
        self.assertEqual(len(blocks), 1)

        self.check_block_list(
            [ worker2.aws_id ], reasons, blocks
            )
