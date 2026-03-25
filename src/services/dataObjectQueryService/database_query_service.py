"""
Abstract base class for database query services.
All database-specific implementations must subclass this.
"""
from abc import ABC, abstractmethod
from typing import Optional


class DatabaseQueryService(ABC):
    """Abstract base for querying database object metadata across different database engines."""

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection to the database."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the database connection."""

    @abstractmethod
    def list_databases(self) -> list[str]:
        """
        List databases available on this server.
        Returns an empty list for engines where the concept does not apply (e.g. Oracle).
        """

    @abstractmethod
    def list_schemas(self) -> list[str]:
        """List schemas (or owners) available on this server / in the selected database."""

    @abstractmethod
    def search_objects(
        self,
        pattern: str,
        object_type: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> list[dict]:
        """
        Search for database objects whose names or descriptions match *pattern*.

        Implementations should:
        - Auto-add ``%`` wildcards around the pattern.
        - Search both object names and any available description/comment metadata.
        - Return results sorted by relevance (exact → prefix → substring → comment).

        Returns a list of dicts, each with keys:
            schema     : str  — owning schema / database schema
            name       : str  — object name
            type       : str  — e.g. 'TABLE', 'VIEW'
            match_type : str  — one of 'exact', 'prefix', 'substring', 'comment'
        """

    @abstractmethod
    def describe_object(self, object_name: str, schema: Optional[str] = None) -> str:
        """
        Return a formatted, human-readable description of a database object's structure.

        Accepts schema-qualified names (``SCHEMA.OBJECT_NAME``).
        """

    # ------------------------------------------------------------------ #
    # Context-manager support                                              #
    # ------------------------------------------------------------------ #
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
