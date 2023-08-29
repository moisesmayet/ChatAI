from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.config import constants
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
    admin_whatsapp = form['admin_whatsapp']

    db: Session = get_local_db_conn()
    admin = db.query(Admin).filter(Admin.user_number == admin_user).first()
    admin_ws = db.query(Admin).filter(Admin.user_number != admin_user,
                                      Admin.user_whatsapp == admin_whatsapp).first()
    if admin_ws:
        admin_active = False
        admin_staff = False
        admin_super = False
        if 'admin_active' in form:
            admin_active = True
        if 'admin_staff' in form:
            admin_staff = True
        if 'admin_super' in form:
            admin_super = True

        db: Session = get_local_db_conn()
        admin_password = bcrypt.hash(form['admin_password'])
        new_admin = Admin(admin_user=admin_user, admin_name=form['admin_name'], admin_whatsapp=admin_whatsapp,
                          admin_password=admin_password, admin_active=admin_active, admin_staff=admin_staff,
                          admin_super=admin_super)
        db.add(new_admin)
        db.commit()

        redirect = RedirectResponse(url=admin_app.url_path_for('admins_list'))
        redirect.status_code = 302
        return redirect
    else:
        msg = f'Exists other {constants.alias_expert} with same whatsapp'
        admins = db.query(Admin).order_by(Admin.admin_name.asc()).all()
        return templates.TemplateResponse('admin/admins/admins_new.html', {'request': request, 'admins': admins,
                                                                           'language': eval(
                                                                               request.cookies.get('UserLang')),
                                                                           'menu': eval(request.cookies.get('Menu')),
                                                                           'msg': msg})

    db.close()


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
    admin_whatsapp = form['admin_whatsapp']

    db: Session = get_local_db_conn()
    admin = db.query(Admin).filter(Admin.user_number == admin_user).first()
    admin_ws = db.query(Admin).filter(Admin.user_number != admin_user, Admin.user_whatsapp == admin_whatsapp).first()
    if admin_ws:
        admin_active = False
        admin_staff = False
        admin_super = False
        if 'admin_active' in form:
            admin_active = True
        if 'admin_staff' in form:
            admin_staff = True
        if 'admin_super' in form:
            admin_super = True

        password = form['admin_password']
        if password != '':
            admin_password = bcrypt.hash(password)
        admin.admin_name = form['admin_name']
        admin.admin_whatsapp = admin_whatsapp
        admin.admin_password = admin_password
        admin.admin_active = admin_active
        admin.admin_staff = admin_staff
        admin.admin_super = admin_super
        db.merge(admin)
        db.commit()

        redirect = RedirectResponse(url=admin_app.url_path_for('admins_list'))
        redirect.status_code = 302
        return redirect
    else:
        msg = f'Exists other {constants.alias_expert} with same whatsapp'
        admin_logeado = False
        if admin_user == request.cookies.get('UserId'):
            admin_logeado = True
        admins = db.query(Admin).order_by(Admin.admin_name.asc()).all()
        return templates.TemplateResponse('admin/admins/admins_edit.html',
                                          {'request': request, 'admins': admins, 'admin': admin,
                                           'admin_logeado': admin_logeado,
                                           'constants.alias_expert': constants.alias_expert.capitalize(),
                                           'language': eval(request.cookies.get('UserLang')),
                                           'menu': eval(request.cookies.get('Menu')), 'msg': msg})
    db.close()


@admin_app.get('/admin/admins/delete/{admin_user}', response_class=HTMLResponse)
async def admins_delete(request: Request, admin_user: str):
    db: Session = get_local_db_conn()
    admin_all = db.query(Admin).order_by(Admin.admin_user.asc()).all()
    admin = db.query(Admin).filter(Admin.admin_user == admin_user).first()
    db.close()
    return templates.TemplateResponse('admin/admin/admin_delete.html',
                                      {'request': request, 'admin_all': admin_all, 'admin': admin,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@admin_app.post('/admin/admins/delete/{admin_user}', response_class=HTMLResponse)
async def admins_delete(request: Request, admin_user: str):
    db: Session = get_local_db_conn()
    admin = db.query(Admin).filter(Admin.admin_user == admin_user).first()
    db.delete(admin)
    db.commit()
    db.close()

    redirect = RedirectResponse(url=admin_app.url_path_for('admin_list'))
    redirect.status_code = 302
    return redirect
