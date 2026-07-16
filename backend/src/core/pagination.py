"""Shared pagination bounds.

One home for page-size defaults and caps so service signatures, repository
defaults, and router ``Query(...)`` params can't drift apart. Changing a value
here changes the API contract — regenerate ``openapi.json`` and the frontend
types (``bun run api:gen``).
"""

# The single default page size for list/paginated endpoints.
DEFAULT_PAGE_SIZE = 10
# The largest page a client may request on a normal endpoint.
MAX_PAGE_SIZE = 100

# Admin / audit-log endpoints page larger for bulk inspection.
ADMIN_DEFAULT_PAGE_SIZE = 100
ADMIN_MAX_PAGE_SIZE = 1000
