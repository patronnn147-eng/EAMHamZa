import os
from sqlalchemy import create_engine, inspect


def main():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set")
        return

    # Use sync engine for inspection
    sync_url = url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)
    inspector = inspect(engine)

    columns = inspector.get_columns("ordres_intervention")
    print("Columns in ordres_intervention:")
    for col in columns:
        print(f"- {col['name']}")

    columns_ot = inspector.get_columns("ordres_travail")
    print("\nColumns in ordres_travail:")
    for col in columns_ot:
        print(f"- {col['name']}")


if __name__ == "__main__":
    main()
