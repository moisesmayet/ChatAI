import csv
import json
import os
import re
import openai
import pydub
import requests
import speech_recognition as sr
import pandas as pd
from datetime import datetime, timedelta
from elevenlabs import generate, save
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from heyoo import WhatsApp
from langchain.chat_models import ChatOpenAI
from llama_index import Prompt, GPTVectorStoreIndex, SimpleDirectoryReader, LLMPredictor, ServiceContext
from pydantic import BaseModel
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session
from backend.model.model import Agent, Message, Order, Product, Query, User, generate_random_key, Petition, Topic, Wsid, \
    Bug
from backend.config.constants import business_constants, exists_business, is_catalog, is_workflow, get_media_recipient

chatai_app = APIRouter()


class Token(BaseModel):
    access_token: str


class Answer(BaseModel):
    web_answer: str


class Question(BaseModel):
    web_question: str


class UserId(BaseModel):
    web_userid: str


class UserName(BaseModel):
    web_username: str


class UserWhatsapp(BaseModel):
    web_userwhatsapp: str


class SecretKey(BaseModel):
    web_secretkey: str


@chatai_app.get('/{business_code}/createby')
async def createby():
    return {'message': f'ChatAI by Moisés Mayet'}


@chatai_app.get('/{business_code}/webhook/')
async def webhook_whatsapp(request: Request, business_code: str):
    if exists_business(business_code):
        # Verificamos con el token de acceso
        if request.query_params.get('hub.verify_token') == business_constants[business_code]["openai_api_key"]:
            challenge = request.query_params.get('hub.challenge')
            return PlainTextResponse(f'{challenge}')

    return 'Error de autenticación.'


@chatai_app.post('/{business_code}/webhook/')
async def webhook_whatsapp(request: Request, business_code: str):
    if exists_business(business_code):
        # Se obtienen los datos en un JSON
        data = await request.json()

        if 'entry' in data and len(data['entry']) > 0 and 'changes' in data['entry'][0] and len(
                data['entry'][0]['changes']) > 0:
            # Se recupera el mensaje del JSON
            # ai_whatsapp = data['entry'][0]['changes'][0]['value']['metadata']['display_phone_number']
            message = ''
            message_data = data['entry'][0]['changes'][0]['value'].get('messages')

            if message_data:
                # Identificador único de mensaje
                idwa = message_data[0]['id']
                # Número de teléfono del usuario
                user_whatsapp = message_data[0]['from']
                # Se verifica si el mensaje es de tipo texto o media
                message_type = message_data[0]['type']

                db: Session = get_db_conn(business_code)
                # Ejecutamos la consulta para obtener la cantidad de registros
                cantidad = db.query(Wsid).filter(Wsid.wsid_code == idwa).count()
                db.close()

                if cantidad == 0:
                    db: Session = get_db_conn(business_code)
                    # Verificar si es un agente
                    agent = db.query(Agent).filter(Agent.agent_number == user_whatsapp).first()

                    # Guardar el id del mensaje de whatsapp
                    new_wsid = Wsid(wsid_code=idwa, wsid_date=datetime.now())
                    db.add(new_wsid)
                    db.commit()
                    db.close()

                    # Verificar que el mensaje no sea viejo(más de 15 min de enviado)
                    msg_time = int(message_data[0]['timestamp'])
                    msg_time = datetime.fromtimestamp(msg_time)
                    current_datetime = datetime.now()
                    # Calcular la diferencia entre las fechas
                    time_difference = current_datetime - msg_time
                    # Definir el umbral en horas
                    threshold = timedelta(minutes=business_constants[business_code]["messages_old"])
                    if time_difference <= threshold:
                        try:
                            reply = {}
                            filename = ''
                            audio_awnser = ''
                            openai_api_key = business_constants[business_code]["openai_api_key"]
                            os.environ['OPENAI_API_KEY'] = openai_api_key
                            openai.api_key = openai_api_key

                            user_response = create_user(user_whatsapp, user_whatsapp,
                                                        business_constants[business_code]["alias_user"],
                                                        business_code)

                            if message_type == 'text':
                                # Obtener el texto del mensaje
                                message = message_data[0]['text']['body'].strip()
                            else:
                                if business_constants[business_code]["messages_voice"] and message_type == 'audio':
                                    # Directorio local de medias
                                    filename = re.sub(r'\W', '', idwa)
                                    media_sent = get_media_recipient(business_code, user_whatsapp, 'audio', 'sent')
                                    local_media = os.path.join(os.getcwd(), f'{media_sent}/')
                                    audio_awnser = f'{local_media}answer_{filename}.ogg'
                                    if not os.path.exists(audio_awnser):
                                        # Obtener la url media de whatsapp
                                        audio_url = message_data[0]['audio']['id']
                                        audio_url = f'{business_constants[business_code]["whatsapp_url"]}{audio_url}/'
                                        response = requests.get(audio_url, headers={
                                            'Authorization': f'Bearer {business_constants[business_code]["whatsapp_token"]}'})
                                        audio_data = json.loads(response.content.decode('utf-8'))
                                        audio_url = audio_data['url']

                                        # Descargar media de whatsapp
                                        audio_ogg = f'{local_media}{filename}.ogg'
                                        audio_text = f'{local_media}{filename}.{business_constants[business_code]["transcribe_format"]}'
                                        response = requests.get(audio_url, headers={
                                            'Authorization': f'Bearer {business_constants[business_code]["whatsapp_token"]}'})
                                        with open(audio_ogg, 'wb') as file:
                                            file.write(response.content)

                                        ogg_file = os.path.join(media_sent, audio_ogg)
                                        pydub.AudioSegment.from_ogg(ogg_file).export(audio_text,
                                                                                     format=
                                                                                     business_constants[business_code][
                                                                                         "transcribe_format"])
                                        audio_filename = os.path.join(media_sent, audio_text)

                                        # Realiza la transcripción del audio
                                        message = transcribe_audio(audio_filename, openai_api_key, business_code)
                                        # Elimina el archivo de audio descargado
                                        remove_file(audio_ogg)

                                        # Notificar que se va a escuchar el audio
                                        msg_audio = f'Voy a escuchar el audio que me enviaste y en breve te respondo.'
                                        save_message(user_whatsapp, f'{message}\n{audio_filename}', msg_audio,
                                                     message_type, 'whatsapp', agent, None, business_code)
                                        send_text([msg_audio], user_whatsapp, business_code)

                                        if message == '':
                                            msg_audio = f'No se escucha bien la nota de voz.'

                                            send_voice(msg_audio, user_whatsapp, agent, filename, business_code)
                                            save_message(user_whatsapp, audio_filename, msg_audio, message_type,
                                                         'whatsapp', agent, None, business_code)
                                            return JSONResponse({'status': 'success'}, status_code=200)
                                else:
                                    if message_type == 'order':
                                        # Obtener el texto del mensaje
                                        catalog = message_data[0]['order']['catalog_id']
                                        products = message_data[0]['order']['product_items']
                                        order_number = save_order(user_whatsapp, business_code)
                                        for product in products:
                                            price = product['item_price']
                                            excel_values = get_row_values_excel(business_code, catalog,
                                                                                {'key': 'id',
                                                                                 'value': product[
                                                                                     'product_retailer_id']},
                                                                                ['id', 'title', 'description'])
                                            excel_values = excel_values[0]
                                            values = [excel_values['id'], excel_values['title'],
                                                      excel_values['description'],
                                                      price, price, product['currency'], '', 'Unidad',
                                                      product['quantity'],
                                                      order_number]
                                            save_product(values, business_code)

                                        answers = f'Su orden de compra ({order_number}) fue enviada satisfactoriamente'
                                        send_text([answers], user_whatsapp, business_code)
                                        save_message(user_whatsapp, '', answers, message_type, 'whatsapp', agent, None,
                                                     business_code)
                                        return JSONResponse({'status': 'success'}, status_code=200)
                                    else:
                                        if message_type == 'interactive':
                                            button = message_data[0]['interactive']['button_reply']
                                            message = button['title']
                                            button_id = str(button['id'])
                                            button_id = button_id.split('][')
                                            topic_name = button_id[0]
                                            topic_name = topic_name.replace('[', '')
                                            petition_number = button_id[1]
                                            petition_step = button_id[2].replace(']', '')
                                            petition_step = format_step(petition_step)
                                            petition = db.query(Petition).filter((Petition.user_number == user_whatsapp) &
                                                                                 (Petition.topic_name == topic_name) &
                                                                                 (Petition.status_code == 'CRE')).order_by(
                                                Petition.petition_date.desc()).first()
                                            if (petition and petition.petition_number == petition_number) or (
                                                    petition_number == 'None' and petition_step != 'cancel'):
                                                if petition:
                                                    petition_number = petition.petition_number
                                                reply = send_interactive(user_whatsapp, message, '', message_type,
                                                                         agent, petition_number,
                                                                         topic_name,
                                                                         petition_step, False, business_code)
                                            else:
                                                if petition_step == 'cancel':
                                                    answers = f'Si desea algo más, con gusto le ayudaré'
                                                else:
                                                    answers = f'Ya realizaste este proceso. Si deseas puedes solicitarme hablar con un {business_constants[business_code]["alias_expert"]}'
                                                send_text([answers], user_whatsapp, business_code)
                                                save_message(user_whatsapp, '', answers, message_type, 'whatsapp',
                                                             agent, None, business_code)
                                                return JSONResponse({'status': 'success'}, status_code=200)
                                        else:
                                            if message_type == 'audio' or \
                                                    message_type == 'image' or \
                                                    message_type == 'video' or \
                                                    message_type == 'document' or \
                                                    message_type == 'contact' or \
                                                    message_type == 'sticker' or \
                                                    message_type == 'location':
                                                msg = ''
                                                if message_type != 'sticker' and message_type != 'location':
                                                    msg = download_media(business_code, user_whatsapp,
                                                                         message_data[0][message_type], message_type,
                                                                         idwa)
                                                answers = f'Gracias por tu mensaje'
                                                send_text([answers], user_whatsapp, business_code)
                                                save_message(user_whatsapp, msg, answers, message_type, 'whatsapp',
                                                             agent, None, business_code)
                                                return JSONResponse({'status': 'success'}, status_code=200)
                                            else:
                                                if message_type != 'reaction':
                                                    answers = f'Gracias por tu mensaje'
                                                    send_text([answers], user_whatsapp, business_code)
                                                    save_message(user_whatsapp, '', answers, message_type, 'whatsapp',
                                                                 agent, None, business_code)
                                                    return JSONResponse({'status': 'success'}, status_code=200)

                            # Revisar que haya mensaje
                            if len(message):
                                if not reply:
                                    reply = reply_message(message, message_type, user_response['number'],
                                                          user_response['usuario'], agent,
                                                          user_response['user_completed'],
                                                          'whatsapp', business_code)

                                send_messages(reply['respond'], reply['notify'], message_type, user_response,
                                              user_whatsapp,
                                              reply['answers'], agent, filename, audio_awnser, business_code)

                                # Retornar la respuesto en un JSON
                                return JSONResponse({'status': 'success'}, status_code=200)
                        except Exception as e:
                            # En caso de error, retornar una respuesta JSON con el mensaje de error
                            save_message(user_whatsapp, message, '', message_type, 'whatsapp', agent, None,
                                         business_code)
                            save_bug(business_code, str(e), 'whatsapp')
                            notify_bug(f'webhook_whatsapp', message, str(e), business_code)
                            return JSONResponse({'status': 'no_messages'}, status_code=200)

    # No hay mensajes disponibles
    return JSONResponse({'status': 'no_messages'}, status_code=200)


@chatai_app.post('/{business_code}/webhookweb')
async def webhook_web(userid: UserId, username: UserName, userwhatsapp: UserWhatsapp, question: Question,
                      secretkey: SecretKey, business_code: str):
    answer = ''
    if exists_business(business_code):
        if question.web_question != 'string' and question.web_question != '':
            if secretkey.web_secretkey == business_constants[business_code]["server_key"]:

                user_response = create_user(userid.web_userid, userwhatsapp.web_userwhatsapp, username.web_username,
                                            business_code)

                openai_api_key = business_constants[business_code]["openai_api_key"]
                os.environ['OPENAI_API_KEY'] = openai_api_key
                openai.api_key = openai_api_key
                reply = reply_message(question.web_question, 'text', user_response['number'], user_response['usuario'],
                                      None,
                                      user_response['user_completed'], 'web', business_code)

                if reply['respond']:
                    answer = ' '.join(reply['answers'])

                if reply['notify']:
                    notify(user_response['number'], user_response['whatsapp'], user_response['usuario'], business_code)
            else:
                answer = f'El chabot no tiene acceso al servidor desde {secretkey.web_secretkey}.'
        else:
            answer = f'No pude procesar tu mensaje. Por favor, intenta hacer la pregunta de otra forma.'
    else:
        answer = f'El servicio no esta activo.'

    return Answer(web_answer=answer)


@chatai_app.get("/backend/media/{business_code}/{msg_user}/{msg_type}/{msg_recipient}/{filename:path}")
async def serve_media(business_code: str, msg_user: str, msg_type: str, msg_recipient: str, filename: str):
    file_path = ''
    if exists_business(business_code):
        # Utiliza la clase FileResponse para enviar el archivo multimedia
        # recipient 'sent' or 'received'
        # type 'audio', 'image', 'video' or 'document'
        file_path = get_media_recipient(business_code, msg_user, msg_type, msg_recipient)
        file_path = f'{file_path}/{filename}'
    return FileResponse(file_path)


def reply_message(message, message_type, number_user, usuario, agent, user_completed, origin, business_code):
    answers = []
    agent_notify = False
    send_answer = True

    # Conectamos a la base de datos
    db: Session = get_db_conn(business_code)

    if agent is None:
        role_wa = 'user'

        watting = watting_agent(number_user, business_code)
        if not watting:
            reply = get_answer(message, role_wa, number_user, usuario, origin, message_type, agent, business_code)
            agent_notify = reply['notify']
            answer = reply['answer']
            answers.append(answer)
            send_answer = reply['send_answer']
            if reply['check_transfer_agent']:
                suggest_transfer = suggest_transfer_agent(answer, number_user, business_code)
                if not suggest_transfer['send_answer']:
                    answers.append(suggest_transfer['answer'])
                    send_answer = False

            # Verificar si tiene mensajes hoy
            current_date = datetime.now().date()
            exists_msg = db.query(Message).filter(Message.user_number == number_user,
                                                  Message.msg_date >= current_date).first()

            if exists_msg is None and not user_completed:
                greetings = f'Mi nombre es {business_constants[business_code]["alias_ai"]} y estaré aquí para cualquier información que necesites.'
                if origin != 'web':
                    greetings += ' Me gustaría saber como te llamas.'
                answers.append(greetings)
                message_type = 'name'

            answers_str = ' '.join(answers)
        else:
            origin = 'agent'
            answers_str = ''

        if message_type != 'audio':
            save_message(number_user, message, answers_str.strip(), message_type, origin, agent, None, business_code)
    else:
        usuario = agent.agent_name
        role_wa = 'agents'
        reply = get_answer(message, role_wa, number_user, usuario, origin, message_type, agent, business_code)
        answers.append(reply['answer'])
        agent_notify = reply['notify']
        send_answer = reply['send_answer']

        answers_str = ' '.join(answers)
        if message_type != 'audio':
            save_message(number_user, message, answers_str.strip(), message_type, origin, agent, None, business_code)

    # Cerramos la conexión y el cursor
    db.close()

    # Retornar status
    return {'answers': answers, 'respond': send_answer, 'notify': agent_notify}


def get_answer(query_message, query_role, query_number, query_usuario, query_origin, query_type, query_agent,
               business_code):
    try:
        agent_notify = False
        check_transfer_agent = False
        answer = ''
        if query_message.strip() != '':
            if query_role == 'user':
                behavior = business_constants[business_code]["behavior_user"]
            else:
                behavior = business_constants[business_code]["behavior_agent"]
            if query_usuario is None or query_usuario == '':
                behavior = behavior.replace(f'{business_constants[business_code]["alias_user"]}',
                                            business_constants[business_code]["alias_user"])
            else:
                behavior = behavior.replace(f'{business_constants[business_code]["alias_user"]}', query_usuario)

            index_context = get_index(query_message, business_constants[business_code]["topic_context"], 'None',
                                      business_code)
            if index_context == 'None':
                index_context = answering_name(business_code, query_number, 'None')

            if index_context != 'None' and query_role != 'agents':
                if index_context != '0' and index_context != '1':
                    key_topic = business_constants[business_code]["topic_list"][index_context]
                    db: Session = get_db_conn(business_code)
                    topic = db.query(Topic).filter(Topic.topic_name == key_topic).first()
                    db.close()
                    if not is_workflow_unique(query_number, key_topic, topic.type_code, business_code):
                        if is_workflow(business_code, key_topic):
                            send_answer = True
                            if query_origin == 'whatsapp':
                                petition = get_open_petition(query_number, key_topic, business_code)

                                if petition is None:
                                    workflow = get_workflow(business_code, 'None', key_topic, '', 'interactive', False)
                                else:
                                    if petition.petition_steptype != 'confirm':
                                        petition_step = petition.petition_step
                                        petition_steptype = petition.petition_steptype
                                    else:
                                        petition_step = petition.petition_stepfrom
                                        petition_steptype = 'data'

                                    petition_request = f'¿Desea continuar con "{topic.topic_description}"?'
                                    workflow_values = {'TEXT': petition_request, 'TYPE': petition_steptype, 'TAG': '',
                                                       'BUTTON1': 'Continuar', 'GOTOID1': petition_step,
                                                       'BUTTON2': 'Reiniciar', 'GOTOID2': '1',
                                                       'BUTTON3': 'Cancelar', 'GOTOID3': 'cancel'}
                                    workflow = create_workflow(business_code, petition.petition_number, key_topic,
                                                               petition_step, workflow_values,
                                                               True)
                                payload = json_button(workflow)
                                send_json(query_number, payload, business_code)
                                answer = workflow['text']
                                send_answer = False
                            else:
                                answer = f'Para ayudarte mejor con esta solicitud, te recomendamos escribir a nuestro Whatsapp {business_constants[business_code]["whatsapp_number"]}'
                            return {'answer': answer, 'send_answer': send_answer, 'notify': agent_notify,
                                    'check_transfer_agent': check_transfer_agent}
                        else:
                            if is_catalog(business_code, key_topic):
                                if query_origin == 'whatsapp':
                                    catalog = get_catalog(business_code, key_topic)
                                    payload = json_catalog(catalog)
                                    send_json(query_number, payload, business_code)
                                    answer = f'Con gusto aquí le mostramos nuestro catálogo'
                                else:
                                    answer = f'Si desea adquirir un {business_constants[business_code]["alias_item"]}, le recomendamos escribir al nuestro Whatsapp  {business_constants[business_code]["whatsapp_number"]} para enviarte nuestro catálogo'
                                return {'answer': answer, 'send_answer': True, 'notify': agent_notify,
                                        'check_transfer_agent': check_transfer_agent}
                            else:
                                reply = get_reply_info(query_message, query_number, query_origin, query_type,
                                                       query_agent,
                                                       business_code)
                                if reply:
                                    return {'answer': reply['answers'][0], 'send_answer': reply['respond'],
                                            'notify': False, 'check_transfer_agent': check_transfer_agent}

                        if answer == '':
                            behavior += f'Basándote en la siguiente información de contexto.\\\n{{context_str}}\\\n'
                            behavior += f'Responde el siguiente texto: "{{query_str}}"\\\n'
                            qa_template = Prompt(behavior)

                            query_index = get_query_index(key_topic, business_code)
                            if query_index is not None:
                                answer = query_index.as_query_engine(text_qa_template=qa_template).query(
                                    query_message).response
                            else:
                                answer = f'En este momento estamos atendiendo el máximo de usuarios. Si deseas puedes solicitar comunicarte directamente con un {business_constants[business_code]["alias_expert"]}'
                    else:
                        if topic.type_code == 'WFU':
                            answer = f'Ya realizaste este proceso. Si deseas puedes solicitarme hablar con un {business_constants[business_code]["alias_expert"]}'
                        else:
                            transfer = transfer_agent(behavior, query_message, query_number, query_role, business_code)
                            answer = transfer['answer']
                            agent_notify = transfer['agent_notify']

                    process_answer(answer, business_code)
                else:
                    if index_context == '0':
                        transfer = transfer_agent(behavior, query_message, query_number, query_role, business_code)
                        answer = transfer['answer']
                        agent_notify = transfer['agent_notify']
                    else:
                        reply = get_reply_info(query_message, query_number, query_origin, query_type, query_agent,
                                               business_code)
                        if reply:
                            return {'answer': reply['answers'][0], 'send_answer': reply['respond'], 'notify': False,
                                    'check_transfer_agent': check_transfer_agent}

                        user_name = get_completion(
                            f'''Extrae el nombre de la persona del texto y si no hay nombre contesta "None": {query_message}''',
                            business_code)
                        if user_name.endswith('.'):
                            user_name = user_name[:-1]
                        if user_name != 'None' and re.match('^[A-Za-z][a-z]+( [A-Za-z][a-z]+)?$', user_name,
                                                            re.IGNORECASE):
                            update_user(query_number, user_name, business_code)
                            answer = f'{user_name}, es un placer. ¿En qué puedo ayudarte?'
                        else:
                            answer = get_chatcompletion(behavior, query_message, query_number, query_role,
                                                        business_code)
                            if answer == 'not_chatcompletion':
                                answer = f'Quizás un {business_constants[business_code]["alias_expert"]} podría responder mejor tus inquietudes'
                            check_transfer_agent = True
            else:
                answer = ''
                if query_role == 'agent':
                    topic_order = f'"<1> Información del {business_constants[business_code]["alias_user"]}", "<2> Información de mensajes"'
                    sentence = get_index(query_message, topic_order, '0', business_code)
                    if sentence != '0':
                        number = get_completion(
                            f'''Extrae el número telefónico del texto y si no hay número contesta "None": {query_message}''',
                            business_code)
                        if number != 'None':
                            number = str(number).replace('+', '')
                            if number.isdigit():
                                if sentence == '1':
                                    db: Session = get_db_conn(business_code)
                                    user = db.query(User).filter(User.user_number == number).first()
                                    if user:
                                        answer = f'El número pertenece al {business_constants[business_code]["alias_user"]} {user.user_name}'
                                    db.close()
                                else:
                                    if sentence == '2':
                                        cantidad = get_completion(
                                            f'''Extrae la cantidad de mensajes del texto y si no hay cantidad contesta "1": {query_message}''',
                                            business_code)
                                        if cantidad.isdigit():
                                            db: Session = get_db_conn(business_code)
                                            messages = db.query(Message).filter(Message.user_number == number).order_by(
                                                Message.id.desc()).limit(cantidad).all()
                                            for message in messages:
                                                answer += f'[{message.msg_date}] {message.msg_sent}\n{message.msg_received}\n'
                                            db.close()

                if answer == '':
                    if query_type == 'interactive':
                        reply = get_reply_info(query_message, query_number, query_origin, query_type, query_agent,
                                               business_code)
                        if reply:
                            return {'answer': reply['answers'][0], 'send_answer': reply['respond'], 'notify': False,
                                    'check_transfer_agent': check_transfer_agent}
                    answer = get_chatcompletion(behavior, query_message, query_number, query_role, business_code)
                    if answer == 'check_transfer_agent':
                        answer = f'Hola, si deseas un {business_constants[business_code]["alias_expert"]} podría responder mejor tus inquietudes'
                        check_transfer_agent = True
                process_answer(answer, business_code)
        else:
            answer = f'Parece que tu mensaje está vacío. Por favor, intenta hacer la pregunta de otra forma.'

        answer = str(answer)
        if 'None, es un placer.' in answer:
            answer_split = answer.split("None, es un placer.", 1)
            if answer_split.count() > 1:
                answer = answer_split[1].strip()
            else:
                answer = f'Es un placer asistirle'

        if business_constants[business_code]["messages_translator"] and index_context != '1':
            language = get_language(query_message, answer, business_code)
            if language != 'None':
                answer = get_promptcompletion(
                    f'Debes traducir siguiente texto "{answer}" al {language} y dar solo la traducción como respuesta.',
                    business_code)
                answer = re.findall(r'"([^"]*)"', answer)
                answer = answer[0]

        return {'answer': answer, 'send_answer': True, 'notify': agent_notify,
                'check_transfer_agent': check_transfer_agent}
    except Exception as e:
        save_bug(business_code, str(e), 'whatsapp')
        notify_bug(f'get_answer', query_message, str(e), business_code)
        return {'answer': '', 'send_answer': False, 'notify': False, 'check_transfer_agent': False}


def answer_transfer_agent(business_code):
    answer = f'Ya realicé la notificación para que te atienda un {business_constants[business_code]["alias_expert"]}.\n'
    answer += f'En unos minutos uno de nuestros representantes te brindará asistencia.\n'
    if business_constants[business_code]["alias_site"] != '':
        answer += f'En nuestro sitio web {business_constants[business_code]["alias_site"]} puede encontrar toda la información necesaria.\n'
    answer += f'Fue un placer para mi atenderte.'
    return answer


def transfer_agent(behavior, query_message, query_number, query_role, business_code):
    agent_notify = False
    prompt = f'Responde 1 si el texto es un pedido o solicitud. Reponde 0 si el texto es una pregunta\\\nTexto: "{query_message}"'
    sentence = get_completion(prompt, business_code)
    if sentence and sentence[0] == '1':
        answer = answer_transfer_agent(business_code)
        agent_notify = True
    else:
        answer = get_chatcompletion(behavior, query_message, query_number, query_role, business_code)
        if answer == 'not_chatcompletion':
            answer = f'Háblame un poco más de eso'
    return {'agent_notify': agent_notify, 'answer': answer}


def suggest_transfer_agent(query_answer, query_number, business_code):
    answer = query_answer
    send_answer = True
    alias_expert = business_constants[business_code]["alias_expert"]
    if alias_expert in query_answer:
        send_text([query_answer], query_number, business_code)
        petition_request = f'¿Desea que le transfiera con un {business_constants[business_code]["alias_expert"]}?'
        workflow_values = {'TEXT': petition_request, 'TYPE': 'agent', 'TAG': '',
                           'BUTTON1': f'Sí', 'GOTOID1': 'agent',
                           'BUTTON2': 'nan', 'GOTOID2': 'nan',
                           'BUTTON3': 'nan', 'GOTOID3': 'nan'}
        workflow = create_workflow(business_code, 'None', 'agent', '', workflow_values, True)
        payload = json_button(workflow)
        send_json(query_number, payload, business_code)
        answer = workflow['text']
        send_answer = False
    return {'answer': answer, 'send_answer': send_answer}


def process_answer(answer, business_code):
    if answer != '':
        answer = answer.replace('\\n', '\\\n')
        answer = answer.replace('\\', '')
    else:
        answer = f'Lo siento no tengo respuesta a tu pregunta. Si deseas puedes solicitar comunicarte directamente con un {business_constants[business_code]["alias_expert"]}'
    return answer


def get_query_index(key_topic, business_code):
    try:
        topic_index = {}
        openai_model = business_constants[business_code]['openai_model']
        prompt_dir = business_constants[business_code]['prompt_dir']
        index_persist_dir = business_constants[business_code]['index_persist_dir']

        if key_topic not in topic_index:
            directory_prompt = f'{prompt_dir}/{key_topic}'
            directory_persist = f'{index_persist_dir}/{key_topic}'
            # Cargar los datos del directorio "prompt" y almacenarlos en caché
            documents = SimpleDirectoryReader(directory_prompt).load_data()
            modelo = LLMPredictor(llm=ChatOpenAI(temperature=0.2, request_timeout=30, model_name=openai_model))
            service_context = ServiceContext.from_defaults(llm_predictor=modelo)
            index_storage = GPTVectorStoreIndex.from_documents(documents, service_context=service_context)
            index_storage.storage_context.persist(persist_dir=directory_persist)
            topic_index[key_topic] = index_storage
            return index_storage

        return topic_index[key_topic]
    except Exception as e:
        return None


def get_index(query, options, index_default, business_code):
    prompt = f'Buscar el elemento de la lista tiene mayor similitud al texto: "{query}"\n\nOptions:\n{options}\nSi no encuentra relación responde ""\nEjemplo:<1> El sol'
    index_context = get_promptcompletion(prompt, business_code)
    index = re.findall(r"(\d+)", index_context)
    if len(index) == 1:
        index = index[0]
        if index.isdigit():
            if int(index) < len(business_constants[business_code]["topic_list"]):
                return index

    return index_default


def get_promptcompletion(prompt, business_code):
    try:
        messages = [{'role': 'user', 'content': prompt}]
        response = openai.ChatCompletion.create(
            model=business_constants[business_code]["openai_model"],
            messages=messages,
            request_timeout=30,
            n=1,
            temperature=0,
            stop=None
        )
        return response.choices[0].message['content']
    except Exception as e:
        notify_bug(f'get_promptcompletion', prompt, str(e), business_code)
        return f'En este momento estamos atendiendo el máximo de usuarios. Lamentamos este inconveniente. Por favor escríbanos en unos minutos y con gusto le atenderemos'


def get_chatcompletion(behavior, question, user_number, role, business_code):
    messages = [{"role": "system", "content": behavior}]
    if business_constants[business_code]["messages_historical"] > 0:
        try:
            db: Session = get_db_conn(business_code)
            if role == 'user':
                role_messages = db.query(Message).filter(Message.user_number == user_number).order_by(
                    Message.id.desc()).limit(business_constants[business_code]["messages_historical"]).all()
                role_messages = sorted(role_messages, key=lambda x: x.id)
                for message in role_messages:
                    messages.append({"role": "user", "content": message.msg_sent})
                    messages.append({"role": "assistant", "content": message.msg_received})
            else:
                role_queries = db.query(Query).filter(Query.agent_number == user_number).order_by(Query.id.desc()).limit(
                    business_constants[business_code]["messages_historical"]).all()
                role_queries = sorted(role_queries, key=lambda x: x.id)
                for query in role_queries:
                    messages.append({"role": "user", "content": query.query_sent})
                    messages.append({"role": "assistant", "content": query.query_received})
            db.close()
            messages.append({"role": "user", "content": question})

            response = openai.ChatCompletion.create(
                model=business_constants[business_code]["openai_model"],
                messages=messages,
                request_timeout=30,
                temperature=0.3,
                n=1,
                stop=None
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            notify_bug(f'get_chatcompletion', question, str(e), business_code)
            return f'En este momento estamos atendiendo el máximo de usuarios. Lamentamos este inconveniente. Por favor escríbanos en unos minutos y con gusto le atenderemos'
    else:
        prompt = f'Responde 1 si el siguiente texto es un saludo o un agradecimiento\\\nTexto: "{question}"'
        response = get_completion(prompt, business_code)
        if response and response[0] == '1':
            try:
                messages.append({"role": "user", "content": question})
                response = openai.ChatCompletion.create(
                    model=business_constants[business_code]["openai_model"],
                    messages=messages,
                    request_timeout=30,
                    temperature=0.3,
                    n=1,
                    stop=None
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                notify_bug(f'get_chatcompletion', question, str(e), business_code)
                return f'En este momento estamos atendiendo el máximo de usuarios. Lamentamos este inconveniente. Por favor escríbanos en unos minutos y con gusto le atenderemos'
        else:
            return f'not_chatcompletion'


def get_completion(prompt, business_code):
    try:
        response = openai.Completion.create(
            engine=business_constants[business_code]["openai_engine"],
            prompt=prompt,
            request_timeout=30,
            temperature=0.3,
            n=1,
            stop=None
        )

        return response.choices[0].text.strip()
    except Exception as e:
        notify_bug(f'get_completion', prompt, str(e), business_code)
        return f'En este momento estamos atendiendo el máximo de usuarios. Lamentamos este inconveniente. Por favor escríbanos en unos minutos y con gusto le atenderemos'


def get_order(number_user, business_code):
    # Ejecutamos la consulta para encontrar una orden
    db: Session = get_db_conn(business_code)

    order = db.query(Order).filter((Order.user_number == number_user) & (Order.status_code == 'CRE')).order_by(
        Order.order_start.desc()).first()

    # Cerramos la conexión y el cursor
    db.close()

    if order:
        return order.order_number
    else:
        return '0'


def save_bug(business_code, bug, origin):
    db: Session = get_db_conn(business_code)
    new_bug = Bug(bug_description=bug, bug_origin=origin, bug_date=datetime.now())
    db.add(new_bug)
    db.commit()
    db.close()


def save_message(msg_number, msg_sent, msg_received, msg_type, msg_origin, msg_agent, msg_petition, business_code):
    # Ejecutamos la consulta para insertar un nueva orden
    db: Session = get_db_conn(business_code)

    if msg_agent is None:
        new_message = Message(user_number=msg_number, msg_sent=msg_sent,
                              msg_received=msg_received, msg_type=msg_type,
                              msg_origin=msg_origin, msg_date=datetime.now(), petition_number=msg_petition)
    else:
        new_message = Query(agent_number=msg_number, query_sent=msg_sent, query_received=msg_received,
                            query_type=msg_type, query_origin=msg_origin, query_date=datetime.now())
    db.add(new_message)
    db.commit()

    if msg_agent is None:
        last_message = db.query(Message).filter((Message.user_number == msg_number) &
                                                (Message.msg_received != '')).order_by(
            Message.id.desc()).first()
        user = db.query(User).filter(User.user_number == msg_number).first()
        user.user_lastmsg = last_message.id
        user.user_lastdate = datetime.now()
        db.merge(user)
        db.commit()
    db.close()


def is_workflow_unique(number_user, topic_name, type_code, business_code):
    if type_code == 'WFU':
        db: Session = get_db_conn(business_code)
        petition = db.query(Petition).filter((Petition.user_number == number_user) &
                                             (Petition.topic_name == topic_name) &
                                             (Petition.status_code == 'COM')).first()
        db.close()
        if petition is not None:
            return True
    return False


def get_open_petition(number_user, topic_name, business_code):
    db: Session = get_db_conn(business_code)
    petition = db.query(Petition).filter((Petition.user_number == number_user) &
                                         (Petition.topic_name == topic_name) &
                                         (Petition.status_code == 'CRE')).order_by(
        Petition.petition_date.desc()).first()
    if petition is not None:
        if petition.petition_steptype.startswith('finish'):
            petition.status_code = 'COM'
            db.commit()
            petition_number = create_petition(number_user, topic_name, petition.petition_stepfrom, business_code)
            petition = db.query(Petition).filter(Petition.petition_number == petition_number).first()
    # Cerramos la conexión y el cursor
    db.close()

    return petition


def create_petition(number_user, topic_name, petition_step, business_code):
    # Ejecutamos la consulta para insertar un nueva orden
    db: Session = get_db_conn(business_code)
    while True:
        petition_number = generate_random_key(10)
        petition = db.query(Petition).filter(Petition.petition_number == petition_number).first()
        if petition is None:
            break

    topic = db.query(Topic).filter(Topic.topic_name == topic_name).first()
    new_petition = Petition(petition_number=petition_number, user_number=number_user, topic_name=topic_name,
                            status_code='CRE', petition_name=topic.topic_description,
                            petition_request=f'{topic.topic_description}\nCódigo: {petition_number}',
                            petition_step=petition_step, petition_stepfrom='1', petition_steptype='start')

    db.add(new_petition)
    db.commit()
    # Cerramos la conexión y el cursor
    db.close()

    return petition_number


def save_petition(number_user, topic_name, petition_step, petition_steptype, status_code, petition_request,
                  business_code):
    # Ejecutamos la consulta para insertar un nueva orden
    db: Session = get_db_conn(business_code)
    petition = db.query(Petition).filter((Petition.user_number == number_user) & (Petition.topic_name == topic_name) &
                                         (Petition.status_code == 'CRE')).order_by(
        Petition.petition_date.desc()).first()
    if petition is not None:
        current_datetime = datetime.now()
        # Calcular la diferencia entre las fechas
        time_difference = current_datetime - petition.petition_date
        # Definir el umbral en horas
        threshold = timedelta(hours=24)
        if time_difference <= threshold:
            petition_number = petition.petition_number
            if petition_step == 'cancel':
                petition.status_code = 'CAN'
            else:
                if status_code is not None:
                    petition.status_code = status_code
        else:
            if petition_step != 'cancel':
                petition_number = create_petition(number_user, topic_name, petition_step, business_code)
            petition.status_code = 'CAN'
        petition.petition_date = datetime.now()
        if petition_request != '':
            if petition.petition_request != '':
                petition.petition_request += f'\n{petition_request}'
            else:
                petition.petition_request = petition_request
        petition.petition_stepfrom = petition.petition_step
        petition.petition_step = petition_step
        petition.petition_steptype = petition_steptype
        db.merge(petition)
        db.commit()
    else:
        if petition_step != 'cancel':
            petition_number = create_petition(number_user, topic_name, petition_step, business_code)
    # Cerramos la conexión y el cursor
    db.close()

    if petition_steptype.startswith('finish') or petition_step == 'cancel':
        petition_number = ''

    return petition_number


def save_order(number_user, business_code):
    # Ejecutamos la consulta para insertar un nueva orden
    db: Session = get_db_conn(business_code)
    while True:
        order_number = generate_random_key(10)
        order = db.query(Order).filter(Order.order_number == order_number).first()
        if order is None:
            break

    new_order = Order(order_number=order_number, user_number=number_user, status_code='CRE', order_start=datetime.now())
    db.add(new_order)
    db.commit()
    # Cerramos la conexión y el cursor
    db.close()

    return order_number


def save_product(product, business_code):
    # Ejecutamos la consulta para insertar un nuevo producto
    db: Session = get_db_conn(business_code)

    product_code = product[0]
    order_number = product[9]
    product_amount = product[8]
    cantidad = count_product(order_number, product_code, business_code)
    if cantidad == 0:
        product_name = product[1]
        product_description = product[2]
        product_price = product[3]
        product_payment = product[4]
        product_currency = product[5]
        product_offer = product[6]
        product_measure = product[7]
        new_product = Product(product_code=product_code, product_name=product_name,
                              product_description=product_description, product_offer=product_offer,
                              product_price=product_price, product_payment=product_payment,
                              product_currency=product_currency,
                              product_measure=product_measure, product_amount=product_amount, order_number=order_number)
        db.add(new_product)

        # Guardamos los cambios en la base de datos
        db.commit()

    # Cerramos la conexión y el cursor
    db.close()


def update_product(order_number, product_code, product_amount, business_code):
    # Ejecutamos la consulta para actuaizar un producto
    db: Session = get_db_conn(business_code)

    cantidad = count_product(order_number, product_code, business_code)
    if cantidad > 0:
        product = db.query(Product).filter_by(product_code=product_code, order_number=order_number).first()
        product.product_amount = product_amount

        # Guardamos los cambios en la base de datos
        db.commit()

    # Cerramos la conexión y el cursor
    db.close()

    if cantidad > 0:
        return f'Se actualizó el {business_constants[business_code]["alias_item"]} de tu {business_constants[business_code]["alias_order"]}.'
    else:
        return f'No existe el {business_constants[business_code]["alias_item"]}({product_code}) de tu {business_constants[business_code]["alias_order"]}.'


def get_product(order_number, business_code):
    # Ejecutamos la consulta para obtener un producto
    db: Session = get_db_conn(business_code)
    result = ''
    products = db.query(Product).filter_by(order_number=order_number)
    for product in products:
        result = f'{business_constants[business_code]["alias_item"]}: {product.product_name}({product.product_code}), precio: {product.product_payment}$'
        if product.product_offer != '':
            result += f'({product.product_offer})'
        result += f', cantidad: {product.product_amount}({product.product_measure})\n'

    # Cerramos la conexión y el cursor
    db.close()

    if result != '':
        return f'{business_constants[business_code]["alias_order"]}: \n{result}'
    else:
        return f'No tenemos registros de {business_constants[business_code]["alias_item"]}s que hayas solicitado.'


def get_row_values_excel(business_code, topic_name, row_id, list_ids):
    list_values = []
    dir_excel = os.path.join(os.getcwd(), f'{business_constants[business_code]["prompt_dir"]}/{topic_name}/')
    files = os.listdir(dir_excel)

    for file in files:
        # Ruta completa del archivo
        file_path = os.path.join(dir_excel, file)
        # Verificar si es un archivo
        if os.path.isfile(file_path):
            file_ext = os.path.splitext(file_path)[1]
            if file_ext.lower() in ['.xls', '.xlsx']:
                excel_data = pd.read_excel(file_path, skiprows=1)  # Saltar a la tercera fila
                if row_id is not None:
                    for index, row in excel_data.iterrows():
                        value = str(row_id['value'])
                        if value == '' or value == str(row[row_id['key']]):
                            row_values = {}
                            for item_id in list_ids:
                                row_values[item_id] = str(row[item_id]).strip()
                            list_values.append(row_values)
                            return list_values
                else:
                    for index, row in excel_data.iterrows():
                        row_values = {}
                        for item_id in list_ids:
                            row_values[item_id] = str(row[item_id]).strip()
                        list_values.append(row_values)
    return list_values


def get_row_values_csv(business_code, topic_name, row_id, list_ids):
    list_values = {}
    dir_csv = os.path.join(os.getcwd(), f'{business_constants[business_code]["prompt_dir"]}/{topic_name}/')
    files = os.listdir(dir_csv)
    for file in files:
        # Ruta completa del archivo
        file_csv = os.path.join(dir_csv, file)
        # Verificar si es un archivo
        if os.path.isfile(file_csv):
            file_ext = os.path.splitext(file_csv)[1]
            if file_ext.lower() == '.csv':
                with open(file_csv, 'r', newline='', encoding='utf-8') as products:
                    reader = csv.DictReader(products)
                    if row_id is not None:
                        for row in reader:
                            if str(row_id.value) == '' or str(row_id.value) == str(row[row_id.key]):
                                row_values = {}
                                for item_id in list_ids:
                                    row_values[item_id] = str(row[item_id]).strip()
                                list_values.append(row_values)
                                return list_values
                    else:
                        for row in reader:
                            row_values = {}
                            for item_id in list_ids:
                                row_values[item_id] = str(row[item_id]).strip()
                            list_values.append(row_values)
    return list_values


def count_product(order_number, product_code, business_code):
    # Ejecutamos la consulta para actuaizar un producto
    db: Session = get_db_conn(business_code)

    cantidad = db.query(Product).filter_by(order_number=order_number, product_code=product_code).count()

    # Cerramos la conexión y el cursor
    db.close()

    return cantidad


def delete_product(order_number, product_code, business_code):
    # Ejecutamos la consulta para eliminar un producto
    db: Session = get_db_conn(business_code)

    cantidad = count_product(order_number, product_code, business_code)
    if cantidad > 0:
        product = db.query(Product).filter_by(product_code=product_code, order_number=order_number).first()
        if product:
            db.delete(product)

        # Guardamos los cambios en la base de datos
        db.commit()

    # Cerramos la conexión y el cursor
    db.close()

    if cantidad > 0:
        return f'Se eliminó el {business_constants[business_code]["alias_item"]} de tu {business_constants[business_code]["alias_order"]}.'
    else:
        return f'No se encontró el {business_constants[business_code]["alias_item"]} en tu {business_constants[business_code]["alias_order"]}.'


def create_user(user_number, user_whatsapp, user_name, business_code):
    usuario = user_name
    whatsapp = user_whatsapp
    user_completed = False

    # Ejecutamos la consulta para insertar un nuevo usuario
    db: Session = get_db_conn(business_code)

    user = db.query(User).filter(User.user_number == user_number).first()
    if user:
        if user.user_whatsapp == '':
            if user_whatsapp != '':
                user.user_whatsapp = user_whatsapp
                db.merge(user)
                db.commit()
        else:
            whatsapp = user.user_whatsapp
            user_ws = db.query(User).filter((User.user_number == whatsapp) & (User.user_whatsapp == whatsapp)).first()
            if user_ws:
                other_user = db.query(User).filter(
                    (User.user_number != whatsapp) & (User.user_whatsapp == whatsapp)).first()
                if other_user:
                    user_number = other_user.user_number
                    messages = db.query(Message).filter(Message.user_number == whatsapp).all()
                    if len(messages) > 0:
                        for message in messages:
                            message.user_number = user_number
                            db.merge(message)
                        db.commit()
                    if user_ws:
                        db.delete(user_ws)
                        db.commit()

        user = db.query(User).filter(User.user_number == user_number).first()
        if user.user_name != '' and user.user_name != business_constants[business_code]["alias_user"]:
            usuario = user.user_name
            user_completed = True
        else:
            if usuario != '' and usuario != business_constants[business_code]["alias_user"]:
                user_completed = True
                usuario = user_name
                user.user_name = user_name
                db.merge(user)
                db.commit()
    else:
        # Verificar si ya existia un usuario diferente con ese whatsapp
        user_ws = None
        if user_whatsapp != '':
            user_ws = db.query(User).filter((User.user_number != user_number) &
                                            (User.user_whatsapp == user_whatsapp)).first()
            if user_ws:
                user_number = user_ws.user_number
                if user_ws.user_name == '':
                    if usuario != '' and usuario != business_constants[business_code]["alias_user"]:
                        user_completed = True
                        user_ws.user_name = usuario
                        db.merge(user_ws)
                        db.commit()
                else:
                    usuario = user_ws.user_name
                    user_completed = True

        if not user_ws:
            if usuario != '' and usuario != business_constants[business_code]["alias_user"]:
                user_completed = True
            new_user = User(user_number=user_number, user_name=usuario, user_whatsapp=user_whatsapp)
            db.add(new_user)
            db.commit()

            if user_whatsapp != '' and user_number != user_whatsapp:
                messages = db.query(Message).filter(Message.user_number == user_whatsapp).all()
                if len(messages) > 0:
                    for message in messages:
                        message.user_number = user_number
                        db.merge(message)
                    db.commit()
                if user_ws:
                    db.delete(user_ws)
                    db.commit()
    db.close()

    return {'number': user_number, 'whatsapp': whatsapp, 'usuario': usuario, 'user_completed': user_completed}


def update_user(user_number, user_name, business_code):
    # Ejecutamos la consulta para insertar un nuevo usuario
    db: Session = get_db_conn(business_code)

    user = User(user_number=user_number, user_name=user_name)
    db.merge(user)

    # Guardamos los cambios en la base de datos
    db.commit()

    # Cerramos la conexión y el cursor
    db.close()


def notify(notify_number, notify_whatsapp, notify_usuario, business_code):
    db: Session = get_db_conn(business_code)

    # Se busca un agente que este dispoible y lleve mas tiempo libre
    agent = db.query(Agent).filter(Agent.agent_active.is_(True) & Agent.agent_staff.is_(True)).order_by(
        Agent.agent_lastcall.asc()).first()
    if agent:
        agent_number = agent.agent_number
        agent_whatsapp = agent.agent_whatsapp
        agent_name = agent.agent_name
        """
        msg_count = 3
        alias_user = business_constants[business_code]["alias_user"]
        if alias_user != notify_usuario:
            alias_user = f'{alias_user} {notify_usuario}'
        agent_message = [
            f'Hola {agent_name}, el {alias_user} ha solicitado hablar con un {business_constants[business_code]["alias_expert"]}.']
        # Se le envía al agente las preguntas que el usuario realizó en el día de actual
        messages = db.query(Message).filter(Message.user_number == notify_number).order_by(Message.id.desc()).limit(
            msg_count).all()
        questions = [message.msg_sent for message in messages]
        if questions:
            if len(questions) > 1:
                agent_message.append(
                    f'A continuación te muestro los {len(questions)} útimos mesajes:')
                questions.reverse()
            else:
                agent_message.append(f'A continuación te muestro el útimo mesaje:')

            for question in questions:
                agent_message.append(question)

        if notify_whatsapp != '':
            agent_message.append(
                f'El número de contacto del {alias_user} es +{notify_whatsapp}.')

        send_text(agent_message, agent_whatsapp, business_code)
        """
        send_template(agent_name, agent_whatsapp, notify_usuario, notify_whatsapp, business_code)

        # Actualizar la hora de atención
        agent = db.query(Agent).filter(Agent.agent_number == agent_number).first()
        if agent:
            agent.agent_lastcall = datetime.now()
            db.merge(agent)
            # Guardamos los cambios en la base de datos
            db.commit()

    # Cerramos la conexión y el cursor
    db.close()


def notify_bug(business_def, business_msg, business_bug, business_code):
    db: Session = get_db_conn(business_code)
    agent = db.query(Agent).filter(Agent.agent_active.is_(True) & Agent.agent_super.is_(True)).first()
    db.close()

    # url = f'https://graph.facebook.com/v17.0/159540240573780/messages'
    # bearer = f'Bearer EABdgy5ZCsnccBOzrOq9CnnHjHPe9ZBCSJbr4xdsJtqFBFNRXCWKXkQeaiP8gvsZAAGtKZCEnWFzCHALZBEkEgPKJZAAZBjBR0kUIo0GZCZBgJQoOuwmZBacZB33THmuVjZAjVAfY2KU4Iw0ln1G6C3nFKNZBfflLMjmlNxw6hhyVsw81DDoBgLOSEXNcl6am67TO2d6DK'
    url = f'{business_constants[business_code]["whatsapp_url"]}{business_constants[business_code]["whatsapp_id"]}/messages'
    bearer = f'Bearer {business_constants[business_code]["whatsapp_token"]}'

    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": agent.agent_whatsapp,
        "type": "template",
        "template": {
            "name": "notificacion_error",
            "language": {
                "code": "es"
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": business_code
                        },
                        {
                            "type": "text",
                            "text": business_def
                        },
                        {
                            "type": "text",
                            "text": business_msg
                        },
                        {
                            "type": "text",
                            "text": business_bug
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

    # message = f'El siguiente error ha ocurrido en la aplicación {business_code}:\nFunción: {business_def}\nMensaje: {business_msg}\nError: {business_bug}'
    # send_text([message], agent.agent_whatsapp, business_code)


def send_messages(send_answer, send_notify, message_type, user_response, user_whatsapp, answers, agent, filename,
                  audio_awnser,
                  business_code):
    # Mensajes al usuario
    if send_answer:
        if message_type == 'text' or message_type == 'interactive':
            send_text(answers, user_whatsapp, business_code)
        else:
            answers_str = ' '.join(answers)
            send_voice(answers_str, user_whatsapp, agent, filename, business_code)
            if os.path.exists(audio_awnser):
                os.remove(audio_awnser)

        if send_notify:
            notify(user_response['number'], user_response['whatsapp'], user_response['usuario'],
                   business_code)


def send_text(answers, numberwa, business_code):
    mensajewa = WhatsApp(business_constants[business_code]["whatsapp_token"],
                         business_constants[business_code]["whatsapp_id"])
    # enviar los mensajes
    for answer in answers:
        mensajewa.send_message(message=answer, recipient_id=numberwa)


def send_template(agent_name, agent_whatsapp, user_name, user_whatsapp, business_code):
    # url = f'https://graph.facebook.com/v17.0/159540240573780/messages'
    # bearer = f'Bearer EABdgy5ZCsnccBOzrOq9CnnHjHPe9ZBCSJbr4xdsJtqFBFNRXCWKXkQeaiP8gvsZAAGtKZCEnWFzCHALZBEkEgPKJZAAZBjBR0kUIo0GZCZBgJQoOuwmZBacZB33THmuVjZAjVAfY2KU4Iw0ln1G6C3nFKNZBfflLMjmlNxw6hhyVsw81DDoBgLOSEXNcl6am67TO2d6DK'
    url = f'{business_constants[business_code]["whatsapp_url"]}{business_constants[business_code]["whatsapp_id"]}/messages'
    bearer = f'Bearer {business_constants[business_code]["whatsapp_token"]}'

    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": agent_whatsapp,
        "type": "template",
        "template": {
            "name": "notificacion_agente",
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
                            "text": user_name
                        },
                        {
                            "type": "text",
                            "text": user_whatsapp
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
    mensajewa = WhatsApp(constants.business_constants[business_code]["whatsapp_token"], constants.business_constants[business_code]["whatsapp_id"])
    componente = '{"type": "body","parameters": [{"type": "text","text": "' + agent_name + '"},{"type": "text","text": "' + user_name + '"},{"type": "text","text": "' + user_whatsapp + '"}]}'
    mensajewa.send_template('notificacion_agente', agent_whatsapp, components=[componente], lang="es")
    """


def send_voice(answers, numberwa, agent, filename, business_code):
    mensajewa = WhatsApp(business_constants[business_code]["whatsapp_token"],
                         business_constants[business_code]["whatsapp_id"])
    filename = f'answer_{filename}.mp3'
    media_received = get_media_recipient(business_code, numberwa, 'audio', 'received')
    audio_answer = os.path.join(os.getcwd(), f'{media_received}/{filename}')

    audio = generate(
        text=answers,
        voice='Rachel',
        model='eleven_multilingual_v1',
    )
    save(audio, audio_answer)

    audio_url = business_constants[business_code]["server_url"] + f'/{media_received}/{filename}'
    answers += f'{answers}\n{audio_url}'
    save_message(numberwa, '', answers, 'audio', 'whatsapp', agent, None, business_code)
    mensajewa.send_audio(audio=audio_url, recipient_id=numberwa)


def send_interactive(user_whatsapp, received, answered, message_type, agent, message_petition, topic_name,
                     petition_step, verify_data,
                     business_code):
    agent_notify = False
    petition_request = ''
    petition_steptype = ''
    answers = []
    if petition_step != 'agent':
        if petition_step != 'cancel':
            if message_petition != 'None':
                petition_number = message_petition
            else:
                petition_number = save_petition(user_whatsapp, topic_name, 1, petition_steptype,
                                                None, petition_request, business_code)

            workflow = get_workflow(business_code, petition_number, topic_name, petition_step, message_type,
                                    verify_data)
            if workflow['process_petition']:
                petition_step = workflow['step']
                petition_steptype = workflow['type']

                if not petition_steptype.startswith('finish'):
                    if petition_steptype == 'confirm':
                        workflow['text'] = f'{workflow["text"]}\n{received}'
                        tag = str(workflow["tag"]).strip()
                        if tag != '':
                            petition_request = f'{tag} {received}'

                    answers.append(workflow['text'])

                    petition_number = save_petition(user_whatsapp, topic_name, petition_step, petition_steptype,
                                                    None, petition_request, business_code)

                    payload = json_button(workflow)
                    send_json(user_whatsapp, payload, business_code)
                else:
                    petition_number = save_petition(user_whatsapp, topic_name, petition_step, petition_steptype,
                                                    'COM', '', business_code)
                    db: Session = get_db_conn(business_code)
                    petition = db.query(Petition).filter(Petition.petition_number == petition_number).first()
                    db.close()
                    answers.append(workflow['text'])
                    if petition_steptype == 'finish_req':
                        answers.append(petition.petition_request)
                    petition_number = None

                msg = ' '.join(answers)
            else:
                return {}
        else:
            petition_number = save_petition(user_whatsapp, topic_name, petition_step, 'cancel',
                                            'CAN', petition_request, business_code)
            if petition_number != '':
                msg = f'La solicitud {petition_number} fue cancelada. Si desea algo más, con gusto le ayudaré'
            else:
                msg = f'Si desea algo más, con gusto le ayudaré'
            answers.append(msg)
            petition_number = None
    else:
        agent_notify = True
        msg = answer_transfer_agent(business_code)
        answers.append(msg)
        petition_number = None

    if received == '':
        received = msg
    else:
        answered = msg

    save_message(user_whatsapp, received, answered, message_type, 'whatsapp', agent, petition_number, business_code)

    if not petition_steptype.startswith('finish') and petition_step != 'cancel' and petition_step != 'agent':
        send_answer = False
    else:
        send_answer = True

    return {'answers': answers, 'respond': send_answer, 'notify': agent_notify}


def send_json(numberwa, jsonwa, business_code):
    mensajewa = WhatsApp(business_constants[business_code]["whatsapp_token"],
                         business_constants[business_code]["whatsapp_id"])
    mensajewa.send_custom_json(recipient_id=numberwa, data=jsonwa)


def create_workflow(business_code, petition_number, workflow_name, workflow_step, workflow_values, workflow_process):
    db: Session = get_db_conn(business_code)
    topic = db.query(Topic).filter(Topic.topic_name == workflow_name).first()
    db.close()

    if topic is not None:
        prtition = topic.topic_description
    else:
        prtition = 'agent'

    buttons = []
    petition_steptype = workflow_values['TYPE']
    if not petition_steptype.startswith('finish'):
        button = {
            "type": "reply",
            "reply": {
                "id": f'[{workflow_name}][{petition_number}][{workflow_values["GOTOID1"].strip()}]',
                "title": workflow_values["BUTTON1"].strip()
            }
        }
        buttons.append(button)

        if workflow_values["BUTTON2"].strip() != 'nan' and workflow_values["GOTOID2"].strip() != 'nan':
            button = {
                "type": "reply",
                "reply": {
                    "id": f'[{workflow_name}][{petition_number}][{workflow_values["GOTOID2"].strip()}]',
                    "title": workflow_values["BUTTON2"].strip()
                }
            }
            buttons.append(button)

        if workflow_values["BUTTON3"].strip() != 'nan' and workflow_values["GOTOID3"].strip() != 'nan':
            button = {
                "type": "reply",
                "reply": {
                    "id": f'[{workflow_name}][{petition_number}][{workflow_values["GOTOID3"].strip()}]',
                    "title": workflow_values["BUTTON3"].strip()
                }
            }
            buttons.append(button)

    workflow = {'step': workflow_step, 'petition': prtition, 'process_petition': workflow_process,
                'buttons': buttons, 'text': workflow_values['TEXT'],
                'type': workflow_values['TYPE'], 'tag': workflow_values['TAG']}

    return workflow


def get_workflow(business_code, workflow_petition, workflow_name, workflow_step, workflow_type, workflow_verify):
    excel_values = get_row_values_excel(business_code, workflow_name, {'key': 'ID', 'value': workflow_step},
                                        ['NEXTID', 'TEXT', 'TYPE', 'TAG', 'BUTTON1', 'GOTOID1', 'BUTTON2', 'GOTOID2',
                                         'BUTTON3',
                                         'GOTOID3'])

    petition_steptype = excel_values[0]['TYPE']
    if not workflow_verify or petition_steptype == 'data':
        process_petition = True
    else:
        process_petition = False

    if workflow_type != 'interactive' and petition_steptype == 'data':
        workflow_step = format_step(excel_values[0]['NEXTID'])
        excel_values = get_row_values_excel(business_code, workflow_name, {'key': 'ID', 'value': workflow_step},
                                            ['TEXT', 'TYPE', 'TAG', 'BUTTON1', 'GOTOID1', 'BUTTON2', 'GOTOID2',
                                             'BUTTON3',
                                             'GOTOID3'])

    return create_workflow(business_code, workflow_petition, workflow_name, workflow_step, excel_values[0],
                           process_petition)


def get_catalog(business_code, catalog):
    excel_values = get_row_values_excel(business_code, catalog, None, ['id'])

    sections = []
    product_items = []
    for product_retailer in excel_values:
        product_items.append({"product_retailer_id": product_retailer['id']})

    section = {
        "title": "Catálogo",
        "product_items": product_items
    }
    sections.append(section)

    workflow = {'whatsapp_catalog': catalog, 'sections': sections}

    return workflow


def get_reply_info(query_message, query_number, query_origin, query_type, query_agent, business_code):
    reply = {}
    if query_origin == 'whatsapp':
        petition = get_petition_workflow(query_number, business_code)
        if petition is not None:
            reply = send_interactive(query_number, query_message, '', query_type,
                                     query_agent, petition.petition_number, petition.topic_name,
                                     petition.petition_step, True, business_code)
    return reply


def json_button(workflow):
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": workflow['text']
            },
            "action": {
                "buttons": workflow['buttons']
            }
        }
    }
    return payload


def json_product(product):
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "product",
            "body": {
                "text": "🛒 Carrito de compras"
            },
            "action": {
                "catalog_id": product['whatsapp_catalog'],
                "product_retailer_id": product['id']
            }
        }
    }
    return payload


def json_catalog(catalog):
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "product_list",
            "header": {
                "type": "text",
                "text": "🛒 Carrito de compras"
            },
            "body": {
                "text": "Lista de productos"
            },
            "action": {
                "catalog_id": catalog['whatsapp_catalog'],
                "sections": catalog['sections']
            }
        }
    }
    return payload


def json_list():
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "🛒 Carrito de compras"
            },
            "body": {
                "text": "Lista de los productos solicitados"
            },
            "action": {
                "button": "Lista de productos",
                "sections": [
                    {
                        "title": "SECTION_1_TITLE",
                        "rows": [
                            {
                                "id": "SECTION_1_ROW_1_ID",
                                "title": "SECTION_1_ROW_1_TITLE",
                                "description": "SECTION_1_ROW_1_DESCRIPTION"
                            },
                            {
                                "id": "SECTION_1_ROW_2_ID",
                                "title": "SECTION_1_ROW_2_TITLE",
                                "description": "SECTION_1_ROW_2_DESCRIPTION"
                            }
                        ]
                    },
                    {
                        "title": "SECTION_2_TITLE",
                        "rows": [
                            {
                                "id": "SECTION_2_ROW_1_ID",
                                "title": "SECTION_2_ROW_1_TITLE",
                                "description": "SECTION_2_ROW_1_DESCRIPTION"
                            },
                            {
                                "id": "SECTION_2_ROW_2_ID",
                                "title": "SECTION_2_ROW_2_TITLE",
                                "description": "SECTION_2_ROW_2_DESCRIPTION"
                            }
                        ]
                    }
                ]
            }
        }
    }
    return payload


def transcribe_audio(audio, api_key, business_code):
    if business_constants[business_code]["transcribe_api"] == 'openai':
        # Traductor de voz a texto openai whisper
        model_id = 'whisper-1'
        media_file = open(audio, 'rb')
        response = openai.Audio.transcribe(
            api_key=api_key,
            model=model_id,
            file=media_file
        )
        return response['text'].strip()
    else:
        # Traductor de voz a texto google
        recognizer = sr.Recognizer()

        # Carga el audio en el reconocedor
        with sr.AudioFile(audio) as source:
            audio_data = recognizer.record(source)

        # Realiza la transcripción utilizando el reconocedor de voz
        try:
            transcription = recognizer.recognize_google(audio_data)
            return transcription.strip()
        except sr.UnknownValueError:
            return ''
        except sr.RequestError as e:
            return ''


def get_language(query, anwers, business_code):
    lang_code = str(business_constants[business_code]['lang_code']).split('-')[1]
    languaje_query = get_completion(f'Responde cuál es el idioma del siguiente texto "{query}". ejemplo: "Español"',
                                    business_code)
    messages_lang = business_constants[business_code]["messages_lang"]
    if lang_code != languaje_query and languaje_query in messages_lang:
        languaje_anwer = get_completion(
            f'Responde cuál es el idioma del siguiente texto "{anwers}". ejemplo: "Español"',
            business_code)
        if languaje_query != languaje_anwer:
            return languaje_query

    return 'None'


def watting_agent(user_number, business_code):
    db: Session = get_db_conn(business_code)

    user = db.query(User).filter(User.user_number == user_number).first()
    if user.user_wait:
        last_message = db.query(Message).filter(Message.id == user.user_lastmsg).first()

        if last_message:
            current_datetime = datetime.now()
            time_difference = current_datetime - last_message.msg_date

            # Verificar si han pasado más de x minutos
            if time_difference < timedelta(minutes=business_constants[business_code]["messages_wait"]):
                return True
            else:
                user.user_wait = False
                db.merge(user)
                db.commit()

    db.close()
    return False


def empty_dir(dir_to_empty):
    files = os.listdir(dir_to_empty)
    for file in files:
        # Ruta completa del archivo
        file_url = os.path.join(dir_to_empty, file)
        # Verificar si es un archivo
        if os.path.isfile(file_url):
            # Eliminar el archivo
            os.remove(file_url)


def remove_file(file_url):
    # Verificar si es un archivo
    if os.path.isfile(file_url):
        # Eliminar el archivo
        os.remove(file_url)


def get_petition_workflow(user_number, business_code):
    petition = None
    db: Session = get_db_conn(business_code)
    user = db.query(User).filter(User.user_number == user_number).first()
    if user is not None:
        last_message = db.query(Message).filter(Message.id == user.user_lastmsg).first()
        if last_message is not None:
            petition = db.query(Petition).filter((Petition.petition_number == last_message.petition_number) &
                                                 (Petition.status_code == 'CRE')).order_by(
                Petition.petition_date.desc()).first()
    db.close()

    return petition


def format_step(petition_step):
    try:
        petition_step = float(petition_step)
        return str(int(petition_step))
    except ValueError:
        return petition_step


def download_media(business_code, user_whatsapp, media_data, media_type, idwa):
    media_id = media_data['id']
    media_ext = str(media_data['mime_type']).split('/')[1]
    # Directorio local de medias
    media = None
    filename = re.sub(r'\W', '', idwa)
    media_sent = get_media_recipient(business_code, user_whatsapp, media_type, 'sent')
    local_media = os.path.join(os.getcwd(), f'{media_sent}/')
    media_awnser = f'{local_media}answer_{filename}.{media_ext}'
    if not os.path.exists(media_awnser):
        # Obtener la url media de whatsapp
        media_url = f'{business_constants[business_code]["whatsapp_url"]}{media_id}/'
        response = requests.get(media_url, headers={
            'Authorization': f'Bearer {business_constants[business_code]["whatsapp_token"]}'})
        media_data = json.loads(response.content.decode('utf-8'))
        media_url = media_data['url']

        # Descargar media de whatsapp
        media = f'{local_media}{filename}.{media_ext}'
        response = requests.get(media_url, headers={
            'Authorization': f'Bearer {business_constants[business_code]["whatsapp_token"]}'})
        with open(media, 'wb') as file:
            file.write(response.content)

    return media


def answering_name(business_code, user_number, index_default):
    db: Session = get_db_conn(business_code)
    user = db.query(User).filter(User.user_number == user_number).first()
    last_message = db.query(Message).filter((Message.id == user.user_lastmsg) & (Message.msg_type == 'name')).first()
    db.close()

    if last_message is not None:
        return '1'

    return index_default
