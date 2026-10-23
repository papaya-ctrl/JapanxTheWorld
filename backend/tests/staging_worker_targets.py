"""Spawn-safe fault target; importing this module never initializes Django."""
import os


def crashed_worker(connection, limits, model_root):
    connection.recv()
    os._exit(7)
