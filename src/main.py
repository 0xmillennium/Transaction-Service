from src import config
config.setup_logger()

import asyncio
import logging
from fastapi import FastAPI
from datetime import datetime, timezone
from contextlib import asynccontextmanager


logger = logging.getLogger("src.main")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Manages the startup and shutdown of the FastAPI application.

    Initializes the ORM, database engine, message bus, blockchain adapter,
    and starts the message consumer. Ensures proper cleanup on application shutdown.
    """
    from src import bootstrap
    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from src.adapters.database import orm
    from src.service_layer import unit_of_work
    from src.adapters.message_broker import connection_manager, publisher, subscriber

    logger.info("Application starting up...")

    orm.init_orm_mappers()


    orm.metadata.create_all(
        bind=create_engine(
            config.get_primary_url(
                is_async=False
            ),
            echo=True
        )
    )

    primary_engine = create_async_engine(
        config.get_primary_url(is_async=True),
        echo=False
    )

    standby_engine = create_async_engine(
        config.get_standby_url(),
        echo=False
    )

    primary_session_factory = async_sessionmaker(bind=primary_engine)
    standby_session_factory = async_sessionmaker(bind=standby_engine)

    puow = unit_of_work.SqlAlchemyUnitOfWork(primary_session_factory)
    suow = unit_of_work.SqlAlchemyUnitOfWork(standby_session_factory)
    conn = connection_manager.RabbitMQConnectionManager(connection_url=config.get_rabbitmq_url())
    pub = publisher.EventPublisher(connection_manager=conn)

    mbus = bootstrap.bootstrap(puow=puow, pub=pub)
    sub = subscriber.EventSubscriber(connection_manager=conn, messagebus=mbus)
    _app.state.messagebus = mbus
    _app.state.conn = conn
    _app.state.suow = suow
    consume_task = asyncio.create_task(sub.start_consuming())


    logger.info("Application started successfully and ready.")
    try:
        yield
    finally:
        logger.info("Application shutting down...")
        await sub.stop_consuming()
        try:
            await asyncio.wait_for(consume_task, timeout=30)
        except asyncio.TimeoutError:
            logger.warning("Consumer task timeout, cancelling...")
            consume_task.cancel()
        await pub.close()
        await conn.close()
        logger.info("Application shut down successfully.")


def create_app():
    """
    Creates and configures the FastAPI application instance.

    Sets up middleware, exception handlers, and includes API routers.

    Returns:
        FastAPI: The configured FastAPI application.
    """
    from src.entrypoints import broker_app, transaction_app
    from src.core.exceptions.exception_handlers import EXCEPTION_HANDLERS
    from src.core.correlation.middleware import CorrelationIdMiddleware
    from src.core.security.middleware import JWTAuthMiddleware

    _app = FastAPI(
        title="Transaction Service API",
        description="Blockchain transaction service for TraderJoe swaps on Avalanche",
        version="1.0.0",
        docs_url="/documentation",
        redoc_url="/api-reference",
        lifespan=lifespan
    )

    _app.add_middleware(CorrelationIdMiddleware)
    _app.add_middleware(JWTAuthMiddleware)

    # Register exception handlers
    for exception_class, handler in EXCEPTION_HANDLERS.items():
        _app.add_exception_handler(exception_class, handler)

    _app.include_router(broker_app.router)
    _app.include_router(transaction_app.router)

    return _app

app = create_app()

@app.get("/", summary="Root endpoint providing basic API information")
async def root():
    """
    Returns basic information about the API, its status, and links to documentation.
    """
    return {
        "message": "Welcome to Transaction Service API!",
        "version": app.version,
        "status": "active",
        "current_time": datetime.now(tz=timezone.utc).isoformat(),
        "documentation_url": "/documentation",
        "github_repo": "to be added:)" # Optional: Link to your API's repository
    }

@app.get("/ping", summary="Ping endpoint providing testability of service.")
async def ping():
    return {"ping": "pong!"}