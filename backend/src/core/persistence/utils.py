"""Utility functions for ID generation and common operations"""

from nanoid import generate


def gen_id(size: int = 12) -> str:
    """
    Generate a compact, URL-safe ID using nanoid.
    A default size of 12 gives ~149 years to have 1% probability of collision
    at 1000 IDs per hour, which is more than enough for our use case.

    Example output: "V1StGXR8_Z5j"
    """
    return generate(size=size)


def gen_short_id(size: int = 8) -> str:
    """Shorter ID for less critical entities. ~2 years at 1000/hour for 1% collision"""
    return generate(size=size)
