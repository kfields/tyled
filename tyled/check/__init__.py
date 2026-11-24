"""Checking a map as a place: can the people and things in it stand, walk and get in and out?

`check_map` returns a list of `Finding`s, empty when the map is fine; ``tyled check`` prints them.
"""

from tyled.check.checks import CheckError, Finding, check_map

__all__ = ["CheckError", "Finding", "check_map"]
