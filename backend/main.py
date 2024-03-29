from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.router.scheduler.scheduler_router import scheduler_app
from backend.router.admin.admin_router import admin_app
from backend.router.admin.business_router import business_app
from backend.router.auth.auth_router import auth_app
from backend.router.chatai_router import chatai_app
from backend.router.dashboard_router import dashboard_app
from backend.router.user_router import user_app
from backend.router.agent_router import agent_app
from backend.router.behavior_router import behavior_app
from backend.router.order_router import order_app
from backend.router.petition_router import petition_app
from backend.router.parameter_router import parameter_app
from backend.router.topic_router import topic_app
from fastapi.staticfiles import StaticFiles

app = FastAPI(docs_url=None, redoc_url=None)


origins = ['*']


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# System
app.include_router(scheduler_app)

# Admin
app.include_router(admin_app)
app.include_router(business_app)

# Dashboard
app.include_router(auth_app)
app.include_router(chatai_app)
app.include_router(dashboard_app)
app.include_router(user_app)
app.include_router(agent_app)
app.include_router(behavior_app)
app.include_router(order_app)
app.include_router(petition_app)
app.include_router(parameter_app)
app.include_router(topic_app)

app.mount('/static', StaticFiles(directory='./frontend/statics'), name='static')
