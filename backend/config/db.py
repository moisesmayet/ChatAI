from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from backend.model.model import Business


def get_data_conn():
    # Parámetros de conexión
    host = '127.0.0.1'
    port = 5432
    user = 'postgres'
    password = 'gvDT332dchGBK'  # 'postgresuapa'
    return {'host': host, 'port': port, 'user': user, 'password': password}


def get_session_local(database):
    conn = get_data_conn()

    # Crea la cadena de conexión
    DATABASE_URL = f'postgresql://{conn["user"]}:{conn["password"]}@{conn["host"]}:{conn["port"]}/{database}'

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return SessionLocal()


def load_business(session_local):
    # Crear una conexión
    db: Session = session_local

    business_enables = db.query(Business).filter(Business.business_enable).all()

    # Cerramos la conexión y el cursor
    db.close()

    return business_enables


def create_db_conns(business_enables):
    for item in business_enables:
        db_conn = {'SessionLocal': get_session_local(item.business_code)}
        business_sessions[item.business_code] = db_conn


def get_db_conn(business_code):
    # Crea la sesión de la base de datos
    if business_code != business_code_local:
        return business_sessions[business_code]['SessionLocal']
    else:
        return get_local_db_conn()


def get_local_db_conn():
    # Crea la sesión local de la base de datos
    return business_session_local


def get_business():
    # Crea la sesión de la base de datos
    return business


def match_business_code_local(business_code):
    if business_code_local == business_code:
        return True
    else:
        return False


business_code_local = 'MC0D35D3VCH4T4180100420645CUB4'
business_session_local = get_session_local(business_code_local)
business = load_business(business_session_local)
business_sessions = {}
create_db_conns(business)
