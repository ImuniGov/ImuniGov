from alembic import context

from backend.db import make_engine, metadata

with make_engine().connect() as connection:
    sqlite = connection.dialect.name == "sqlite"
    if sqlite:
        # Alembic batch rebuilds referenced tables. Restore enforcement after integrity check.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
    context.configure(connection=connection, target_metadata=metadata)
    try:
        with context.begin_transaction():
            context.run_migrations()
            if sqlite and connection.exec_driver_sql("PRAGMA foreign_key_check").first():
                raise RuntimeError(
                    "Migração produziu referência inconsistente; restaure o backup verificado."
                )
    except Exception:
        connection.rollback()
        raise
    else:
        if sqlite:
            connection.commit()
    finally:
        if sqlite:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
