from fastapi import APIRouter
from fastapi_utilities import repeat_at
from datetime import datetime, timedelta
from heyoo import WhatsApp
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session
from backend.model.model import User, Message
from backend.config import constants

scheduler_app = APIRouter()


@scheduler_app.on_event('startup')
@repeat_at(cron="40 12 * * *")
async def send_notification():
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

        business_message = f'Saludos {business.business_contact}, a continuación le envio el reporte diario:'
        if users > 0:
            business_message += f'\n{users} usuarios estuvieron interactuactuando con {business.business_name}.'
            business_message += f'\nSe respondieron aproximandemente {messages} mensajes.'
        else:
            business_message += f'\nNingún usuario se contactó con {business.business_name}.'

        send_text(business_message, business.business_phone, business.business_code)


def send_text(anwser, numberwa, business_code):
    mensajewa = WhatsApp(constants.business_constants[business_code]["whatsapp_token"], constants.business_constants[business_code]["whatsapp_id"])
    # enviar los mensajes
    mensajewa.send_message(message=anwser, recipient_id=numberwa)
