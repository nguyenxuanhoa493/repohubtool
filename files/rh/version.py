# -*- coding: utf-8 -*-
"""Single source of truth for the build number.

The build script reads APP_VERSION from here to name the release, and the
updater compares it against the version in the published manifest, so the
constant must stay in sync with the git tag."""

APP_VERSION = "1.72"


def version_tuple(v=None):
    """Split a version string into ints so 1.10 sorts after 1.9.

    Anything unparsable sorts lowest, which makes a malformed manifest look
    older than the running build instead of triggering a bogus update."""
    try:
        return tuple(int(p) for p in str(v or APP_VERSION).strip().lstrip("v").split("."))
    except (TypeError, ValueError):
        return (0,)


def is_newer(remote, local=None):
    """True when *remote* is a strictly later version than *local*."""
    return version_tuple(remote) > version_tuple(local)
