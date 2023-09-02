from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.router.auth.auth_router import auth_required
from backend.model.model import Admin
from backend.config.db import get_local_db_conn
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

admin_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@admin_app.get('/admin/admins', response_class=HTMLResponse)
@auth_required
def admins_list(request: Request):
    db: Session = get_local_db_conn()
    admins = db.query(Admin).order_by(Admin.admin_name.asc()).all()
    db.close()
    return templates.TemplateResponse('admin/admins/admins.html', {'request': request, 'admins': admins, 'admin': '',
                                                                   'language': eval(request.cookies.get('UserLang')),
                                                                   'menu': eval(request.cookies.get('Menu'))})


@admin_app.get('/admins/view/{admin_user}', response_class=HTMLResponse)
@auth_required
def admins_view(request: Request, admin_user: str):
    db: Session = get_local_db_conn()
    admins = db.query(Admin).order_by(Admin.admin_name.asc()).all()
    admin = db.query(Admin).filter(Admin.admin_user == admin_user).first()
    db.close()
    return templates.TemplateResponse('admin/admins/admins_view.html',
                                      {'request': request, 'admins': admins, 'admin': admin,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@admin_app.get('/admin/admins/new', response_class=HTMLResponse)
async def admins_new(request: Request):
    db: Session = get_local_db_conn()
    admins = db.query(Admin).order_by(Admin.admin_name.asc()).all()
    db.close()
    return templates.TemplateResponse('admin/admins/admins_new.html', {'request': request, 'admins': admins,
                                                                       'language': eval(
                                                                           request.cookies.get('UserLang')),
                                                                       'menu': eval(request.cookies.get('Menu'))})


@admin_app.post('/admin/admins/new', response_class=HTMLResponse)
async def admins_new(request: Request):
    form = await request.form()
    form = {field: form[field] for field in form}
    admin_user = form['admin_user']

    admin_active = False
    if 'admin_active' in form:
        admin_active = True

    db: Session = get_local_db_conn()
    admin_password = bcrypt.hash(form['admin_password'])
    new_admin = Admin(admin_user=admin_user, admin_name=form['admin_name'],
                      admin_password=admin_password, admin_active=admin_active)
    db.add(new_admin)
    db.commit()
    db.close()

    redirect = RedirectResponse(url=admin_app.url_path_for('admins_list'))
    redirect.status_code = 302
    return redirect


@admin_app.get('/admin/admins/edit/{admin_user}', response_class=HTMLResponse)
async def admins_edit(request: Request, admin_user: str):
    db: Session = get_local_db_conn()
    admin_logeado = False
    if admin_user == request.cookies.get('UserId'):
        admin_logeado = True
    admins = db.query(Admin).order_by(Admin.admin_name.asc()).all()
    admin = db.query(Admin).filter(Admin.admin_user == admin_user).first()
    db.close()
    return templates.TemplateResponse('admin/admins/admins_edit.html',
                                      {'request': request, 'admins': admins, 'admin': admin,
                                       'admin_logeado': admin_logeado,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@admin_app.post('/admin/admins/edit/{admin_user}', response_class=HTMLResponse)
async def admins_edit(request: Request, admin_user: str):
    form = await request.form()
    form = {field: form[field] for field in form}

    db: Session = get_local_db_conn()
    admin = db.query(Admin).filter(Admin.admin_user == admin_user).first()

    admin_active = False
    if 'admin_active' in form:
        admin_active = True

    admin.admin_name = form['admin_name']
    admin.admin_active = admin_active
    db.merge(admin)
    db.commit()
    db.close()

    redirect = RedirectResponse(url=admin_app.url_path_for('admins_list'))
    redirect.status_code = 302
    return redirect


@admin_app.get('/admin/admins/password/{admin_user}', response_class=HTMLResponse)
async def admins_password(request: Request, admin_user: str):
    db: Session = get_local_db_conn()
    admin_logeado = False
    if admin_user == request.cookies.get('UserId'):
        admin_logeado = True
    admins = db.query(Admin).order_by(Admin.admin_name.asc()).all()
    admin = db.query(Admin).filter(Admin.admin_user == admin_user).first()
    db.close()
    return templates.TemplateResponse('admin/admins/admins_password.html',
                                      {'request': request, 'admins': admins, 'admin': admin,
                                       'admin_logeado': admin_logeado,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@admin_app.post('/admin/admins/password/{admin_user}', response_class=HTMLResponse)
async def admins_password(request: Request, admin_user: str):
    form = await request.form()
    form = {field: form[field] for field in form}

    password1 = form['admin_password1']
    password2 = form['admin_password2']

    db: Session = get_local_db_conn()
    admin = db.query(Admin).filter(Admin.admin_user == admin_user).first()
    if password1 != '' and password1 == password2:
        if password1 != '':
            admin_password = bcrypt.hash(password1)
        admin.admin_password = admin_password
        db.merge(admin)
        db.commit()

        redirect = RedirectResponse(url=admin_app.url_path_for('admins_list'))
        redirect.status_code = 302
        return redirect
    else:
        msg = f'Passwords do not match'

        admin_logeado = False
        if admin_user == request.cookies.get('UserId'):
            admin_logeado = True
        admins = db.query(Admin).order_by(Admin.admin_name.asc()).all()
    db.close()
    return templates.TemplateResponse('admin/admins/admins_password.html',
                                      {'request': request, 'admins': admins, 'admin': admin,
                                       'admin_logeado': admin_logeado,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu')), 'msg': msg})


@admin_app.get('/admin/admins/delete/{admin_user}', response_class=HTMLResponse)
async def admins_delete(request: Request, admin_user: str):
    db: Session = get_local_db_conn()
    admins = db.query(Admin).order_by(Admin.admin_user.asc()).all()
    admin = db.query(Admin).filter(Admin.admin_user == admin_user).first()
    db.close()
    return templates.TemplateResponse('admin/admins/admins_delete.html',
                                      {'request': request, 'admins': admins, 'admin': admin,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@admin_app.post('/admin/admins/delete/{admin_user}', response_class=HTMLResponse)
async def admins_delete(request: Request, admin_user: str):
    db: Session = get_local_db_conn()
    admin = db.query(Admin).filter(Admin.admin_user == admin_user).first()
    db.delete(admin)
    db.commit()
    db.close()

    redirect = RedirectResponse(url=admin_app.url_path_for('admins_list'))
    redirect.status_code = 302
    return redirect
