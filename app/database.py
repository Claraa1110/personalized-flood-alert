import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))

def check_db():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("連線成功:", result.fetchone())

        result = conn.execute(text("SELECT PostGIS_Version()"))
        print("PostGIS 版本:", result.fetchone()[0])

if __name__ == "__main__":
    check_db()
