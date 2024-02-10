import json
import requests
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_utilities import repeat_at
from datetime import datetime, timedelta
from backend.config.db import get_db_conn
from backend.router.auth.auth_router import auth_required
from sqlalchemy.orm import Session
from backend.model.model import User, Message
from backend.config import constants
from backend.router.user_router import user_app

scheduler_app = APIRouter()


@scheduler_app.get('/{business_code}/today', response_class=HTMLResponse)
@auth_required
def scheduler_today(request: Request, business_code: str):
    send_notification()

    response = RedirectResponse(url=user_app.url_path_for('users_list', business_code=business_code))
    response.set_cookie(key='message', value='Reporte enviado')

    return response


@scheduler_app.on_event('startup')
@repeat_at(cron="0 8 * * *")
async def scheduler_daily():
    send_notification()


def send_notification():
    # Obtener la fecha actual y calcular la fecha del día anterior
    fecha_actual = datetime.now()
    fecha_anterior = fecha_actual - timedelta(days=1)

    # Convertir las fechas a formato string (YYYY-MM-DD) para comparación en la consulta
    fecha_actual_str = fecha_actual.strftime("%Y-%m-%d")
    fecha_anterior_str = fecha_anterior.strftime("%Y-%m-%d")

    for business in constants.business_notification:
        db: Session = get_db_conn(business.business_code)

        # Usuarios que escribieron el día anterior
        users = db.query(User).filter(
            User.user_lastdate >= fecha_anterior_str,
            User.user_lastdate < fecha_actual_str
        ).count()

        # Mensages enviados el día anterior
        messages = db.query(Message).filter(
            Message.msg_date >= fecha_anterior_str,
            Message.msg_date < fecha_actual_str
        ).count()

        db.close()

        language = constants.get_language(constants.lang_code, business.business_code)

        business_users = f'Ningún {str(language["user"]).lower()} se contactó con el chatbot.'
        business_messages = f'No se respondieron mensajes'
        if users > 0:
            if users > 1:
                business_users = f'{users} {str(language["users"]).lower()} estuvieron interactuando con el chatbot.'
            else:
                business_users = f'Solo un {str(language["user"]).lower()} interactuó con el chatbot.'

            if messages > 1:
                business_messages = f'Se respondieron aproximandemente {messages} mensajes.'
            else:
                business_messages = f'Se respondió un solo mensaje.'

        send_template(business.business_contact, business.business_phone, business_users, business_messages, business.business_code)


def send_template(agent_name, agent_whatsapp, text_users, text_messages, business_code):
    # url = f'https://graph.facebook.com/v17.0/159540240573780/messages'
    # bearer = f'Bearer EABdgy5ZCsnccBOzrOq9CnnHjHPe9ZBCSJbr4xdsJtqFBFNRXCWKXkQeaiP8gvsZAAGtKZCEnWFzCHALZBEkEgPKJZAAZBjBR0kUIo0GZCZBgJQoOuwmZBacZB33THmuVjZAjVAfY2KU4Iw0ln1G6C3nFKNZBfflLMjmlNxw6hhyVsw81DDoBgLOSEXNcl6am67TO2d6DK'
    url = f'{constants.business_constants[business_code]["whatsapp_url"]}{constants.business_constants[business_code]["whatsapp_id"]}/messages'
    bearer = f'Bearer {constants.business_constants[business_code]["whatsapp_token"]}'

    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": agent_whatsapp,
        "type": "template",
        "template": {
            "name": "notificacion_diaria",
            "language": {
                "code": "es"
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": agent_name
                        },
                        {
                            "type": "text",
                            "text": text_users
                        },
                        {
                            "type": "text",
                            "text": text_messages
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
    # mensajewa = WhatsApp("EABdgy5ZCsnccBOzrOq9CnnHjHPe9ZBCSJbr4xdsJtqFBFNRXCWKXkQeaiP8gvsZAAGtKZCEnWFzCHALZBEkEgPKJZAAZBjBR0kUIo0GZCZBgJQoOuwmZBacZB33THmuVjZAjVAfY2KU4Iw0ln1G6C3nFKNZBfflLMjmlNxw6hhyVsw81DDoBgLOSEXNcl6am67TO2d6DK", "159540240573780")
    mensajewa = WhatsApp(constants.business_constants[business_code]["whatsapp_token"], constants.business_constants[business_code]["whatsapp_id"])
    componente = '{"type": "body","parameters": [{"type": "text","text": "' + agent_name + '"},{"type": "text","text": "' + text_users + '"},{"type": "text","text": "' + text_messages + '"}]}'
    mensajewa.send_template('notificacion_diaria', agent_whatsapp, components=[componente], lang="es")
    """
