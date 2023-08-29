import jwt
from jwt import PyJWTError
from typing import Union
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from functools import wraps
from backend import main
from backend.config.constants import get_default_user, get_default_hash, exists_business, get_default_business_code
from datetime import datetime, timedelta


auth_app = APIRouter()

oauth2_schene = OAuth2PasswordBearer('/token')

templates = Jinja2Templates(directory='./frontend/templates')


def create_token(business_code: str, data: dict, time_expires: Union[datetime, None] = None):
    data_copy = data.copy()
    if time_expires is None:
        expires = datetime.utcnow() + timedelta(minutes=15)
    else:
        expires = datetime.utcnow() + time_expires
    data_copy.update({'exp': expires})

    algorithm_hash = get_default_hash(business_code)
    token = jwt.encode(data_copy, business_code, algorithm=algorithm_hash)
    return token


def verify_token(business_code: str, token: str = Depends(oauth2_schene)):
    if exists_business(business_code):
        try:
            algorithm_hash = get_default_hash(business_code)
            token_decode = jwt.decode(token, business_code, algorithms=[algorithm_hash])
            user_id = token_decode.get('sub')
            if user_id is None:
                raise HTTPException(status_code=402, detail='Credenciales inválidas',
                                    headers={'WWW-Authenticate': 'Bearer'})
        except PyJWTError:
            raise HTTPException(status_code=402, detail='Credenciales inválidas', headers={'WWW-Authenticate': 'Bearer'})

        return user_id
    else:
        raise HTTPException(status_code=402, detail='Credenciales inválidas', headers={'WWW-Authenticate': 'Bearer'})


def verify_token_web(business_code: str, token: str = Depends(oauth2_schene)):
    if exists_business(business_code):
        try:
            algorithm_hash = get_default_hash(business_code)
            token_decode = jwt.decode(token, business_code, algorithms=[algorithm_hash])
            user_id = token_decode.get('sub')
            if user_id is None:
                return ''
        except PyJWTError:
            return ''

        return user_id
    else:
        return ''


def get_enable_agent(business_code: str, token: str = Depends(oauth2_schene)):
    user_id = verify_token(business_code, token)
    if user_id:
        user = get_default_user(business_code, user_id)
        if user:
            return user

    raise HTTPException(status_code=402, detail='Credenciales inválidas', headers={'WWW-Authenticate': 'Bearer'})


def auth_required(router):
    @wraps(router)
    def authorize_cookie(**kwargs):
        token = kwargs['request'].cookies.get('Authorization')
        business_code = kwargs.get('business_code', get_default_business_code())
        if token:
            token_type, jwt_token = token.split(' ')
            agent_number = verify_token_web(business_code, jwt_token)
            if agent_number != '':
                return router(**kwargs)
        return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))
    return authorize_cookie


@auth_app.post('/{business_code}/token')
def auth_login(business_code: str, form_data: OAuth2PasswordRequestForm = Depends()):
    user_id = form_data.username
    user = get_default_user(business_code, user_id)
    if user:
        if user.verify_password(form_data.password):
            token_expires = timedelta(minutes=1440)
            access_token = create_token(business_code, {'sub': user_id}, token_expires)
            token_type = 'bearer'
            return {'access_token': access_token, 'token_type': token_type}

    raise HTTPException(status_code=402, detail='Credenciales inválidas', headers={'WWW-Authenticate': 'Bearer'})


@auth_app.get('/{business_code}/logout', response_class=HTMLResponse)
async def auth_logout(request: Request, business_code: str):
    redirect = get_redirect(request, business_code)
    return redirect


@auth_app.get('/logout', response_class=HTMLResponse)
async def auth_logout_admin(request: Request):
    business_code = get_default_business_code()
    redirect = get_redirect(request, business_code)
    return redirect


def get_redirect(request, business_code):
    redirect = RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))
    redirect.status_code = 302

    token = request.cookies.get('Authorization')
    if token:
        redirect.set_cookie('Authorization', '')
        redirect.set_cookie('Pemission', '')
        redirect.set_cookie('UserId', '')
        redirect.set_cookie('UserLang', '')
        redirect.set_cookie('Menu', '')

    return redirect

