from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class AdminBase(BaseModel):
    admin_user: str
    admin_name: str
    admin_password: str
    admin_active: bool


class AdminLogin(BaseModel):
    admin_password: str


class AdminDelete(BaseModel):
    admin_user: str


class AdminCreate(AdminBase):
    pass


class AdminUpdate(AdminBase):
    pass


class Admin(AdminBase):
    class Config:
        orm_mode = True


class AgentBase(BaseModel):
    agent_number: str
    agent_name: str
    agent_lastcall: Optional[datetime]
    agent_active: bool
    agent_password = str
    agent_super = bool
    agent_staff = bool
    agent_whatsapp = str


class AgentLogin(BaseModel):
    agent_password = str


class AgentDelete(BaseModel):
    agent_number: int


class AgentCreate(AgentBase):
    pass


class AgentUpdate(AgentBase):
    pass


class Agent(AgentBase):
    class Config:
        orm_mode = True


class BehaviorBase(BaseModel):
    behavior_code: str
    behavior_description: str


class BehaviorCreate(BehaviorBase):
    pass


class Behavior(BehaviorBase):
    class Config:
        orm_mode = True


class BugBase(BaseModel):
    id: Optional[int]
    bug_description: str
    bug_origin: str
    bug_date: Optional[datetime]


class BugCreate(BugBase):
    pass


class Bug(BugBase):
    class Config:
        orm_mode = True


class BusinessBase(BaseModel):
    business_code: str
    business_name: str
    business_contact: str
    business_address: str
    business_phone: str
    business_email: str
    business_enable: bool
    business_create: Optional[datetime]


class BusinessDelete(BaseModel):
    business_code: str


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BusinessBase):
    pass


class Business(BusinessBase):
    class Config:
        orm_mode = True


class LogBase(BaseModel):
    id: Optional[int]
    order_number: str
    log_status: str
    log_date: Optional[datetime]


class LogCreate(LogBase):
    pass


class Log(LogBase):
    class Config:
        orm_mode = True


class MessageBase(BaseModel):
    id: Optional[int]
    msg_type: str
    user_number: str
    msg_received: str
    msg_sent: str
    msg_date: Optional[datetime]
    msg_origin: str
    petition_number: str


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    class Config:
        orm_mode = True


class OrderBase(BaseModel):
    order_number: Optional[str]
    status_code: str
    user_number: str
    order_end: datetime
    order_start: Optional[datetime]


class OrderCreate(OrderBase):
    pass


class Order(OrderBase):
    class Config:
        orm_mode = True


class ParameterBase(BaseModel):
    parameter_name: str
    parameter_value: str


class ParameterCreate(ParameterBase):
    pass


class ParameterUpdate(ParameterBase):
    pass


class Parameter(ParameterBase):
    class Config:
        orm_mode = True


class PetitionBase(BaseModel):
    petition_number: Optional[str]
    topic_name: str
    status_code: str
    petition_name: str
    petition_request: str
    petition_step: str
    petition_stepfrom: str
    petition_steptype: str
    petition_date: datetime
    status_code: str


class PetitionCreate(PetitionBase):
    pass


class Petition(PetitionBase):
    class Config:
        orm_mode = True


class ProductBase(BaseModel):
    product_code: str
    order_number: str
    product_name: str
    product_description: str
    product_offer: str
    product_price: float
    product_payment: float
    product_currency: str
    product_amount: float
    product_measure: str


class ProductDelete(BaseModel):
    product_code: str


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class Product(ProductBase):
    class Config:
        orm_mode = True


class QueryBase(BaseModel):
    id: Optional[int]
    query_sent: str
    query_received: str
    query_date: Optional[datetime]
    query_type: str
    agent_number: str
    query_origin: str


class QueryCreate(QueryBase):
    pass


class Query(QueryBase):
    class Config:
        orm_mode = True


class StatusBase(BaseModel):
    status_code: str
    status_name: str


class StatusCreate(StatusBase):
    pass


class Status(StatusBase):
    class Config:
        orm_mode = True


class TopicBase(BaseModel):
    topic_name: str
    topic_description: str
    topic_context: str
    topic_order: float
    topic_rebuild: bool
    type_code: str


class TopicCreate(TopicBase):
    pass


class Topic(TopicBase):
    class Config:
        orm_mode = True


class TypeBase(BaseModel):
    type_code: str
    type_name: str


class TypeCreate(TypeBase):
    pass


class Type(TypeBase):
    class Config:
        orm_mode = True


class UserBase(BaseModel):
    user_number: str
    user_name: str
    user_lastmsg: int
    user_wait: bool
    user_whatsapp = str


class UserCreate(UserBase):
    pass


class User(UserBase):
    class Config:
        orm_mode = True


class WsidBase(BaseModel):
    id: Optional[int]
    wsid_code: str
    wsid_date: Optional[datetime]


class WsidCreate(UserBase):
    pass


class Wsid(UserBase):
    class Config:
        orm_mode = True
