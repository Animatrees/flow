from abc import ABC, abstractmethod
from collections.abc import Sequence


class AbstractRepository[IdT, CreateSchema, ReadSchema, UpdateSchema](ABC):
    """Repository contract for generic CRUD persistence.

    Supports:
        - object reads by id
        - full collection reads
        - object creation
        - object updates
        - object deletion
    """

    @abstractmethod
    async def get_by_id(self, id_: IdT) -> ReadSchema | None:
        """Return an object by id, or `None` if it does not exist."""

    @abstractmethod
    async def get_all(self) -> Sequence[ReadSchema]:
        """Return all objects."""

    @abstractmethod
    async def create(self, data: CreateSchema) -> ReadSchema:
        """Create an object."""

    @abstractmethod
    async def update(self, id_: IdT, data: UpdateSchema) -> ReadSchema | None:
        """Update an object, or return `None` if it does not exist."""

    @abstractmethod
    async def delete(self, id_: IdT) -> bool:
        """Delete an object."""
