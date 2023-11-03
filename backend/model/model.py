import random
import string
from sqlalchemy import Column, String, Integer, Boolean, Numeric, Text, ForeignKey, DateTime
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from passlib.hash import bcrypt

# Conexión mediante sqlalchemy
db_conn = declarative_base()


def generate_random_key(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


class Admin(db_conn):
    __tablename__ = "admins"

    admin_user = Column(String(254), primary_key=True)
    admin_name = Column(String(100))
    admin_password = Column(String)
    admin_active = Column(Boolean, default=True)

    def verify_password(self, password: str):
        return bcrypt.verify(password, self.admin_password)


class Agent(db_conn):
    __tablename__ = "agents"

    agent_number = Column(String(254), primary_key=True)
    agent_lastcall = Column(DateTime, default=datetime.utcnow)
    agent_name = Column(String(100))
    agent_active = Column(Boolean)
    agent_password = Column(String)
    agent_super = Column(Boolean, default=False)
    agent_staff = Column(Boolean, default=False)
    agent_whatsapp = Column(String(20), default='')

    def verify_password(self, password: str):
        return bcrypt.verify(password, self.agent_password)


class Behavior(db_conn):
    __tablename__ = "behaviors"

    behavior_code = Column(String(3), primary_key=True)
    behavior_description = Column(Text)


class Bug(db_conn):
    __tablename__ = "bugs"

    id = Column(Integer, primary_key=True)
    bug_description = Column(String(1000))
    bug_origin = Column(String(1000))
    bug_date = Column(DateTime, default=datetime.utcnow)


class Business(db_conn):
    __tablename__ = "business"

    business_code = Column(String(30), primary_key=True, default=generate_random_key(30))
    business_name = Column(String(100))
    business_contact = Column(String(100))
    business_address = Column(Text)
    business_phone = Column(String(20))
    business_email = Column(String(254))
    business_enable = Column(Boolean, default=True)
    business_create = Column(DateTime, default=datetime.utcnow)


class Log(db_conn):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(10), ForeignKey("orders.order_number"))
    log_status = Column(String(20))
    log_date = Column(DateTime, default=datetime.utcnow)


class Message(db_conn):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    msg_type = Column(String(20))
    user_number = Column(String(254), ForeignKey("users.user_number"))
    msg_sent = Column(Text)
    msg_received = Column(Text)
    msg_date = Column(DateTime, default=datetime.utcnow)
    msg_origin = Column(String(10))
    petition_number = Column(String(10), ForeignKey("petitions.petition_number"))


class Order(db_conn):
    __tablename__ = "orders"

    order_number = Column(String(10), primary_key=True, default=generate_random_key(10))
    status_code = Column(String(3), ForeignKey("status.status_code"))
    user_number = Column(String(254), ForeignKey("users.user_number"))
    order_end = Column(DateTime)
    order_start = Column(DateTime, default=datetime.utcnow)


class Parameter(db_conn):
    __tablename__ = "parameters"

    parameter_name = Column(String(10), primary_key=True)
    parameter_value = Column(String(1000))


class Petition(db_conn):
    __tablename__ = "petitions"

    petition_number = Column(String(10), primary_key=True, default=generate_random_key(10))
    user_number = Column(String(254), ForeignKey("users.user_number"))
    topic_name = Column(String, ForeignKey("topics.topic_name"))
    petition_name = Column(String(200))
    petition_request = Column(Text)
    petition_step = Column(String(20))
    petition_stepfrom = Column(String(20))
    petition_steptype = Column(String(10))
    petition_date = Column(DateTime, default=datetime.utcnow)
    status_code = Column(String(3), ForeignKey("status.status_code"))


class Product(db_conn):
    __tablename__ = "products"

    product_code = Column(String(10), primary_key=True)
    order_number = Column(String(10), ForeignKey("orders.order_number"), primary_key=True)
    product_name = Column(String(20))
    product_description = Column(String(1000))
    product_offer = Column(String(50))
    product_price = Column(Numeric(10, 2))
    product_payment = Column(Numeric(10, 2))
    product_currency = Column(String(20))
    product_amount = Column(Numeric)
    product_measure = Column(String(20))


class Query(db_conn):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True)
    query_sent = Column(Text)
    query_received = Column(Text)
    query_date = Column(DateTime, default=datetime.utcnow)
    query_type = Column(String(10))
    agent_number = Column(String(254), ForeignKey("agents.agent_number"))
    query_origin = Column(String(10))


class Status(db_conn):
    __tablename__ = "status"

    status_code = Column(String(3), primary_key=True)
    status_name = Column(String(20))


class Topic(db_conn):
    __tablename__ = "topics"

    topic_name = Column(String, primary_key=True)
    topic_description = Column(String(200))
    topic_context = Column(String(1000))
    topic_order = Column(Numeric)
    topic_rebuild = Column(Boolean)
    type_code = Column(String(3), ForeignKey("types.type_code"))


class Type(db_conn):
    __tablename__ = "types"

    type_code = Column(String(3), primary_key=True)
    type_name = Column(String(20))


class User(db_conn):
    __tablename__ = "users"

    user_name = Column(String(50))
    user_number = Column(String(254), primary_key=True)
    user_lastmsg = Column(Integer, default=0)
    user_lastdate = Column(DateTime, default=datetime.utcnow)
    user_wait = Column(Boolean, default=False)
    user_whatsapp = Column(String(20), default='')


class Wsid(db_conn):
    __tablename__ = "wsids"

    id = Column(Integer, primary_key=True)
    wsid_code = Column(String(1000))
    wsid_date = Column(DateTime, default=datetime.utcnow)
