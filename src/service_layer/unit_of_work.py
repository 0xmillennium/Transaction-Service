import abc
from sqlalchemy.orm.session import Session
from src.adapters.database import repository


class AbstractUnitOfWork(abc.ABC):
    """
    Abstract base class for a Unit of Work.

    Manages a business transaction for the transaction service,
    ensuring atomicity and providing a way to collect domain events.
    """

    repo: repository.AbstractRepository

    async def commit(self):
        """
        Commits changes made within the unit of work.
        """
        await self._commit()

    def collect_new_events(self):
        """
        Collects new domain events from tracked aggregates.
        """
        for entity in self.repo.seen:
            while entity.events:
                yield entity.events.pop(0)

    @abc.abstractmethod
    async def _commit(self):
        """
        Abstract method to commit database changes.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self):
        """
        Abstract method to rollback database changes.
        """
        raise NotImplementedError


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """
    SQLAlchemy implementation of the Unit of Work pattern.

    Provides access to all repositories through a single transaction context.
    All new repositories for TokenApproval, ApprovalTransaction, and SwapTransaction
    are accessible through the main repo instance.
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()
        self.repo = repository.SqlAlchemyRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()

    async def _commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()