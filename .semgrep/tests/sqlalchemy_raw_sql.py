from sqlalchemy import text


def get_user_bad(db, user_id):
    # ruleid: sqlalchemy-raw-sql-interpolation
    return db.execute(text(f"SELECT * FROM users WHERE id = {user_id}"))


def get_user_good(db, user_id):
    # ok: sqlalchemy-raw-sql-interpolation
    return db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})
