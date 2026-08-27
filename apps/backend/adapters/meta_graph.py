"""Shared Meta Graph API configuration.

Keep one pinned version for OAuth, publishing, and replies. Mixing versions makes
an OAuth flow pass while a later publish/reply call fails under different API
semantics, which is especially hard to diagnose during a pilot.
"""

GRAPH_VERSION = "v26.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
