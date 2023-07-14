import json
import os
import openai
from elevenlabs import set_api_key

import backend.main
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session
from backend.model.model import Parameter, Topic, Behavior

# Directorio de persistencia del índice
index_persist_dir = f'backend/data_index'

# Directorio de media
media_url = f'backend/media'


def empty_dir(dir_to_empty):
    files = os.listdir(dir_to_empty)
    for del_file in files:
        # Ruta completa del archivo
        file_url = os.path.join(dir_to_empty, del_file)
        # Verificar si es un archivo
        if os.path.isfile(file_url):
            # Eliminar el archivo
            os.remove(file_url)


def agregar_plural(palabra, idioma):
    vocales = ['a', 'e', 'i', 'o', 'u']
    consonantes_especiales = ['s', 'x', 'z']

    if idioma == 'es-Español':
        if palabra[-1] in vocales:
            palabra_plural = palabra + 's'
        elif palabra[-1] in consonantes_especiales:
            palabra_plural = palabra + 'es'
        else:
            palabra_plural = palabra + 'es'
    else:
        # Si no es idioma español, devolver la palabra sin cambios
        palabra_plural = palabra

    return palabra_plural


def get_language(language_code):
    lang_file = f'backend/config/lang/{language_code}.json'
    if not os.path.exists(lang_file):
        lang_file = f'backend/config/lang/es-Español.json'

    with open(lang_file, 'r', encoding='utf8') as file:
        lang = json.load(file)

    if language_code == 'es-Español':
        lang.update({'language_name': 'en-English'})
        lang.update({'language_code': 'EN'})
    else:
        lang.update({'language_name': 'es-Español'})
        lang.update({'language_code': 'ES'})

    return lang


def get_lang_value(alias_name, alias_lang):
    lang_file = f'backend/config/lang/{alias_lang}.json'
    code = alias_lang.split('-')
    # Leer el contenido del archivo JSON
    with open(lang_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    lang_pairs = {}

    if alias_name in data:
        lang_pairs.update({f'{code[0]}_s': data[alias_name]})

    alias_name = f'{alias_name}s'
    if alias_name in data:
        lang_pairs.update({f'{code[0]}_p': data[alias_name]})

    return lang_pairs


def get_alias(alias_name):
    lang_values = {}

    value = get_lang_value(alias_name, 'es-Español')
    if value:
        lang_values.update(value)
    value = get_lang_value(alias_name, 'en-English')
    if value:
        lang_values.update(value)

    return lang_values


def refresh_alias(alias_lang, alias_name, alias_value):
    lang_file = f'backend/config/lang/{alias_lang}.json'
    # Leer el contenido del archivo JSON
    with open(lang_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Modificar el valor deseado en el diccionario
    data[alias_name] = alias_value

    # Escribir el diccionario modificado en el archivo JSON
    with open(lang_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)


# Cagar valores de la base de datos
db: Session = get_db_conn()

# OpenAI API key
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'openai_api_key').first()
openai_api_key = parameter.parameter_value
os.environ['OPENAI_API_KEY'] = openai_api_key
openai.api_key = openai_api_key

# OpenAI Model
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'openai_model').first()
openai_model = parameter.parameter_value
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'openai_engine').first()
openai_engine = parameter.parameter_value

# Eleven Labs API key
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'eleven_api_key').first()
set_api_key(parameter.parameter_value)

# Server
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'server_key').first()
server_key = parameter.parameter_value
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'server_url').first()
server_url = parameter.parameter_value

# encript
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'algorithm_hash').first()
algorithm_hash = parameter.parameter_value

# Whasapp token
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'whasapp_id').first()
whasapp_id = parameter.parameter_value
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'whasapp_url').first()
whasapp_url = parameter.parameter_value
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'whasapp_token').first()
whasapp_token = parameter.parameter_value

# Modificar textos(audios y traducciones)
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'messages_wait').first()
messages_wait = int(parameter.parameter_value)
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'transcribe_api').first()
transcribe_api = parameter.parameter_value
transcribe_format = f'mp3' if transcribe_api == 'openai' else f'wav'
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'messages_historical').first()
messages_historical = int(parameter.parameter_value)
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'messages_translator').first()
messages_translator = str(parameter.parameter_value)
if messages_translator.lower() == 'si':
    messages_translator = True
else:
    messages_translator = False
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'messages_voice').first()
messages_voice = str(parameter.parameter_value)
if messages_voice.lower() == 'si':
    messages_voice = True
else:
    messages_voice = False

# Alias
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'alias_user').first()
alias_user = parameter.parameter_value
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'alias_expert').first()
alias_expert = parameter.parameter_value
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'alias_order').first()
alias_order = parameter.parameter_value
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'alias_item').first()
alias_item = parameter.parameter_value
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'alias_offer').first()
alias_offer = parameter.parameter_value
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'alias_ai').first()
alias_ai = parameter.parameter_value
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'alias_business').first()
alias_business = parameter.parameter_value

# Limpiar directorios
topic_list = {}
topic_index = {}
topic_context = ''
topics = db.query(Topic).order_by(Topic.topic_order).all()
topic_len = len(topics) - 1
for i, item in enumerate(topics):
    topic = item.topic_name
    context_value = item.topic_context
    topic_context += f'", "<{i}>: ' + context_value.replace(',', f' \\')
    topic_list[str(i)] = topic
    topic_index[topic] = ''
    if item.topic_rebuild:
        directory = f'{index_persist_dir}/{topic}'
        # Si existe el directorio
        if os.path.exists(directory):
            persist_dir = os.path.join(os.getcwd(), f'{index_persist_dir}/{topic}/')
            empty_dir(persist_dir)
        else:
            os.makedirs(directory)
topic_context += f'"'
topic_context = topic_context.replace('{alias_order}', alias_order)
topic_context = topic_context.replace('{alias_item}', alias_item)
topic_context = topic_context.replace('{alias_offer}', alias_offer)
topic_context = topic_context.replace('{alias_expert}', alias_expert)
if topic_context[:3] == '", ':
    topic_context = topic_context[3:]

behavior = db.query(Behavior).filter(Behavior.behavior_code == 'USR').first()
behavior_user = str(behavior.behavior_description)
behavior_user = behavior_user.replace('{alias_ai}', alias_ai)
behavior_user = behavior_user.replace('{alias_business}', alias_business)
behavior_user = behavior_user.replace('{alias_expert}', alias_expert)
behavior = db.query(Behavior).filter(Behavior.behavior_code == 'AGT').first()
behavior_agent = str(behavior.behavior_description)
behavior_agent = behavior_agent.replace('{alias_ai}', alias_ai)
behavior_agent = behavior_agent.replace('{alias_business}', alias_business)
behavior_agent = behavior_agent.replace('{alias_expert}', alias_expert)

# Languaje
parameter = db.query(Parameter).filter(Parameter.parameter_name == 'lang_code').first()
lang_code = parameter.parameter_value

db.close()
