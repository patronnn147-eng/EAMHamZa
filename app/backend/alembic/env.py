#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Desc   :

import asyncio
import importlib
import os
import pkgutil
from logging.config import fileConfig

import models
from alembic import context
from core.database import Base
from sqlalchemy import pool, create_engine
from sqlalchemy.ext.asyncio import create_async_engine

# Automatically import all ORM models under Models
for _, module_name, _ in pkgutil.iter_modules(models.__path__):
    importlib.import_module(f"{models.__name__}.{module_name}")

config = context.config

database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def alembic_include_object(object, name, type_, reflected, compare_to):
    # type_ can be 'table', 'index', 'column', 'constraint'
    # ignore particular table_name
    return True


def run_migrations_online_sync(db_url):
    """Run migrations in 'online' mode using a synchronous engine."""
    connectable = create_engine(
        db_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=alembic_include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


async def run_migrations_online_async(db_url):
    """Run migrations in 'online' mode using an asynchronous engine."""
    connectable = create_async_engine(db_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
                include_object=alembic_include_object,
            )
        )
        async with connection.begin():
            await connection.run_sync(lambda sync_conn: context.run_migrations())
    await connectable.dispose()


def run_migrations():
    db_url = config.get_main_option("sqlalchemy.url")
    if not db_url:
        raise RuntimeError("Alembic sqlalchemy.url is empty and DATABASE_URL is not set")
    
    if "asyncpg" in db_url:
        asyncio.run(run_migrations_online_async(db_url))
    else:
        run_migrations_online_sync(db_url)


run_migrations()
