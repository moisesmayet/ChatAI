from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from heyoo import WhatsApp
from datetime import datetime
from backend import main
from backend.config import constants
from backend.router.auth.auth_router import auth_required
from backend.model.model import User, Message
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session

user_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@user_app.get('/users', response_class=HTMLResponse)
@auth_required
def users_list(request: Request):
    db: Session = get_db_conn()
    users = db.query(User).order_by(User.user_name.asc()).all()
    db.close()
    return templates.TemplateResponse('dashboard/users/users.html', {'request': request, 'users': users, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu'))})


@user_app.get('/users/view/{user_number}', response_class=HTMLResponse)
@auth_required
def users_view(request: Request, user_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        users = db.query(User).order_by(User.user_name.asc()).all()
        user = db.query(User).filter(User.user_number == user_number).first()
        db.close()
        return templates.TemplateResponse('dashboard/users/users_view.html', {'request': request, 'users': users, 'user': user, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu'))})


@user_app.get('/users/messages/{user_number}', response_class=HTMLResponse)
@auth_required
def users_messages(request: Request, user_number: str):
    db: Session = get_db_conn()
    user = db.query(User).filter(User.user_number == user_number).first()
    last_message = db.query(Message).filter(Message.user_number == user_number).order_by(Message.id.desc()).first()
    user.use_lastmsg = last_message.id
    db.merge(user)
    db.commit()

    users = db.query(User).order_by(User.user_name.asc()).all()
    user_messages = db.query(Message).filter(Message.user_number == user_number).order_by(Message.id.asc()).all()

    db.close()
    return templates.TemplateResponse('dashboard/users/users_messages.html', {'request': request, 'users': users, 'user_messages': user_messages, 'user_number': user_number, 'user_whatsapp': user.user_whatsapp, 'button_end': user.user_wait, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu'))})


@user_app.get('/users/edit/{user_number}', response_class=HTMLResponse)
async def users_edit(request: Request, user_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        users = db.query(User).order_by(User.user_name.asc()).all()
        user = db.query(User).filter(User.user_number == user_number).first()
        db.close()
        return templates.TemplateResponse('dashboard/users/users_edit.html',
                                          {'request': request, 'users': users, 'user': user,
                                           'constants.alias_user': constants.alias_user.capitalize(), 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu'))})

    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@user_app.post('/users/edit/{user_number}', response_class=HTMLResponse)
async def users_edit(request: Request, user_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}
        user_whatsapp = form['user_whatsapp']

        db: Session = get_db_conn()
        user = db.query(User).filter(User.user_number == user_number).first()
        user_ws = db.query(User).filter(User.user_number != user_number, User.user_whatsapp == user_whatsapp).first()
        if not user_ws:
            user.user_name = form['user_name']
            user.user_whatsapp = user_whatsapp
            db.merge(user)
            db.commit()

            redirect = RedirectResponse(url=user_app.url_path_for('users_list'))
            redirect.status_code = 302
            return redirect
        else:
            msg = f'Exists other {constants.alias_user} with same whatsapp'
            users = db.query(User).order_by(User.user_name.asc()).all()
            return templates.TemplateResponse('dashboard/users/users_edit.html',
                                              {'request': request, 'users': users, 'user': user,
                                               'constants.alias_user': constants.alias_user.capitalize(), 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')),
                                               'msg': msg})
        db.close()
    return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@user_app.post('/users/send', response_class=HTMLResponse)
async def send_chat(request: Request):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}
        chat_msg = form['chat_msg']
        user_number = form['chat_number']
        user_whatsapp = form['chat_whatsapp']

        current_datetime = datetime.now()
        year = str(current_datetime.year)
        month = str(current_datetime.month).zfill(2)
        day = str(current_datetime.day).zfill(2)
        hour = str(current_datetime.hour).zfill(2)
        minute = str(current_datetime.minute).zfill(2)
        second = str(current_datetime.second).zfill(2)
        microsecond = str(current_datetime.microsecond).zfill(6)
        idwa = f'{user_number}-{year}{month}{day}{hour}{minute}{second}{microsecond}'

        user_wait = True
        if 'close_chat' in form:
            chat_msg = f'Fue un placer atenderte. Si tienes más consultas o necesitas asistencia en el futuro no dudes en escribir.\n¡Que sigas teniendo un maravilloso día!'
            user_wait = False

        send_text(chat_msg, user_whatsapp, idwa)

        db: Session = get_db_conn()

        new_message = Message(user_number=user_number, msg_sent='', msg_received=chat_msg.strip(), msg_code=idwa, msg_type='text', msg_origin='agent', msg_date=datetime.now())
        db.add(new_message)
        db.commit()

        last_message = db.query(Message).filter(Message.user_number == user_number, Message.msg_code == idwa).first()
        user = db.query(User).filter(User.user_number == user_number).first()
        user.use_lastmsg = last_message.id
        user.user_wait = user_wait
        db.merge(user)
        db.commit()

        db.close()

        redirect = RedirectResponse(url=user_app.url_path_for('users_messages', user_number=user_number))
        redirect.status_code = 302
        return redirect
    else:
        return RedirectResponse(main.dashboard_app.url_path_for('signin'))


@user_app.get('/refresh_chat')
def refresh_chat(user_number: str):
    content = [{'div_message': '', 'div_class': ''}]
    db: Session = get_db_conn()

    user = db.query(User).filter(User.user_number == user_number).first()
    if user:
        last_message = db.query(Message).filter(
            Message.user_number == user_number,
            Message.msg_sent != '',
            Message.id > user.use_lastmsg
        ).order_by(Message.id.asc()).first()

        if last_message:
            user.use_lastmsg = last_message.id
            db.merge(user)
            db.commit()
            content = [{'div_message': last_message.msg_sent, 'div_class': 'user-message'}]
            if last_message.msg_received != '':
                content.append({'div_message': last_message.msg_received, 'div_class': 'chatbot-message'})

    db.close()

    return {'content': content}


def send_text(anwser, numberwa, idwa):
    mensajewa = WhatsApp(constants.whasapp_token, constants.whasapp_id)
    # enviar los mensajes
    mensajewa.send_message(message=anwser, recipient_id=numberwa)
    # mensajewa.mark_as_read(idwa)
