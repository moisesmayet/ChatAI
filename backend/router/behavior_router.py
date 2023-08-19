from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend import main
from backend.router.auth.auth_router import auth_required
from backend.model.model import Behavior
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session

behavior_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@behavior_app.get('/behaviors', response_class=HTMLResponse)
@auth_required
def behaviors_list(request: Request):
    db: Session = get_db_conn()
    behaviors = db.query(Behavior).order_by(Behavior.behavior_code.asc()).all()
    db.close()
    return templates.TemplateResponse('dashboard/behaviors/behaviors.html', {'request': request, 'behaviors': behaviors, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu'))})


@behavior_app.get('/behaviors/view/{behavior_code}', response_class=HTMLResponse)
@auth_required
def behaviors_view(request: Request, behavior_code: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        behaviors = db.query(Behavior).order_by(Behavior.behavior_code.asc()).all()
        behavior = db.query(Behavior).filter(Behavior.behavior_code == behavior_code).first()
        db.close()
        return templates.TemplateResponse('dashboard/behaviors/behaviors_view.html', {'request': request, 'behaviors': behaviors, 'behavior': behavior, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu'))})


@behavior_app.get('/behaviors/new', response_class=HTMLResponse)
async def behaviors_new(request: Request):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        behaviors = db.query(Behavior).order_by(Behavior.behavior_code.asc()).all()
        db.close()
        return templates.TemplateResponse('dashboard/behaviors/behaviors_new.html', {'request': request, 'behaviors': behaviors, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu'))})

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@behavior_app.post('/behaviors/new', response_class=HTMLResponse)
async def behaviors_new(request: Request):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}

        db: Session = get_db_conn()
        new_behavior = Behavior(behavior_code=form['behavior_code'], behavior_description=form['behavior_description'])
        db.add(new_behavior)
        db.commit()
        db.close()

        redirect = RedirectResponse(url=behavior_app.url_path_for('behaviors_list'))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@behavior_app.get('/behaviors/edit/{behavior_code}', response_class=HTMLResponse)
async def behaviors_edit(request: Request, behavior_code: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        behaviors = db.query(Behavior).order_by(Behavior.behavior_code.asc()).all()
        behavior = db.query(Behavior).filter(Behavior.behavior_code == behavior_code).first()
        db.close()
        return templates.TemplateResponse('dashboard/behaviors/behaviors_edit.html', {'request': request, 'behaviors': behaviors, 'behavior': behavior, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu'))})

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@behavior_app.post('/behaviors/edit/{behavior_code}', response_class=HTMLResponse)
async def behaviors_edit(request: Request, behavior_code: str):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}

        db: Session = get_db_conn()
        behavior = Behavior(behavior_code=behavior_code, behavior_description=form['behavior_description'])
        db.merge(behavior)
        db.commit()
        db.close()

        redirect = RedirectResponse(url=behavior_app.url_path_for('behaviors_list'))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@behavior_app.get('/behaviors/delete/{behavior_code}', response_class=HTMLResponse)
async def behaviors_delete(request: Request, behavior_code: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        behaviors = db.query(Behavior).order_by(Behavior.behavior_code.asc()).all()
        behavior = db.query(Behavior).filter(Behavior.behavior_code == behavior_code).first()
        db.close()
        return templates.TemplateResponse('dashboard/behaviors/behaviors_delete.html', {'request': request, 'behaviors': behaviors, 'behavior': behavior, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu'))})

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@behavior_app.post('/behaviors/delete/{behavior_code}', response_class=HTMLResponse)
async def behaviors_delete(request: Request, behavior_code: str):
    if request.cookies.get('Permission') == 'super':
        db: Session = get_db_conn()
        behavior = db.query(Behavior).filter(Behavior.behavior_code == behavior_code).first()
        db.delete(behavior)
        db.commit()
        db.close()

        redirect = RedirectResponse(url=behavior_app.url_path_for('behaviors_list'))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))

