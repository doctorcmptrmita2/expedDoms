"""Fix database tables"""
from sqlalchemy import text
from app.core.database import engine

with engine.connect() as conn:
    conn.execute(text("UPDATE alembic_version SET version_num = 'ae3452e56c99'"))
    conn.commit()
    print("Alembic version updated")








