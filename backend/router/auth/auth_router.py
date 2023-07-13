import jwt
from jwt import PyJWTError
from typing import Union
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from functools import wraps
from backend import main
from backend.config.constants import openai_api_key, algorithm_hash
from backend.model.model import Agent
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session
from datetime import datetime, timedelta


auth_app = APIRouter()

oauth2_schene = OAuth2PasswordBearer('/token')

templates = Jinja2Templates(directory='./frontend/templates')


def get_agent(agent_number):
    db: Session = get_db_conn()
    agent = db.query(Agent).filter(Agent.agent_number == agent_number).first()
    db.close()
    return agent


def create_token(data: dict, time_expires: Union[datetime, None] = None):
    data_copy = data.copy()
    if time_expires is None:
        expires = datetime.utcnow() + timedelta(minutes=15)
    else:
        expires = datetime.utcnow() + time_expires
    data_copy.update({'exp': expires})

    token = jwt.encode(data_copy, openai_api_key, algorithm=algorithm_hash)
    return token


def verify_token(token: str = Depends(oauth2_schene)):
    try:
        token_decode = jwt.decode(token, openai_api_key, algorithms=[algorithm_hash])
        agent_number = token_decode.get('sub')
        if agent_number is None:
            raise HTTPException(status_code=402, detail='Credenciales inválidas',
                                headers={'WWW-Authenticate': 'Bearer'})
    except PyJWTError:
        raise HTTPException(status_code=402, detail='Credenciales inválidas', headers={'WWW-Authenticate': 'Bearer'})

    return agent_number


def verify_token_web(token: str = Depends(oauth2_schene)):
    try:
        token_decode = jwt.decode(token, openai_api_key, algorithms=[algorithm_hash])
        agent_number = token_decode.get('sub')
        if agent_number is None:
            return ''
    except PyJWTError:
        return ''

    return agent_number


def get_enable_agent(token: str = Depends(oauth2_schene)):
    agent_number = verify_token(token)
    if agent_number:
        agent = get_agent(agent_number)
        if agent:
            return agent

    raise HTTPException(status_code=402, detail='Credenciales inválidas', headers={'WWW-Authenticate': 'Bearer'})


def get_busy_agent(agent: Agent = Depends(get_enable_agent)):
    if not agent.agent_active:
        return agent

    raise HTTPException(status_code=402, detail='Credenciales inválidas', headers={'WWW-Authenticate': 'Bearer'})


def auth_required(router):
    @wraps(router)
    def authorize_cookie(**kwargs):
        token = kwargs['request'].cookies.get('Authorization')
        if token:
            token_type, jwt_token = token.split(' ')
            agent_number = verify_token_web(jwt_token)
            if agent_number != '':
                return router(**kwargs)
        return RedirectResponse(main.dashboard_app.url_path_for('signin'))
    return authorize_cookie


@auth_app.post('/token')
def auth_login(form_data: OAuth2PasswordRequestForm = Depends()):
    agent = get_agent(form_data.username)
    if agent:
        if agent.verify_password(form_data.password):
            token_expires = timedelta(minutes=1440)
            access_token = create_token({'sub': agent.agent_number}, token_expires)
            token_type = 'bearer'
            return {'access_token': access_token, 'token_type': token_type}

    raise HTTPException(status_code=402, detail='Credenciales inválidas', headers={'WWW-Authenticate': 'Bearer'})


@auth_app.get('/logout', response_class=HTMLResponse)
async def auth_logout(request: Request):
    redirect = RedirectResponse(main.dashboard_app.url_path_for('signin'))
    redirect.status_code = 302

    token = request.cookies.get('Authorization')
    if token:
        redirect.set_cookie('Authorization', '')
        redirect.set_cookie('Pemission', '')
        redirect.set_cookie('UserId', '')

    return redirect


@auth_app.get('/auth/me')
def auth_token(agent: Agent = Depends(get_busy_agent)):
    return agent


