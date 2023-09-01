import subprocess
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.router.auth.auth_router import auth_required
from backend.model.model import Business, generate_random_key
from backend.config.db import get_local_db_conn, get_data_conn
from sqlalchemy.orm import Session

business_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@business_app.get('/admin/business', response_class=HTMLResponse)
@auth_required
def business_list(request: Request):
    db: Session = get_local_db_conn()
    business_all = db.query(Business).order_by(Business.business_code.asc()).all()
    db.close()
    return templates.TemplateResponse('admin/business/business.html',
                                      {'request': request, 'business_all': business_all,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@business_app.get('/admin/business/view/{business_id}', response_class=HTMLResponse)
@auth_required
def business_view(request: Request, business_id: str):
    db: Session = get_local_db_conn()
    business_all = db.query(Business).order_by(Business.business_code.asc()).all()
    business = db.query(Business).filter(Business.business_code == business_id).first()
    db.close()
    return templates.TemplateResponse('admin/business/business_view.html',
                                      {'request': request, 'business_all': business_all, 'business': business,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@business_app.get('/admin/business/new', response_class=HTMLResponse)
async def business_new(request: Request):
    db: Session = get_local_db_conn()
    business_all = db.query(Business).order_by(Business.business_code.asc()).all()
    db.close()
    return templates.TemplateResponse('admin/business/business_new.html',
                                      {'request': request, 'business_all': business_all,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@business_app.post('/admin/business/new', response_class=HTMLResponse)
async def business_new(request: Request):
    form = await request.form()
    form = {field: form[field] for field in form}

    db: Session = get_local_db_conn()
    while True:
        business_code = generate_random_key(30)
        business = db.query(Business).filter(Business.business_code == business_code).first()
        if business is None:
            break

    new_business = Business(business_name=form['business_name'], business_contact=form['business_contact'], business_address=form['business_address'], business_phone=form['business_phone'], business_email=form['business_email'])
    db.add(new_business)
    db.commit()
    db.close()

    created_db(business_code)

    redirect = RedirectResponse(url=business_app.url_path_for('business_list'))
    redirect.status_code = 302
    return redirect


@business_app.get('/admin/business/edit/{business_id}', response_class=HTMLResponse)
async def business_edit(request: Request, business_id: str):
    db: Session = get_local_db_conn()
    business_all = db.query(Business).order_by(Business.business_code.asc()).all()
    business = db.query(Business).filter(Business.business_code == business_id).first()
    db.close()
    return templates.TemplateResponse('admin/business/business_edit.html',
                                      {'request': request, 'business_all': business_all, 'business': business,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@business_app.post('/admin/business/edit/{business_id}', response_class=HTMLResponse)
async def business_edit(request: Request, business_id: str):
    form = await request.form()
    form = {field: form[field] for field in form}

    db: Session = get_local_db_conn()
    business = Business(business_code=business_id, business_description=form['business_description'])
    db.merge(business)
    db.commit()
    db.close()

    redirect = RedirectResponse(url=business_app.url_path_for('business_list'))
    redirect.status_code = 302
    return redirect


@business_app.get('/admin/business/delete/{business_id}', response_class=HTMLResponse)
async def business_delete(request: Request, business_code: str):
    db: Session = get_local_db_conn()
    business_all = db.query(Business).order_by(Business.business_code.asc()).all()
    business = db.query(Business).filter(Business.business_code == business_code).first()
    db.close()

    remove_db(business_code)

    return templates.TemplateResponse('admin/business/business_delete.html',
                                      {'request': request, 'business_all': business_all, 'business': business,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@business_app.post('/admin/business/delete/{business_id}', response_class=HTMLResponse)
async def business_delete(request: Request, business_id: str):
    db: Session = get_local_db_conn()
    business = db.query(Business).filter(Business.business_code == business_id).first()
    db.delete(business)
    db.commit()
    db.close()

    redirect = RedirectResponse(url=business_app.url_path_for('business_list'))
    redirect.status_code = 302
    return redirect


def created_db(business_code):
    try:
        db_config = get_data_conn()
        # Conectarse al servidor PostgreSQL
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # Crear la nueva base de datos
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(business_code)))

        return restore_db()
    except Exception as e:
        return False


def restore_db():
    try:
        restore_command = [
            "pg_restore",
            "--username=usuario",  # Reemplaza con el nombre de usuario de PostgreSQL
            "--dbname=carefullwork",  # Nombre de la nueva base de datos
            "--no-owner",
            "--verbose",
            "--clean",
            "backend/config/chatai_clear.backup",  # Reemplaza con la ruta al archivo chatai.backup
        ]

        # Ejecutar el comando de restauración
        subprocess.run(restore_command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        return False

    except Exception as e:
        return False


def remove_db(business_code):
    try:
        db_config = get_data_conn()
        # Conectar a PostgreSQL
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True  # Establecer el modo de autocommit para ejecutar comandos DDL

        # Crear un cursor
        cursor = conn.cursor()

        # Ejecutar una consulta SQL para eliminar la base de datos
        cursor.execute(f"DROP DATABASE IF EXISTS {business_code}")

        # Cerrar el cursor y la conexión
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        return False
