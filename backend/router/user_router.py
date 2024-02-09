import io
import json
import re
import requests
import pandas as pd
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from heyoo import WhatsApp
from datetime import datetime, timedelta
from starlette.responses import StreamingResponse
from backend import main
from backend.config import constants
from backend.router.auth.auth_router import auth_required
from backend.model.model import User, Agent, Message
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session


user_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@user_app.get('/{business_code}/users', response_class=HTMLResponse)
@auth_required
def users_list(request: Request, business_code: str):
    db: Session = get_db_conn(business_code)
    search = request.query_params.get('search', '')
    users = db.query(User).filter(User.user_whatsapp.like(f"%{search}%")).order_by(User.user_lastmsg.desc()).all()
    db.close()
    return templates.TemplateResponse('dashboard/users/users.html', {'request': request, 'users': users, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code, 'search': search})


@user_app.get('/{business_code}/users/view/{user_number}', response_class=HTMLResponse)
@auth_required
def users_view(request: Request, business_code: str, user_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        users = db.query(User).order_by(User.user_lastmsg.desc()).all()
        user = db.query(User).filter(User.user_number == user_number).first()
        db.close()
        return templates.TemplateResponse('dashboard/users/users_view.html', {'request': request, 'users': users, 'user': user, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@user_app.get('/{business_code}/users/messages/{user_number}', response_class=HTMLResponse)
@auth_required
def users_messages(request: Request, business_code: str, user_number: str):
    db: Session = get_db_conn(business_code)
    user = db.query(User).filter(User.user_number == user_number).first()
    last_message = db.query(Message).filter(Message.user_number == user_number).order_by(Message.id.desc()).first()
    if last_message is not None:
        user.user_lastmsg = last_message.id
        user.user_lastdate = datetime.now()
        db.merge(user)
    db.commit()

    users = db.query(User).order_by(User.user_lastmsg.desc()).all()
    user_messages = db.query(Message).filter(Message.user_number == user_number).order_by(Message.id.asc()).all()

    db.close()

    msg_date = last_message.msg_date
    diferencia = datetime.now() - msg_date
    button_start = False
    if diferencia >= timedelta(hours=24):
        button_start = True

    return templates.TemplateResponse('dashboard/users/users_messages.html', {'request': request, 'users': users, 'user_messages': user_messages, 'user_number': user_number, 'user_whatsapp': user.user_whatsapp, 'button_start': button_start, 'button_end': user.user_wait, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@user_app.get('/{business_code}/users/edit/{user_number}', response_class=HTMLResponse)
async def users_edit(request: Request, business_code: str, user_number: str):
    permission = request.cookies.get('Permission')
    db: Session = get_db_conn(business_code)
    users = db.query(User).order_by(User.user_lastmsg.desc()).all()
    user = db.query(User).filter(User.user_number == user_number).first()
    db.close()
    return templates.TemplateResponse('dashboard/users/users_edit.html',
                                      {'request': request, 'users': users, 'user': user,
                                       'alias_user': constants.business_constants[business_code]["alias_user"].capitalize(), 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@user_app.post('/{business_code}/users/edit/{user_number}', response_class=HTMLResponse)
async def users_edit(request: Request, business_code: str, user_number: str):
    permission = request.cookies.get('Permission')
    form = await request.form()
    form = {field: form[field] for field in form}
    user_whatsapp = form['user_whatsapp']

    db: Session = get_db_conn(business_code)
    user = db.query(User).filter(User.user_number == user_number).first()
    user_ws = db.query(User).filter((User.user_number != user_number) & (User.user_whatsapp == user_whatsapp)).first()
    if not user_ws:
        user.user_name = form['user_name']
        user.user_whatsapp = user_whatsapp
        db.merge(user)
        db.commit()

        redirect = RedirectResponse(url=user_app.url_path_for('users_list', business_code=business_code))
        redirect.status_code = 302
        return redirect
    else:
        msg = f'Exists other {constants.business_constants[business_code]["alias_user"]} with same whatsapp'
        users = db.query(User).order_by(User.user_lastmsg.desc()).all()
        return templates.TemplateResponse('dashboard/users/users_edit.html',
                                          {'request': request, 'users': users, 'user': user,
                                           'alias_user': constants.business_constants[business_code]["alias_user"].capitalize(),
                                           'permission': permission, 'language': eval(request.cookies.get('UserLang')),
                                           'menu': eval(request.cookies.get('Menu')), 'business_code': business_code,
                                           'msg': msg})
    db.close()


@user_app.get('/{business_code}/users/marketing', response_class=HTMLResponse)
async def users_marketing(request: Request, business_code: str):
    permission = request.cookies.get('Permission')
    db: Session = get_db_conn(business_code)
    db.close()
    return templates.TemplateResponse('dashboard/users/marketing.html',
                                      {'request': request,
                                       'permission': permission, 'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@user_app.post('/{business_code}/users/marketing', response_class=HTMLResponse)
async def users_marketing(request: Request, business_code: str):
    permission = request.cookies.get('Permission')
    form = await request.form()
    form = {field: form[field] for field in form}
    marketing_users = form['marketing_users']
    marketing_message = form['marketing_message']

    patron = re.compile(r'[\n\r\t,]')
    users_numbers = re.sub(patron, ';', marketing_users)
    users_numbers = re.sub(r';+', ';', users_numbers)
    users_numbers = users_numbers.split(';')
    users_numbers = list(set(users_numbers))
    patron = re.compile(r'^18(09|29|49)\d{7}$')
    invalid_numbers = [numero for numero in users_numbers if not re.match(patron, numero)]

    if len(invalid_numbers) == 0:
        user_id = request.cookies.get('UserId')
        db: Session = get_db_conn(business_code)
        agent = db.query(Agent).filter(Agent.agent_number == user_id).first()
        users_numbers.append(agent.agent_whatsapp)
        db.close()

        for user_number in users_numbers:
            user_number = user_number.strip()
            send_template(agent.agent_name, user_number, marketing_message, "notificacion_marketing", business_code)
            save_message(user_number, marketing_message, False, business_code)

        redirect = RedirectResponse(url=user_app.url_path_for('users_marketing', business_code=business_code))
        redirect.status_code = 302
        return redirect
    else:
        msg = f'Los siguientes números de usuarios no son válidos al formato (1XXXYYYZZZZ): {invalid_numbers}'
        return templates.TemplateResponse('dashboard/users/marketing.html',
                                          {'request': request,
                                           'permission': permission, 'language': eval(request.cookies.get('UserLang')),
                                           'menu': eval(request.cookies.get('Menu')), 'business_code': business_code,
                                           'marketing_users': marketing_users, 'marketing_message': marketing_message,
                                           'msg': msg})


@user_app.get('/{business_code}/users/report/{user_number}', response_class=HTMLResponse)
async def users_report(request: Request, business_code: str, user_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        users = db.query(User).order_by(User.user_lastmsg.desc()).all()
        user = db.query(User).filter(User.user_number == user_number).first()
        db.close()

        fecha_actual = datetime.now()
        # Obtener la fecha inicial del mes actual
        date_from = fecha_actual.replace(day=1).strftime('%d-%m-%Y')
        # Calcular la fecha final del mes actual
        date_to = fecha_actual.replace(day=28) + timedelta(days=4)
        date_to = (date_to - timedelta(days=date_to.day)).strftime('%d-%m-%Y')
        datefilter = f'{date_from} - {date_to}'

        return templates.TemplateResponse('dashboard/users/users_report.html',
                                          {'request': request, 'users': users, 'user': user, 'user_number': user_number, 'datefilter': datefilter,
                                           'alias_user': constants.business_constants[business_code]["alias_user"].capitalize(), 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@user_app.post('/{business_code}/users/report/{user_number}', response_class=HTMLResponse)
async def users_report(request: Request, business_code: str, user_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}
        if 'datefilter' in form:
            datefilter = str(form['datefilter']).split(' - ')
            date_from = datefilter[0].strip()
            date_to = datefilter[1].strip()
            date_from = datetime.strptime(date_from, "%d-%m-%Y")
            date_to = datetime.strptime(date_to, "%d-%m-%Y")

            db: Session = get_db_conn(business_code)
            if user_number != '0':
                messages = db.query(Message).filter((Message.user_number == user_number) & (Message.msg_date >= date_from) & (Message.msg_date <= date_to)).all()
            else:
                messages = db.query(Message).filter((Message.msg_date >= date_from) & (Message.msg_date <= date_to)).order_by(Message.user_number.asc()).all()
            db.close()

            data = []
            for message in messages:
                data.append((message.user_number, message.msg_sent, message.msg_received, message.msg_origin, message.msg_type))

            df = pd.DataFrame(data, columns=['Usuario', 'Enviado', 'Recibido', 'Origen', 'Typo'])
            excel_data = io.BytesIO()
            df.to_excel(excel_data, index=False)

            excel_data.seek(0)  # Mueve el cursor al principio del archivo

            return StreamingResponse(iter([excel_data.getvalue()]),
                                     media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                     headers={"Content-Disposition": "attachment; filename=user_report.xlsx"})

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@user_app.post('/{business_code}/users/send', response_class=HTMLResponse)
async def send_chat(request: Request, business_code: str):
    if request.cookies.get('Permission') == 'staff' or request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}
        chat_msg = form['chat_msg']
        user_number = form['chat_number']
        user_whatsapp = form['chat_whatsapp']

        user_wait = True
        if form['chat_start'] == 'True':
            agent_number = request.cookies.get('UserId')
            db: Session = get_db_conn(business_code)
            agent = db.query(Agent).filter(Agent.agent_number == agent_number).first()
            db.close()
            send_template(agent.agent_name, user_whatsapp, chat_msg, "consentimiento_usuario", business_code)
        else:
            if 'close_chat' in form:
                chat_msg = f'Fue un placer atenderte. Si tienes más consultas o necesitas asistencia en el futuro no dudes en escribir.\n¡Que sigas teniendo un maravilloso día!'
                user_wait = False
            send_text(chat_msg, user_whatsapp, business_code)

        save_message(user_number, chat_msg, user_wait, business_code)

        redirect = RedirectResponse(url=user_app.url_path_for('users_messages', user_number=user_number, business_code=business_code))
        redirect.status_code = 302
        return redirect
    else:
        return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@user_app.get('/{business_code}/{user_number}/refresh_chat')
def refresh_chat(business_code: str, user_number: str):
    content = [{'div_message': '', 'div_class': ''}]
    db: Session = get_db_conn(business_code)

    user = db.query(User).filter(User.user_number == user_number).first()
    if user:
        last_message = db.query(Message).filter(
            (Message.user_number == user_number) &
            (Message.msg_sent != '') &
            (Message.msg_received == '') &
            (Message.id > user.user_lastmsg)
        ).order_by(Message.id.asc()).first()

        if last_message:
            user.user_lastmsg = last_message.id
            user.user_lastdate = datetime.now()
            db.merge(user)
            db.commit()
            content = [{'div_message': last_message.msg_sent, 'div_class': 'user-message'}]
            if last_message.msg_received != '':
                content.append({'div_message': last_message.msg_received, 'div_class': 'chatbot-message'})

    db.close()

    return {'content': content}


def save_message(user_number, chat_msg, user_wait, business_code):
    db: Session = get_db_conn(business_code)
    new_message = Message(user_number=user_number, msg_sent='', msg_received=chat_msg.strip(), msg_type='text', msg_origin='agent', msg_date=datetime.now())
    db.add(new_message)
    db.commit()

    last_message = db.query(Message).filter(Message.user_number == user_number).first()
    user = db.query(User).filter(User.user_number == user_number).first()
    user.user_lastmsg = last_message.id
    user.user_lastdate = datetime.now()
    user.user_wait = user_wait
    db.merge(user)
    db.commit()
    db.close()


def send_text(anwser, numberwa, business_code):
    mensajewa = WhatsApp(constants.business_constants[business_code]["whatsapp_token"], constants.business_constants[business_code]["whatsapp_id"])
    # enviar los mensajes
    mensajewa.send_message(message=anwser, recipient_id=numberwa)


def send_template(agent_name, user_whatsapp, agent_msg, template_name, business_code):
    # url = f'https://graph.facebook.com/v17.0/159540240573780/messages'
    # bearer = f'Bearer EABdgy5ZCsnccBOzrOq9CnnHjHPe9ZBCSJbr4xdsJtqFBFNRXCWKXkQeaiP8gvsZAAGtKZCEnWFzCHALZBEkEgPKJZAAZBjBR0kUIo0GZCZBgJQoOuwmZBacZB33THmuVjZAjVAfY2KU4Iw0ln1G6C3nFKNZBfflLMjmlNxw6hhyVsw81DDoBgLOSEXNcl6am67TO2d6DK'
    url = f'{constants.business_constants[business_code]["whatsapp_url"]}{constants.business_constants[business_code]["whatsapp_id"]}/messages'
    bearer = f'Bearer {constants.business_constants[business_code]["whatsapp_token"]}'

    if template_name == "consentimiento_usuario":
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "to": user_whatsapp,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": "es"
                },
                "components": [
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "text",
                                "text": agent_name
                            }
                        ]
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": agent_msg
                            }
                        ]
                    }
                ]
            }
        })
    else:
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "to": user_whatsapp,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": "es"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": agent_msg
                            }
                        ]
                    }
                ]
            }
        })

    headers = {
        'Content-Type': 'application/json',
        'Authorization': bearer
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    """
    mensajewa = WhatsApp("EABdgy5ZCsnccBOzrOq9CnnHjHPe9ZBCSJbr4xdsJtqFBFNRXCWKXkQeaiP8gvsZAAGtKZCEnWFzCHALZBEkEgPKJZAAZBjBR0kUIo0GZCZBgJQoOuwmZBacZB33THmuVjZAjVAfY2KU4Iw0ln1G6C3nFKNZBfflLMjmlNxw6hhyVsw81DDoBgLOSEXNcl6am67TO2d6DK", "159540240573780")
    # mensajewa = WhatsApp(constants.business_constants[business_code]["whatsapp_token"], constants.business_constants[business_code]["whatsapp_id"])
    componente = '{"type": "header","parameters": [{"type": "text","text": "' + agent_name + '"}]},{"type": "body","parameters": [{"type": "text","text": "' + agent_anwser + '"}]}'
    mensajewa.send_template('consentimiento_usuario', user_whatsapp, components=[componente], lang="es")
    """
