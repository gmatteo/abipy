"""Context managers"""

import time


class Timer():
    """
    Context manager to time code section.

    .. example::

        with Timer("Timing code section"):
            do_stuff()
    """

    def __init__(self, description):
        self.description = description

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, type, value, traceback):
        self.end = time.time()
        print(f"{self.description}.\n\tCompleted in {self.end - self.start:.4f} seconds\n")
