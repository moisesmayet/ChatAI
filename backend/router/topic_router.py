import os
import re
import shutil

import unicodedata
from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from backend import main
from backend.config.constants import business_constants
from backend.router.auth.auth_router import auth_required
from backend.model.model import Topic, Type
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session

topic_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@topic_app.get('/{business_code}/topics', response_class=HTMLResponse)
@auth_required
def topics_list(request: Request, business_code: str):
    db: Session = get_db_conn(business_code)
    topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
    types = db.query(Type).all()
    db.close()
    return templates.TemplateResponse('dashboard/topics/topics.html', {'request': request, 'topics': topics, 'types': types, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@topic_app.get('/{business_code}/topics/view/{topic_name}', response_class=HTMLResponse)
@auth_required
def topics_view(request: Request, business_code: str, topic_name: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
        topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        types = db.query(Type).all()
        db.close()
        return templates.TemplateResponse('dashboard/topics/topics_view.html', {'request': request, 'topics': topics, 'topic': topic, 'types': types, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@topic_app.get('/{business_code}/topics/files/{topic_name}', response_class=HTMLResponse)
@auth_required
def topics_files(request: Request, business_code: str, topic_name: str):
    db: Session = get_db_conn(business_code)
    topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
    db.close()
    dir_topic = f'{business_constants[business_code]["prompt_dir"]}/{topic_name}'
    topic_files = []
    if os.path.exists(dir_topic):
        topic_files = os.listdir(dir_topic)
    return templates.TemplateResponse('dashboard/topics/topics_files.html', {'request': request, 'topics': topics, 'topic_files': topic_files, 'topic_name': topic_name, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@topic_app.get('/{business_code}/topics/new', response_class=HTMLResponse)
async def topics_new(request: Request, business_code: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
        types = db.query(Type).all()
        db.close()
        return templates.TemplateResponse('dashboard/topics/topics_new.html', {'request': request, 'topics': topics, 'types': types, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@topic_app.post('/{business_code}/topics/new', response_class=HTMLResponse)
async def topics_new(request: Request, business_code: str):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}
        topic_name = process_text(form['topic_name'])
        topic_rebuild = False
        if 'topic_rebuild' in form:
            topic_rebuild = True

        db: Session = get_db_conn(business_code)
        new_topic = Topic(topic_name=topic_name, topic_context=form['topic_context'], topic_order=form['topic_order'], topic_rebuild=topic_rebuild, type_code=form['type_code'])
        db.add(new_topic)
        db.commit()
        db.close()

        redirect = RedirectResponse(url=topic_app.url_path_for('topics_files', topic_name=topic_name, business_code=business_code))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@topic_app.get('/{business_code}/topics/edit/{topic_name}', response_class=HTMLResponse)
async def topics_edit(request: Request, business_code: str, topic_name: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
        topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        types = db.query(Type).all()
        db.close()
        return templates.TemplateResponse('dashboard/topics/topics_edit.html', {'request': request, 'topics': topics, 'topic': topic, 'types': types, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@topic_app.post('/{business_code}/topics/edit/{topic_name}', response_class=HTMLResponse)
async def topics_edit(request: Request, business_code: str, topic_name: str):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}
        topic_rebuild = False
        if 'topic_rebuild' in form:
            topic_rebuild = True

        db: Session = get_db_conn(business_code)
        if 'topic_order' in form:
            topic = Topic(topic_name=topic_name, topic_context=form['topic_context'], topic_order=form['topic_order'], topic_rebuild=topic_rebuild,  type_code=form['type_code'])
        else:
            topic = Topic(topic_name=topic_name, topic_context=form['topic_context'], topic_rebuild=topic_rebuild,  type_code=form['type_code'])
        db.merge(topic)
        db.commit()
        db.close()

        redirect = RedirectResponse(url=topic_app.url_path_for('topics_list', business_code=business_code))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@topic_app.get('/{business_code}/topics/delete/{topic_name}', response_class=HTMLResponse)
async def topics_delete(request: Request, business_code: str, topic_name: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
        topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        types = db.query(Type).all()
        db.close()
        return templates.TemplateResponse('dashboard/topics/topics_delete.html', {'request': request, 'topics': topics, 'topic': topic, 'types': types, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@topic_app.post('/{business_code}/topics/delete/{topic_name}', response_class=HTMLResponse)
async def topics_delete(request: Request, business_code: str, topic_name: str):
    if request.cookies.get('Permission') == 'super':
        db: Session = get_db_conn(business_code)
        topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        db.delete(topic)
        db.commit()
        db.close()

        dir_to_empty = os.path.join(business_constants[business_code]["prompt_dir"], topic_name)
        if os.path.exists(dir_to_empty):
            shutil.rmtree(dir_to_empty)
        dir_to_empty = os.path.join(business_constants[business_code]["index_persist_dir"], topic_name)
        if os.path.exists(dir_to_empty):
            shutil.rmtree(dir_to_empty)

        redirect = RedirectResponse(url=topic_app.url_path_for('topics_list', business_code=business_code))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@topic_app.post("/topics/upload")
async def topics_upload(request: Request, file: UploadFile):
    form = await request.form()
    form = {field: form[field] for field in form}
    topic_name = form['topic_name']
    business_code = form['business_code']

    contents = await file.read()
    directory_path = os.path.join(business_constants[business_code]["prompt_dir"], topic_name)

    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    file_path = os.path.join(directory_path, file.filename)

    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(contents)

    redirect = RedirectResponse(url=topic_app.url_path_for('topics_files', topic_name=topic_name, business_code=business_code))
    redirect.status_code = 302
    return redirect


@topic_app.get("/{business_code}/topics/deletefile/{topic_name}/{file_name}")
async def topics_deletefile(topic_name: str, file_name: str, business_code: str):
    file_path = os.path.join(business_constants[business_code]["prompt_dir"], topic_name, file_name)

    if os.path.exists(file_path):
        os.remove(file_path)

    redirect = RedirectResponse(url=topic_app.url_path_for('topics_files', topic_name=topic_name, business_code=business_code))
    redirect.status_code = 302
    return redirect


@topic_app.get('/{business_code}/topics/download/{topic_name}/{file_name}')
async def topics_download(topic_name: str, file_name: str, business_code: str):
    # Lógica para obtener la ruta completa del archivo
    file_path = os.path.join(business_constants[business_code]["prompt_dir"], topic_name, file_name)

    # Utiliza la clase FileResponse para enviar el archivo al navegador
    return FileResponse(file_path, filename=file_name, media_type='application/octet-stream')


def process_text(input_text):
    # Sustituir espacios por _
    text_no_spaces = input_text.replace(' ', '_')

    # Eliminar caracteres no alfanuméricos y convertir a minúsculas
    text_alphanumeric = re.sub(r'\W', '', text_no_spaces).lower()

    # Remover diacríticos (tildes) y convertir la ñ en n
    text_normalized = unicodedata.normalize('NFKD', text_alphanumeric).encode('ASCII', 'ignore').decode('utf-8')

    return text_normalized
