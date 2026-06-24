"""ORM models package.

Every model must be imported here so that ``import app.models`` registers it on
``Base.metadata``. Alembic's ``env.py`` imports this package before autogenerate,
so a model that isn't re-exported here will be invisible to migrations.
"""

from app.models.item import Item

__all__ = ["Item"]
