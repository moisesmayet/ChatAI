from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend import main
from backend.config import constants
from backend.router.auth.auth_router import auth_required
from backend.model.model import Agent, Query
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

agent_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@agent_app.get('/agents', response_class=HTMLResponse)
@auth_required
def agents_list(request: Request):
    db: Session = get_db_conn()
    agents = db.query(Agent).order_by(Agent.agent_name.asc()).all()
    db.close()
    return templates.TemplateResponse('dashboard/agents/agents.html', {'request': request, 'agents': agents, 'agent': '', 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang'))})


@agent_app.get('/agents/view/{agent_number}', response_class=HTMLResponse)
@auth_required
def agents_view(request: Request, agent_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        agents = db.query(Agent).order_by(Agent.agent_name.asc()).all()
        agent = db.query(Agent).filter(Agent.agent_number == agent_number).first()
        db.close()
        return templates.TemplateResponse('dashboard/agents/agents_view.html', {'request': request, 'agents': agents, 'agent': agent, 'permission': permission, 'language': eval(request.cookies.get('UserLang'))})


@agent_app.get('/agents/messages/{agent_number}', response_class=HTMLResponse)
@auth_required
def agents_queries(request: Request, agent_number: str):
    db: Session = get_db_conn()
    agents = db.query(Agent).order_by(Agent.agent_name.asc()).all()
    agent_queries = db.query(Query).filter(Query.agent_number == agent_number).order_by(Query.id.asc()).all()
    db.close()
    return templates.TemplateResponse('dashboard/agents/agents_queries.html', {'request': request, 'agents': agents, 'agent_queries': agent_queries, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang'))})


@agent_app.get('/agents/new', response_class=HTMLResponse)
async def agents_new(request: Request):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        agents = db.query(Agent).order_by(Agent.agent_name.asc()).all()
        db.close()
        return templates.TemplateResponse('dashboard/agents/agents_new.html', {'request': request, 'agents': agents, 'permission': permission, 'language': eval(request.cookies.get('UserLang'))})

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@agent_app.post('/agents/new', response_class=HTMLResponse)
async def agents_new(request: Request):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}
        agent_number = form['agent_number']
        agent_whatsapp = form['agent_whatsapp']

        db: Session = get_db_conn()
        agent = db.query(Agent).filter(Agent.user_number == agent_number).first()
        agent_ws = db.query(Agent).filter(Agent.user_number != agent_number,
                                          Agent.user_whatsapp == agent_whatsapp).first()
        if agent_ws:
            agent_active = False
            agent_staff = False
            agent_super = False
            if 'agent_active' in form:
                agent_active = True
            if 'agent_staff' in form:
                agent_staff = True
            if 'agent_super' in form:
                agent_super = True

            db: Session = get_db_conn()
            agent_password = bcrypt.hash(form['agent_password'])
            new_agent = Agent(agent_number=agent_number, agent_name=form['agent_name'], agent_whatsapp=agent_whatsapp, agent_password=agent_password, agent_active=agent_active, agent_staff=agent_staff, agent_super=agent_super)
            db.add(new_agent)
            db.commit()

            redirect = RedirectResponse(url=agent_app.url_path_for('agents_list'))
            redirect.status_code = 302
            return redirect
        else:
            msg = f'Exists other {constants.alias_expert} with same whatsapp'
            agents = db.query(Agent).order_by(Agent.agent_name.asc()).all()
            return templates.TemplateResponse('dashboard/agents/agents_new.html', {'request': request, 'agents': agents, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'msg': msg})

        db.close()

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@agent_app.get('/agents/edit/{agent_number}', response_class=HTMLResponse)
async def agents_edit(request: Request, agent_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        agent_logeado = False
        if agent_number == request.cookies.get('UserId'):
            agent_logeado = True
        agents = db.query(Agent).order_by(Agent.agent_name.asc()).all()
        agent = db.query(Agent).filter(Agent.agent_number == agent_number).first()
        db.close()
        return templates.TemplateResponse('dashboard/agents/agents_edit.html', {'request': request, 'agents': agents, 'agent': agent, 'agent_logeado': agent_logeado, 'permission': permission, 'language': eval(request.cookies.get('UserLang'))})

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@agent_app.post('/agents/edit/{agent_number}', response_class=HTMLResponse)
async def agents_edit(request: Request, agent_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}
        agent_whatsapp = form['agent_whatsapp']

        db: Session = get_db_conn()
        agent = db.query(Agent).filter(Agent.user_number == agent_number).first()
        agent_ws = db.query(Agent).filter(Agent.user_number != agent_number, Agent.user_whatsapp == agent_whatsapp).first()
        if agent_ws:
            agent_active = False
            agent_staff = False
            agent_super = False
            if 'agent_active' in form:
                agent_active = True
            if 'agent_staff' in form:
                agent_staff = True
            if 'agent_super' in form:
                agent_super = True

            password = form['agent_password']
            if password != '':
                agent_password = bcrypt.hash(password)
            agent.agent_name = form['agent_name']
            agent.agent_whatsapp = agent_whatsapp
            agent.agent_password = agent_password
            agent.agent_active = agent_active
            agent.agent_staff = agent_staff
            agent.agent_super = agent_super
            db.merge(agent)
            db.commit()

            redirect = RedirectResponse(url=agent_app.url_path_for('agents_list'))
            redirect.status_code = 302
            return redirect
        else:
            msg = f'Exists other {constants.alias_expert} with same whatsapp'
            agent_logeado = False
            if agent_number == request.cookies.get('UserId'):
                agent_logeado = True
            agents = db.query(Agent).order_by(Agent.agent_name.asc()).all()
            return templates.TemplateResponse('dashboard/agents/agents_edit.html',
                                              {'request': request, 'agents': agents, 'agent': agent,
                                               'agent_logeado': agent_logeado,
                                               'constants.alias_expert': constants.alias_expert.capitalize(), 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'msg': msg})
        db.close()

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))

