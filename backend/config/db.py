from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Parámetros de conexión
host = '127.0.0.1'
port = 5432
user = 'postgres'
password = 'postgresuapa'  # 'gvDT332dchGBK'
database = 'chatai_fisiopatologia_db'

# Crea la cadena de conexión
DATABASE_URL = f'postgresql://{user}:{password}@{host}:{port}/{database}'

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_conn = declarative_base()


def get_db_conn():
    # Crea la sesión de la base de datos
    return SessionLocal()
