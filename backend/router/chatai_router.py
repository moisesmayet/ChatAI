import csv
import json
import os
import re
import shutil
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
from sqlalchemy import func
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session
from backend.model.model import Agent, Message, Order, Product, Query, User
from backend.config.constants import openai_api_key, openai_model, openai_engine, server_url, server_key, media_url, \
    index_persist_dir, \
    whasapp_id, whasapp_url, whasapp_token, messages_translator, messages_voice, \
    transcribe_api, transcribe_format, alias_user, alias_expert, alias_order, alias_item, \
    topic_context, topic_list, topic_index, behavior_user, behavior_agent, messages_historical, alias_ai, messages_wait

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


@chatai_app.get('/createby')
async def createby():
    return {'message': f'ChatAI by Moisés Mayet'}


@chatai_app.get('/webhook/')
async def webhook_whatsapp(request: Request):
    # Verificamos con el token de acceso
    if request.query_params.get('hub.verify_token') == openai_api_key:
        challenge = request.query_params.get('hub.challenge')
        return PlainTextResponse(f'{challenge}')
    else:
        return 'Error de autenticación.'


@chatai_app.post('/webhook/')
async def webhook_whatsapp(request: Request):
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
            if message_type == 'text':
                # Obtener el texto del mensaje
                message = message_data[0]['text']['body'].strip()
            else:
                if messages_voice and message_type == 'audio':
                    # Directorio local de medias
                    filename = re.sub(r'\W', '', idwa)
                    local_media = os.path.join(os.getcwd(), f'{media_url}/{user_whatsapp}/')
                    audio_awnser = f'{local_media}anwser_{filename}.ogg'
                    if not os.path.exists(audio_awnser):
                        # Elimino el directorio
                        if os.path.exists(local_media):
                            # Eliminar el directorio y su contenido
                            shutil.rmtree(local_media)
                        else:
                            os.makedirs(local_media)

                        # Obtener la url media de whatsapp
                        audio_url = message_data[0]['audio']['id']
                        audio_url = f'{whasapp_url}{audio_url}/'
                        response = requests.get(audio_url, headers={'Authorization': f'Bearer {whasapp_token}'})
                        audio_data = json.loads(response.content.decode('utf-8'))
                        audio_url = audio_data['url']

                        # Descargar media de whatsapp
                        audio_ogg = f'{local_media}{filename}.ogg'
                        audio_text = f'{local_media}{filename}.{transcribe_format}'
                        response = requests.get(audio_url, headers={'Authorization': f'Bearer {whasapp_token}'})
                        with open(audio_ogg, 'wb') as file:
                            file.write(response.content)

                        ogg_file = os.path.join(media_url, audio_ogg)
                        pydub.AudioSegment.from_ogg(ogg_file).export(audio_text, format=transcribe_format)
                        audio_filename = os.path.join(media_url, audio_text)

                        # Realiza la transcripción del audio
                        message = transcribe_audio(audio_filename)

                        # Elimina los archivos de audio descargados
                        shutil.rmtree(local_media)

                        # Notificar que se va a escuchar el audio
                        send_text([f'Voy a escuchar el audio que me enviaste y en breve te respondo.'], user_whatsapp,
                                  idwa)
                else:
                    if message_type == 'order':
                        # Obtener el texto del mensaje
                        products = message_data[0]['order']['product_items']
                        save_order(user_whatsapp)
                        order_number = get_order(user_whatsapp)
                        for product in products:
                            price = product['item_price']
                            values = get_product_excel(product['product_retailer_id'])
                            values.append(price)
                            values.append(price)
                            values.append(product['currency'])
                            values.append('')
                            values.append('Unidad')
                            values.append(product['quantity'])
                            values.append(order_number)
                            save_product(values)

                        anwsers = f'Su orden de compra ({order_number}) fue enviada satisfactoriamente'
                        send_text([anwsers], user_whatsapp, idwa)
                        save_message(user_whatsapp, 'producto(s)', anwsers, idwa, message_type, 'whatsapp', datetime.now())
                        return JSONResponse({'status': 'success'}, status_code=200)
                    else:
                        if message_type != 'reaction':
                            anwsers = f'Solo puedo ayudarte si me escribes textos'
                            send_text([anwsers], user_whatsapp, idwa)
                            save_message(user_whatsapp, 'reacción', 'reacción', idwa, message_type, 'whatsapp', datetime.now())
                            return JSONResponse({'status': 'success'}, status_code=200)

            # Revisar que haya mensaje
            if len(message) > 0:
                user_response = create_user(user_whatsapp, user_whatsapp, alias_user)

                reply = reply_message(message, message_type, user_response['number'],
                                      user_response['usuario'], user_response['user_completed'], 'whatsapp', idwa)
                anwsers = reply['anwsers']

                # Mensajes al usuario
                if reply['respond']:
                    if message_type == 'text':
                        send_text(anwsers, user_whatsapp, idwa)
                    else:
                        anwsers_str = ' '.join(anwsers)
                        send_voice(anwsers_str, user_whatsapp, filename, idwa)
                        if os.path.exists(audio_awnser):
                            os.remove(audio_awnser)

                    if reply['notify']:
                        notify(user_response['number'], user_response['whatsapp'], user_response['usuario'], idwa)

                # Retornar la respuesto en un JSON
                return JSONResponse({'status': 'success'}, status_code=200)

    # No hay mensajes disponibles
    return JSONResponse({'status': 'no_messages'}, status_code=200)


@chatai_app.post('/webhookweb')
async def webhook_web(userid: UserId, username: UserName, userwhatsapp: UserWhatsapp, question: Question,
                      secretkey: SecretKey):
    if question.web_question != 'string' and question.web_question != '':
        if secretkey.web_secretkey == server_key:
            current_datetime = datetime.now()
            year = str(current_datetime.year)
            month = str(current_datetime.month).zfill(2)
            day = str(current_datetime.day).zfill(2)
            hour = str(current_datetime.hour).zfill(2)
            minute = str(current_datetime.minute).zfill(2)
            second = str(current_datetime.second).zfill(2)
            microsecond = str(current_datetime.microsecond).zfill(6)
            idwa = f'{userid.web_userid}-{year}{month}{day}{hour}{minute}{second}{microsecond}'

            user_response = create_user(userid.web_userid, userwhatsapp.web_userwhatsapp, username.web_username)

            reply = reply_message(question.web_question, 'text', user_response['number'], user_response['usuario'],
                                  user_response['user_completed'], 'web', idwa)
            anwser = ' '.join(reply['anwsers'])

            if reply['notify']:
                notify(user_response['number'], user_response['whatsapp'], user_response['usuario'], idwa)
        else:
            anwser = f'El chabot no tiene acceso al servidor desde {secretkey.web_secretkey}.'
    else:
        anwser = f'No pude procesar tu mensaje. Por favor, intenta hacer la pregunta de otra forma.'

    return Answer(web_answer=anwser)


@chatai_app.get("/backend/media/{filename:path}")
async def serve_media(filename: str):
    # Especifica la ruta del directorio donde se encuentran los archivos multimedia
    media_directory = "backend/media"

    # Utiliza la clase FileResponse para enviar el archivo multimedia
    file_path = f"{media_directory}/{filename}"
    return FileResponse(file_path)


def reply_message(message, message_type, number_user, usuario, user_completed, origin, idwa):
    anwsers = []
    agent_notify = False
    send_anwser = True

    # Conectamos a la base de datos
    db: Session = get_db_conn()

    # Verificar si es un agente
    agent = db.query(Agent).filter(Agent.agent_number == number_user).first()
    if agent is None:
        # Ejecutamos la consulta para obtener la cantidad de registros
        cantidad = db.query(Message).filter(Message.msg_code == idwa).count()
        if cantidad == 0:
            role_wa = 'user'
            agent_notify = False

            watting = watting_agent(number_user)
            if not watting:
                reply = get_anwser(message, role_wa, number_user, usuario, origin, idwa)
                anwsers.append(reply['anwser'])
                agent_notify = reply['notify']
                send_anwser = reply['send_anwser']

                # Verificar si tiene mensajes hoy
                cantidad = db.query(Message).filter(Message.user_number == number_user,
                                                    Message.msg_date == func.CURRENT_DATE()).count()
                if cantidad == 0 and not user_completed:
                    anwsers.append(
                        f'Mi nombre es {alias_ai} y estaré aquí para cualquier información que necesites. Me gustaría saber como te llamas.')
                anwsers_str = ' '.join(anwsers)
            else:
                origin = 'agent'
                anwsers_str = ''

            save_message(number_user, message, anwsers_str.strip(), idwa, message_type, origin, datetime.now())
    else:
        usuario = agent.agent_name
        # Ejecutamos la consulta para obtener la cantidad de registros
        cantidad = db.query(Query).filter(Query.query_code == idwa).count()
        if cantidad == 0:
            role_wa = 'agents'
            reply = get_anwser(message, role_wa, number_user, usuario, origin, idwa)
            anwsers.append(reply['anwser'])
            agent_notify = reply['notify']
            send_anwser = reply['send_anwser']

            # Ejecutamos la consulta para insertar un nuevo registro de mesaje
            anwsers_str = ' '.join(anwsers)
            new_query = Query(agent_number=number_user, query_sent=message,
                              query_received=anwsers_str.strip(), query_code=idwa, query_type=message_type,
                              query_origin=origin, query_date=datetime.now())
            db.add(new_query)
            db.commit()

    # Cerramos la conexión y el cursor
    db.close()

    # Retornar status
    return {'anwsers': anwsers, 'respond': send_anwser, 'notify': agent_notify}


def get_anwser(query_message, query_role, query_number, query_usuario, query_origin, query_idwa):
    agent_notify = False
    if query_message.strip() != '':
        if query_role == 'user':
            behavior = behavior_user
        else:
            behavior = behavior_agent
        if query_usuario is None or query_usuario == '':
            behavior = behavior.replace('{alias_user}', alias_user)
        else:
            behavior = behavior.replace('{alias_user}', query_usuario)

        anwser = ''
        index_context = get_index(query_message, topic_context, 'None')
        if index_context != 'None' and query_role != 'agents':
            if index_context != '0' and index_context != '1':
                key_topic = topic_list[index_context]
                if key_topic == 'items':
                    if query_origin == 'whatsapp':
                        payload = json_catalog()
                        send_json(query_number, payload, query_idwa)
                        anwser = f'Con gusto aquí le mostramos nuestro catálogo'
                    else:
                        anwser = f'Si desea adquirir un {alias_item}, le recomendamos escribir al WhatsApp para enviarle nuestro catálogo'
                    return {'anwser': anwser, 'send_anwser': True, 'notify': agent_notify}

                if anwser == '':
                    behavior += f'Basándote en la siguiente información de contexto.\\\n{{context_str}}\\\n'
                    behavior += f'Responde el siguiente texto: "{{query_str}}"\\\n'
                    qa_template = Prompt(behavior)
                    query_index = get_query_index(key_topic)
                    anwser = query_index.as_query_engine(text_qa_template=qa_template).query(query_message).response

                if anwser != '':
                    anwser = anwser.replace('\\n', '\\\n')
                    anwser = anwser.replace('\\', '')
                else:
                    anwser = f'No pude procesar tu mensaje. Por favor, intenta hacer la pregunta de otra forma.'
            else:
                if index_context == '0':
                    prompt = f'Responde 1 si el texto es un pedido o solicitud. Reponde 0 si el texto es una pregunta\\\nTexto: "{query_message}"'
                    sentence = get_completion(prompt)
                    if sentence == '1':
                        anwser = f'Ya realicé la notificación para que te atienda un {alias_expert}.\n'
                        anwser += f'En unos minutos uno de nuestros representantes te brindará asistencia.\n'
                        anwser += f'Fue un placer para mi atenderte.'
                        agent_notify = True
                    else:
                        anwser = get_chatcompletion(behavior, query_message, query_number, query_role)
                else:
                    user_name = get_completion(
                        f'''Extrae el nombre de la persona del texto y si no hay nombre contesta "None": {query_message}''')
                    if user_name != 'None':
                        update_user(query_number, user_name)
                        anwser = f'{user_name}, es un placer. ¿En qué puedo ayudarte?'
                    else:
                        anwser = get_chatcompletion(behavior, query_message, query_number, query_role)
        else:
            anwser = ''
            if query_role == 'agent':
                topic_order = f'"<1> Información del {alias_user}", "<2> Información de mensajes"'
                sentence = get_index(query_message, topic_order, '0')
                if sentence != '0':
                    number = get_completion(
                        f'''Extrae el número telefónico del texto y si no hay número contesta "None": {query_message}''')
                    if number != 'None':
                        number = str(number).replace('+', '')
                        if number.isdigit():
                            if sentence == '1':
                                db: Session = get_db_conn()
                                user = db.query(User).filter(User.user_number == number).first()
                                if user:
                                    anwser = f'El número pertenece al {alias_user} {user.user_name}'
                                db.close()
                            else:
                                if sentence == '2':
                                    cantidad = get_completion(
                                        f'''Extrae la cantidad de mensajes del texto y si no hay cantidad contesta "1": {query_message}''')
                                    if cantidad.isdigit():
                                        db: Session = get_db_conn()
                                        messages = db.query(Message).filter(Message.user_number == number).order_by(
                                            Message.id.desc()).limit(cantidad).all()
                                        for message in messages:
                                            anwser += f'[{message.msg_date}] {message.msg_sent}\n{message.msg_received}\n'
                                        db.close()

            if anwser == '':
                anwser = get_chatcompletion(behavior, query_message, query_number, query_role)

            if anwser != '':
                anwser = anwser.replace('\\n', '\\\n')
                anwser = anwser.replace('\\', '')
            else:
                anwser = f'No pude procesar tu mensaje. Por favor, intenta hacer la pregunta de otra forma.'
    else:
        anwser = f'Parece que tu mensaje está vacío. Por favor, intenta hacer la pregunta de otra forma.'

    if messages_translator:
        language = get_language(anwser, query_message)
        if language != 'None':
            anwser = get_promptcompletion(
                f'Debes traducir siguiente texto "{anwser}" al {language} y dar solo la traducción como respuesta.')
            anwser = re.findall(r'"([^"]*)"', anwser)
            anwser = anwser[0]

    return {'anwser': anwser, 'send_anwser': True, 'notify': agent_notify}


def get_query_index(key_topic):
    if not topic_index[key_topic]:
        # Cargar los datos del directorio "prompt" y almacenarlos en caché
        documents = SimpleDirectoryReader(f'backend/prompt/{key_topic}').load_data()
        modelo = LLMPredictor(llm=ChatOpenAI(temperature=0.2, model_name=openai_model))
        service_context = ServiceContext.from_defaults(llm_predictor=modelo)
        index_storage = GPTVectorStoreIndex.from_documents(documents, service_context=service_context)
        index_storage.storage_context.persist(persist_dir=f'{index_persist_dir}/{key_topic}')
        topic_index[key_topic] = index_storage
        return index_storage

    return topic_index[key_topic]


def get_index(query, options, index_default):
    prompt = f'Buscar el elemento de la lista tiene mayor similitud al texto: "{query}"\n\nOptions:\n{options}\nSi no encuentra relación responde ""\nEjemplo:<1> El sol'
    index_context = get_promptcompletion(prompt)
    index = re.findall(r"(\d+)", index_context)
    if len(index) == 1:
        index = index[0]
        if index.isdigit():
            if int(index) <= len(topic_list):
                return index

    return index_default


def get_promptcompletion(prompt):
    messages = [{'role': 'user', 'content': prompt}]
    response = openai.ChatCompletion.create(
        model=openai_model,
        messages=messages,
        n=1,
        temperature=0,
    )
    return response.choices[0].message['content']


def get_chatcompletion(behavior, question, user_number, role):
    messages = [{"role": "system", "content": behavior}]
    if messages_historical > 0:
        db: Session = get_db_conn()
        if role == 'user':
            role_messages = db.query(Message).filter(Message.user_number == user_number).order_by(
                Message.id.desc()).limit(messages_historical).all()
            role_messages = sorted(role_messages, key=lambda x: x.id)
            for message in role_messages:
                messages.append({"role": "user", "content": message.msg_sent})
                messages.append({"role": "assistant", "content": message.msg_received})
        else:
            role_queries = db.query(Query).filter(Query.agent_number == user_number).order_by(Query.id.desc()).limit(
                messages_historical).all()
            role_queries = sorted(role_queries, key=lambda x: x.id)
            for query in role_queries:
                messages.append({"role": "user", "content": query.query_sent})
                messages.append({"role": "assistant", "content": query.query_received})
        db.close()
    messages.append({"role": "user", "content": question})

    response = openai.ChatCompletion.create(
        model=openai_model,
        messages=messages,
        temperature=0.3,
        n=1,
        stop=None
    )

    return response.choices[0].message.content.strip()


def get_completion(prompt):
    response = openai.Completion.create(
        engine=openai_engine,
        prompt=prompt,
        temperature=0.3,
        n=1,
        stop=None
    )

    return response.choices[0].text.strip()


def get_order(number_user):
    # Ejecutamos la consulta para encontrar una orden
    db: Session = get_db_conn()

    order = db.query(Order).filter(Order.user_number == number_user, Order.status_code == 'CRE').order_by(Order.order_start.desc()).first()

    # Cerramos la conexión y el cursor
    db.close()

    if order:
        return order.order_number
    else:
        return '0'


def save_message(msg_number, msg_sent, msg_received, msg_code, msg_type, msg_origin, msg_date):
    # Ejecutamos la consulta para insertar un nueva orden
    db: Session = get_db_conn()

    # Ejecutamos la consulta para insertar un nuevo registro de mesaje
    new_message = Message(user_number=msg_number, msg_sent=msg_sent,
                          msg_received=msg_received, msg_code=msg_code, msg_type=msg_type,
                          msg_origin=msg_origin, msg_date=msg_date)
    db.add(new_message)
    db.commit()


def save_order(number_user):
    # Ejecutamos la consulta para insertar un nueva orden
    db: Session = get_db_conn()

    new_order = Order(user_number=number_user, status_code='CRE', order_start=datetime.now())
    db.add(new_order)
    db.commit()

    # Cerramos la conexión y el cursor
    db.close()


def save_product(product):
    # Ejecutamos la consulta para insertar un nuevo producto
    db: Session = get_db_conn()

    product_code = product[0]
    order_number = product[9]
    product_amount = product[8]
    cantidad = count_product(order_number, product_code)
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


def update_product(order_number, product_code, product_amount):
    # Ejecutamos la consulta para actuaizar un producto
    db: Session = get_db_conn()

    cantidad = count_product(order_number, product_code)
    if cantidad > 0:
        product = db.query(Product).filter_by(product_code=product_code, order_number=order_number).first()
        product.product_amount = product_amount

        # Guardamos los cambios en la base de datos
        db.commit()

    # Cerramos la conexión y el cursor
    db.close()

    if cantidad > 0:
        return f'Se actualizó el {alias_item} de tu {alias_order}.'
    else:
        return f'No existe el {alias_item}({product_code}) de tu {alias_order}.'


def get_product(order_number):
    # Ejecutamos la consulta para obtener un producto
    db: Session = get_db_conn()
    result = ''
    products = db.query(Product).filter_by(order_number=order_number)
    for product in products:
        result = f'{alias_item}: {product.product_name}({product.product_code}), precio: {product.product_payment}$'
        if product.product_offer != '':
            result += f'({product.product_offer})'
        result += f', cantidad: {product.product_amount}({product.product_measure})\n'

    # Cerramos la conexión y el cursor
    db.close()

    if result != '':
        return f'{alias_order}: \n{result}'
    else:
        return f'No tenemos registros de {alias_item}s que hayas solicitado.'


def get_product_excel(product_code):
    dir_excel = os.path.join(os.getcwd(), 'backend/prompt/items/')
    files = os.listdir(dir_excel)

    for file in files:
        # Ruta completa del archivo
        file_path = os.path.join(dir_excel, file)
        # Verificar si es un archivo
        if os.path.isfile(file_path):
            file_ext = os.path.splitext(file_path)[1]
            if file_ext.lower() in ['.xls', '.xlsx']:
                excel_data = pd.read_excel(file_path, skiprows=1)  # Saltar la primera fila
                for index, row in excel_data.iterrows():
                    if str(row['id']) == str(product_code):
                        valor = [str(row['id']), row['title'], row['description']]
                        return valor
    return []


def get_product_csv(product_code):
    dir_csv = os.path.join(os.getcwd(), f'backend/prompt/items/')
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
                    for row in reader:
                        if row['id'] == product_code:
                            valor = [row['id'], row['title'], row['description'], row['price']]
                            return valor
    return []


def count_product(order_number, product_code):
    # Ejecutamos la consulta para actuaizar un producto
    db: Session = get_db_conn()

    cantidad = db.query(Product).filter_by(order_number=order_number, product_code=product_code).count()

    # Cerramos la conexión y el cursor
    db.close()

    return cantidad


def delete_product(order_number, product_code):
    # Ejecutamos la consulta para eliminar un producto
    db: Session = get_db_conn()

    cantidad = count_product(order_number, product_code)
    if cantidad > 0:
        product = db.query(Product).filter_by(product_code=product_code, order_number=order_number).first()
        if product:
            db.delete(product)

        # Guardamos los cambios en la base de datos
        db.commit()

    # Cerramos la conexión y el cursor
    db.close()

    if cantidad > 0:
        return f'Se eliminó el {alias_item} de tu {alias_order}.'
    else:
        return f'No se encontró el {alias_item} en tu {alias_order}.'


def create_user(user_number, user_whatsapp, user_name):
    usuario = user_name
    whatsapp = user_whatsapp
    user_completed = False

    # Ejecutamos la consulta para insertar un nuevo usuario
    db: Session = get_db_conn()

    user = db.query(User).filter(User.user_number == user_number).first()
    if user:
        if user.user_whatsapp == '':
            if user_whatsapp != '':
                user.user_whatsapp = user_whatsapp
                db.merge(user)
                db.commit()
        else:
            whatsapp = user.user_whatsapp
            user_ws = db.query(User).filter(User.user_number == whatsapp, User.user_whatsapp == whatsapp).first()
            if user_ws:
                other_user = db.query(User).filter(User.user_number != whatsapp, User.user_whatsapp == whatsapp).first()
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
        if user.user_name != '' and user.user_name != alias_user:
            usuario = user.user_name
            user_completed = True
        else:
            if usuario != '' and usuario != alias_user:
                user_completed = True
                usuario = user_name
                user.user_name = user_name
                db.merge(user)
                db.commit()
    else:
        # Verificar si ya existia un usuario diferente con ese whatsapp
        user_ws = None
        if user_whatsapp != '':
            user_ws = db.query(User).filter(User.user_number != user_number,
                                            User.user_whatsapp == user_whatsapp).first()
            if user_ws:
                user_number = user_ws.user_number
                if user_ws.user_name == '':
                    if usuario != '' and usuario != alias_user:
                        user_completed = True
                        user_ws.user_name = usuario
                        db.merge(user_ws)
                        db.commit()
                else:
                    usuario = user_ws.user_name
                    user_completed = True

        if not user_ws:
            if usuario != '' and usuario != alias_user:
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


def update_user(user_number, user_name):
    # Ejecutamos la consulta para insertar un nuevo usuario
    db: Session = get_db_conn()

    user = User(user_number=user_number, user_name=user_name)
    db.merge(user)

    # Guardamos los cambios en la base de datos
    db.commit()

    # Cerramos la conexión y el cursor
    db.close()


def notify(notify_number, notify_whatsapp, notify_usuario, notify_idwa):
    db: Session = get_db_conn()

    # Se busca un agente que este dispoible y lleve mas tiempo libre
    agent = db.query(Agent).filter(Agent.agent_active.is_(True)).order_by(Agent.agent_lastcall.asc()).first()
    if agent:
        agent_number = agent.agent_number
        agent_whatsapp = agent.agent_whatsapp
        agent_name = agent.agent_name
        msg_count = 3
        agent_message = [
            f'Hola {agent_name}, el {alias_user} {notify_usuario} ha solicitado hablar con un {alias_expert}.']

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
            agent_message.append(f'El número de contacto del {alias_user} {notify_usuario} es +{notify_whatsapp}.')

        send_text(agent_message, agent_whatsapp, notify_idwa)

        # Actualizar la hora de atención
        agent = db.query(Agent).filter(Agent.agent_number == agent_number).first()
        if agent:
            agent.agent_lastcall = datetime.now()
            db.merge(agent)
            # Guardamos los cambios en la base de datos
            db.commit()

    # Cerramos la conexión y el cursor
    db.close()


def send_text(anwsers, numberwa, idwa):
    mensajewa = WhatsApp(whasapp_token, whasapp_id)
    # enviar los mensajes
    for anwser in anwsers:
        mensajewa.send_message(message=anwser, recipient_id=numberwa)
    # mensajewa.mark_as_read(idwa)


def send_voice(anwsers, numberwa, filename, idwa):
    mensajewa = WhatsApp(whasapp_token, whasapp_id)
    filename = f'anwser_{filename}.mp3'
    audio_anwser = os.path.join(os.getcwd(), f'{media_url}/{numberwa}/{filename}')
    audio = generate(
        text=anwsers,
        voice='Rachel',
        model='eleven_multilingual_v1',
    )
    save(audio, audio_anwser)

    audio_url = server_url + f"/{media_url}/{numberwa}/{filename}"
    mensajewa.send_audio(audio=audio_url, recipient_id=numberwa)
    # mensajewa.mark_as_read(idwa)


def send_json(numberwa, jsonwa, idwa):
    mensajewa = WhatsApp(whasapp_token, whasapp_id)
    mensajewa.send_custom_json(recipient_id=numberwa, data=jsonwa)
    # mensajewa.mark_as_read(idwa)


def json_button():
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "BUTTON_TEXT"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "UNIQUE_BUTTON_ID_1",
                            "title": "BUTTON_TITLE_1"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "UNIQUE_BUTTON_ID_2",
                            "title": "BUTTON_TITLE_2"
                        }
                    }
                ]
            }
        }
    }
    return payload


def json_product():
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "product",
            "body": {
                "text": "optional body text"
            },
            "action": {
                "catalog_id": "693805289237308",
                "product_retailer_id": "2345678901"
            }
        }
    }
    return payload


def json_catalog():
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
                "catalog_id": "693805289237308",
                "sections": [
                    {
                        "title": "Audio y Video",
                        "product_items": [
                            {"product_retailer_id": "4567890123"},
                            {"product_retailer_id": "5678901234"},
                            {"product_retailer_id": "6789012345"},
                        ]
                    },
                    {
                        "title": "Computación",
                        "product_items": [
                            {"product_retailer_id": "3456789012"},
                            {"product_retailer_id": "7890123456"},
                            {"product_retailer_id": "8901234567"},
                            {"product_retailer_id": "9012345678"},
                        ]
                    },
                    {
                        "title": "Teléfonos y Tablets",
                        "product_items": [
                            {"product_retailer_id": "1234567890"},
                            {"product_retailer_id": "2345678901"},
                        ]
                    }
                ]
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


def transcribe_audio(audio):
    if transcribe_api == 'openai':
        # Traductor de voz a texto openai whisper
        model_id = 'whisper-1'
        media_file = open(audio, 'rb')
        response = openai.Audio.transcribe(
            api_key=openai_api_key,
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
            return f'No se escucha bien la nota de voz.'
        except sr.RequestError as e:
            return f'En este momento no podemos atender notas de voz.'


def get_language(query, anwers):
    language = get_completion(f'Responde "None" si el idioma texto "{query}" es igual al idioma del texto "{anwers}"')
    if language != 'None':
        language = get_completion(f'Responde cuál es el idioma del siguiente texto "{query}". ejemplo: "Español"')
    return language


def watting_agent(user_number):
    db: Session = get_db_conn()

    user = db.query(User).filter(User.user_number == user_number).first()
    if user.user_wait:
        last_message = db.query(Message).filter(
            Message.user_number == user_number,
            Message.id == user.use_lastmsg
        ).order_by(Message.id.asc()).first()

        if last_message:
            current_datetime = datetime.now()
            time_difference = current_datetime - last_message.msg_date

            # Verificar si han pasado más de x minutos
            if time_difference < timedelta(minutes=messages_wait):
                return True
            else:
                user.user_wait = False
                db.merge(user)
                db.commit()

    db.close()

    return False
