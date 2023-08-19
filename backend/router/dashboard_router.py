import http3
from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend import main
from backend.config import constants
from backend.model.model import Agent
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

dashboard_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@dashboard_app.get('/login', status_code=status.HTTP_200_OK)
async def signin(request: Request):
    language = constants.get_language(constants.lang_code)
    return templates.TemplateResponse('accounts/login.html', {'request': request, 'language': language})


@dashboard_app.post('/login', status_code=status.HTTP_200_OK)
async def signin(request: Request):
    form = await request.form()
    form = {field: form[field] for field in form}
    form.pop('login', None)

    base_url = request.base_url
    login_url = main.auth_app.url_path_for('auth_login')
    request_url = base_url.__str__() + login_url.__str__()[1:]

    http3client = http3.AsyncClient()
    response = await http3client.post(request_url, data=form)

    language = constants.get_language(constants.lang_code)

    if response.status_code == 200:
        data = response.json()
        token = data['access_token']

        db: Session = get_db_conn()
        username = form['username']
        agent = db.query(Agent).filter(Agent.agent_number == username).first()
        db.close()

        redirect = RedirectResponse(url=main.user_app.url_path_for('users_list'))
        redirect.status_code = 302
        redirect.set_cookie('Authorization', f'Bearer {token}')
        pemission = 'agent'
        if agent.agent_staff:
            pemission = 'staff'
        else:
            if agent.agent_super:
                pemission = 'super'
        redirect.set_cookie('Permission', f'{pemission}')
        redirect.set_cookie('UserId', f'{username}')
        redirect.set_cookie('UserLang', language)
        redirect.set_cookie('Menu', constants.menu)
        return redirect

    if response.status_code == 500:
        msg = 'Issue with the Server'
    else:
        msg = 'Wrong User Id or Password'

    return templates.TemplateResponse("accounts/login.html", {"request": request, 'language': language, "msg": msg})


@dashboard_app.get('/', response_class=HTMLResponse)
def home():
    return RedirectResponse(url=main.user_app.url_path_for('users_list'))


@dashboard_app.get('/language/{lang}', response_class=HTMLResponse)
def change_language(lang: str, request: Request):
    # Obtener la URL de origen
    redirect_url = request.headers.get("referer")
    redirect = RedirectResponse(url=redirect_url)
    redirect.status_code = 302
    language = constants.get_language(lang)
    redirect.set_cookie('UserLang', language)
    return redirect


@dashboard_app.get('/profile', response_class=HTMLResponse)
async def profile(request: Request):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        agent_number = request.cookies.get('UserId')
        if agent_number:
            db: Session = get_db_conn()
            agent = db.query(Agent).filter(Agent.agent_number == agent_number).first()
            db.close()

            return templates.TemplateResponse('accounts/profile.html', {'request': request, 'agent': agent, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu'))})

    return RedirectResponse(url=dashboard_app.url_path_for('signin'))


@dashboard_app.post('/profile', response_class=HTMLResponse)
async def profile(request: Request):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        agent_number = request.cookies.get('UserId')
        if agent_number:
            form = await request.form()
            form = {field: form[field] for field in form}
            if form['password1'] == '' or form['password2'] == '':
                if form['password1'] == form['password2']:
                    db: Session = get_db_conn()
                    agent_password = bcrypt.hash(form['password1'])
                    agent = Agent(agent_number=agent_number, agent_name=form['username'], agent_password=agent_password)
                    db.merge(agent)
                    db.commit()
                    db.close()

                    return RedirectResponse(url=dashboard_app.url_path_for('signin'))
                else:
                    msg = f'Passwords do not match'
            else:
                msg = f'Password missing'

        db: Session = get_db_conn()
        agent = db.query(Agent).filter(Agent.agent_number == agent_number).first()
        db.close()
        return templates.TemplateResponse('accounts/profile.html', {'request': request, 'agent': agent, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'msg': msg})

    return RedirectResponse(url=dashboard_app.url_path_for('signin'))
