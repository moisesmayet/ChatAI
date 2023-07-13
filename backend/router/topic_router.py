import os
from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from backend import main
from backend.config import constants
from backend.router.auth.auth_router import auth_required
from backend.model.model import Topic
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session

topic_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@topic_app.get('/topics', response_class=HTMLResponse)
@auth_required
def topics_list(request: Request):
    db: Session = get_db_conn()
    topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
    db.close()
    return templates.TemplateResponse('dashboard/topics/topics.html', {'request': request, 'topics': topics, 'permission': request.cookies.get('Permission'), 'language': constants.language})


@topic_app.get('/topics/view/{topic_name}', response_class=HTMLResponse)
@auth_required
def topics_view(request: Request, topic_name: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
        topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        db.close()
        return templates.TemplateResponse('dashboard/topics/topics_view.html', {'request': request, 'topics': topics, 'topic': topic, 'permission': permission, 'language': constants.language})


@topic_app.get('/topics/files/{topic_name}', response_class=HTMLResponse)
@auth_required
def topics_files(request: Request, topic_name: str):
    db: Session = get_db_conn()
    topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
    db.close()
    dir_topic = f'backend/prompt/{topic_name}'
    topic_files = []
    if os.path.exists(dir_topic):
        topic_files = os.listdir(dir_topic)
    return templates.TemplateResponse('dashboard/topics/topics_files.html', {'request': request, 'topics': topics, 'topic_files': topic_files, 'topic_name': topic_name, 'permission': request.cookies.get('Permission'), 'language': constants.language})


@topic_app.get('/topics/new', response_class=HTMLResponse)
async def topics_new(request: Request):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
        db.close()
        return templates.TemplateResponse('dashboard/topics/topics_new.html', {'request': request, 'topics': topics, 'permission': permission, 'language': constants.language})

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@topic_app.post('/topics/new', response_class=HTMLResponse)
async def topics_new(request: Request):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}

        topic_system = False
        topic_rebuild = False
        if 'topic_system' in form:
            topic_system = True
        if 'topic_rebuild' in form:
            topic_rebuild = True

        db: Session = get_db_conn()
        new_topic = Topic(topic_name=form['topic_name'], topic_context=form['topic_context'], topic_order=form['topic_order'], topic_rebuild=topic_rebuild, topic_system=topic_system)
        db.add(new_topic)
        db.commit()
        db.close()

        redirect = RedirectResponse(url=topic_app.url_path_for('topics_list'))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@topic_app.get('/topics/edit/{topic_name}', response_class=HTMLResponse)
async def topics_edit(request: Request, topic_name: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        topics = db.query(Topic).order_by(Topic.topic_order.asc()).all()
        topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        db.close()
        return templates.TemplateResponse('dashboard/topics/topics_edit.html', {'request': request, 'topics': topics, 'topic': topic, 'permission': permission, 'language': constants.language})

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@topic_app.post('/topics/edit/{topic_name}', response_class=HTMLResponse)
async def topics_edit(request: Request, topic_name: str):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}

        topic_system = False
        topic_rebuild = False
        if 'topic_system' in form:
            topic_system = True
        if 'topic_rebuild' in form:
            topic_rebuild = True

        db: Session = get_db_conn()
        topic = Topic(topic_name=topic_name, topic_context=form['topic_context'], topic_order=form['topic_order'], topic_rebuild=topic_rebuild, topic_system=topic_system)
        db.merge(topic)
        db.commit()
        db.close()

        redirect = RedirectResponse(url=topic_app.url_path_for('topics_list'))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@topic_app.get('/topics/delete/{topic_name}', response_class=HTMLResponse)
async def topics_delete(request: Request, topic_name: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        topics = db.query(Topic).all()
        topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        db.close()
        return templates.TemplateResponse('dashboard/topics/topics_delete.html', {'request': request, 'topics': topics, 'topic': topic, 'permission': permission, 'language': constants.language})

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@topic_app.post('/topics/delete/{topic_name}', response_class=HTMLResponse)
async def topics_delete(request: Request, topic_name: str):
    if request.cookies.get('Permission') == 'super':
        db: Session = get_db_conn()
        topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
        db.delete(topic)
        db.commit()
        db.close()

        dir_to_empty = os.path.join("backend", "prompt", topic_name)
        empty_dir(dir_to_empty)
        dir_to_empty = os.path.join("backend", "data_index", topic_name)
        empty_dir(dir_to_empty)

        redirect = RedirectResponse(url=topic_app.url_path_for('topics_list'))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@topic_app.post("/topics/upload")
async def topics_upload(request: Request, file: UploadFile):
    form = await request.form()
    form = {field: form[field] for field in form}
    topic_name = form['topic_name']

    contents = await file.read()
    directory_path = os.path.join("backend", "prompt", topic_name)

    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    file_path = os.path.join(directory_path, file.filename)

    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(contents)

    redirect = RedirectResponse(url=topic_app.url_path_for('topics_files', topic_name=topic_name))
    redirect.status_code = 302
    return redirect


@topic_app.get("/topics/deletefile/{topic_name}/{file_name}")
async def topics_deletefile(topic_name: str, file_name: str):
    file_path = os.path.join("backend", "prompt", topic_name, file_name)

    if os.path.exists(file_path):
        os.remove(file_path)

    redirect = RedirectResponse(url=topic_app.url_path_for('topics_files', topic_name=topic_name))
    redirect.status_code = 302
    return redirect


@topic_app.get('/topics/download/{topic_name}/{file_name}')
async def topics_download(topic_name: str, file_name: str):
    # Lógica para obtener la ruta completa del archivo
    file_path = os.path.join("backend", "prompt", topic_name, file_name)

    # Utiliza la clase FileResponse para enviar el archivo al navegador
    return FileResponse(file_path, filename=file_name, media_type='application/octet-stream')


def empty_dir(dir_to_empty):
    files = os.listdir(dir_to_empty)
    for file in files:
        # Ruta completa del archivo
        file_url = os.path.join(dir_to_empty, file)
        # Verificar si es un archivo
        if os.path.isfile(file_url):
            # Eliminar el archivo
            os.remove(file_url)
    os.rmdir(dir_to_empty)
