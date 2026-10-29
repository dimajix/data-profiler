"""Generates test data from a profile and loads it into the simulation environment.

The simulation environment stands in for the real database in tests and wherever the tool is
tried out without access to it.
"""


class SimulationError(Exception):
    """Test data that cannot be generated or loaded: what failed, and where."""
