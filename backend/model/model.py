from sqlalchemy import Column, String, Integer, Boolean, Numeric, Text, ForeignKey, DateTime
from datetime import datetime
from backend.config.db import db_conn
from passlib.hash import bcrypt


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


class Log(db_conn):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(10), ForeignKey("orders.order_number"))
    log_status = Column(String(20))
    log_date = Column(DateTime, default=datetime.utcnow)


class Message(db_conn):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    msg_type = Column(String(10))
    user_number = Column(String(254), ForeignKey("users.user_number"))
    msg_sent = Column(Text)
    msg_received = Column(Text)
    msg_code = Column(String(1000))
    msg_date = Column(DateTime, default=datetime.utcnow)
    msg_origin = Column(String(10))


class Order(db_conn):
    __tablename__ = "orders"

    order_number = Column(String(10), primary_key=True, autoincrement=True)
    status_code = Column(String(3), ForeignKey("status.status_code"))
    user_number = Column(String(254), ForeignKey("users.user_number"))
    order_end = Column(DateTime)
    order_start = Column(DateTime, default=datetime.utcnow)


class Parameter(db_conn):
    __tablename__ = "parameters"

    parameter_name = Column(String(10), primary_key=True)
    parameter_value = Column(String(1000))


class Product(db_conn):
    __tablename__ = "products"

    product_code = Column(String(10), primary_key=True)
    product_payment = Column(Numeric(10, 2))
    product_amount = Column(Numeric)
    order_number = Column(String, ForeignKey("orders.order_number"))
    product_price = Column(Numeric(10, 2))
    product_description = Column(String(1000))
    product_measure = Column(String(20))
    product_name = Column(String(20))
    product_offer = Column(String(50))


class Query(db_conn):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True)
    query_code = Column(String(1000))
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
    topic_context = Column(String(1000))
    topic_rebuild = Column(Boolean)
    topic_order = Column(Numeric)
    topic_system = Column(Boolean)


class User(db_conn):
    __tablename__ = "users"

    user_name = Column(String(50))
    user_number = Column(String(254), primary_key=True)
    use_lastmsg = Column(Integer, default=0)
    user_wait = Column(Boolean, default=False)
    user_whatsapp = Column(String(20), default='')
