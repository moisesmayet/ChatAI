import http3
from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend import main
from backend.config import constants
from backend.config.constants import exists_business, get_default_user, get_default_menu
from backend.config.db import match_business_code_local, get_db_conn
from backend.model.model import Agent, Admin
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

dashboard_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@dashboard_app.get('/{business_code}/login', status_code=status.HTTP_200_OK)
async def signin(request: Request, business_code: str):
    if exists_business(business_code):
        language = constants.get_language(constants.lang_code, business_code)
        return templates.TemplateResponse('accounts/login.html', {'request': request, 'language': language, 'business_code': business_code})
    else:
        return RedirectResponse(url=main.dashboard_app.url_path_for('portal'))


@dashboard_app.post('/{business_code}/login', status_code=status.HTTP_200_OK)
async def signin(request: Request, business_code: str):
    form = await request.form()
    form = {field: form[field] for field in form}
    form.pop('login', None)

    base_url = request.base_url
    login_url = main.auth_app.url_path_for('auth_login', business_code=business_code)
    request_url = base_url.__str__() + login_url.__str__()[1:]

    http3client = http3.AsyncClient()
    response = await http3client.post(request_url, data=form)

    language = constants.get_language(constants.lang_code, business_code)

    if response.status_code == 200:
        data = response.json()
        token = data['access_token']

        username = form['username']
        user = get_default_user(business_code, username)

        redirect = get_default_list(business_code)
        redirect.status_code = 302
        redirect.set_cookie('Authorization', f'Bearer {token}')
        if not match_business_code_local(business_code):
            pemission = 'agent'
            if user.agent_staff:
                pemission = 'staff'
            else:
                if user.agent_super:
                    pemission = 'super'
        else:
            pemission = 'admin'
        redirect.set_cookie('Permission', f'{pemission}')
        redirect.set_cookie('UserId', f'{username}')
        redirect.set_cookie('UserLang', language)
        redirect.set_cookie('Menu', get_default_menu(business_code))
        return redirect

    if response.status_code == 500:
        msg = language["servererror"]
    else:
        msg = language["usererror"]

    return templates.TemplateResponse("accounts/login.html", {"request": request, 'language': language, 'business_code': business_code, "msg": msg})


@dashboard_app.get('/', response_class=HTMLResponse)
def portal(request: Request):
    return templates.TemplateResponse("accounts/portal.html", {"request": request})


@dashboard_app.get('/{business_code}/', response_class=HTMLResponse)
def home(business_code: str):
    redirect = get_default_list(business_code)
    return redirect


@dashboard_app.get('/language/{lang}', response_class=HTMLResponse)
def change_language(lang: str, request: Request):
    # Obtener la URL de origen
    redirect_url = request.headers.get("referer")
    redirect = RedirectResponse(url=redirect_url)
    redirect.status_code = 302
    language = constants.get_language(lang)
    redirect.set_cookie('UserLang', language)
    return redirect


@dashboard_app.get('/{business_code}/profile', response_class=HTMLResponse)
async def profile(request: Request, business_code: str):
    permission = request.cookies.get('Permission')
    if permission == 'admin' or permission == 'super':
        user_id = request.cookies.get('UserId')
        if user_id:
            user = get_default_user(business_code, user_id)
            return templates.TemplateResponse('accounts/profile.html', {'request': request, 'user': user, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})

    return RedirectResponse(url=dashboard_app.url_path_for('signin', business_code=business_code))


@dashboard_app.post('/{business_code}/profile', response_class=HTMLResponse)
async def profile(request: Request, business_code: str):
    permission = request.cookies.get('Permission')
    if permission == 'admin' or permission == 'super':
        user_id = request.cookies.get('UserId')
        if user_id:
            form = await request.form()
            form = {field: form[field] for field in form}
            if form['password1'] == '' or form['password2'] == '':
                if form['password1'] == form['password2']:
                    save_user(business_code, user_id, form['username'], bcrypt.hash(form['password1']))
                    return RedirectResponse(url=dashboard_app.url_path_for('signin', business_code=business_code))
                else:
                    msg = f'Passwords do not match'
            else:
                msg = f'Password missing'

        user = get_default_user(business_code, user_id)
        return templates.TemplateResponse('accounts/profile.html', {'request': request, 'user': user, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code, 'msg': msg})

    return RedirectResponse(url=dashboard_app.url_path_for('signin', business_code=business_code))


def get_default_list(business_code):
    if not match_business_code_local(business_code):
        return RedirectResponse(url=main.user_app.url_path_for('users_list', business_code=business_code))
    else:
        return RedirectResponse(url=main.business_app.url_path_for('business_list'))


def save_user(business_code, user_id, user_name, user_password):
    db: Session = get_db_conn(business_code)
    if not match_business_code_local(business_code):
        user = Agent(agent_number=user_id, agent_name=user_name, agent_password=user_password)
    else:
        user = Admin(admin_user=user_id, admin_name=user_name, admin_password=user_password)
    db.merge(user)
    db.commit()
    db.close()
