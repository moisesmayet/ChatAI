import json
import os
import shutil
from elevenlabs import set_api_key
from backend.config.db import get_db_conn, get_business, match_business_code_local, business_code_local
from sqlalchemy.orm import Session
from backend.model.model import Agent, Admin, Parameter, Topic, Behavior


def get_language(language_code, business_code):
    if match_business_code_local(business_code):
        business_code = 'admin'

    lang_file = f'backend/config/lang/{business_code}/{language_code}.json'
    if not os.path.exists(lang_file):
        lang_file = f'backend/config/lang/{business_code}/es-Español.json'

    with open(lang_file, 'r', encoding='utf8') as file:
        lang = json.load(file)

    if language_code == 'es-Español':
        lang.update({'language_name': 'en-English'})
        lang.update({'language_code': 'EN'})
    else:
        lang.update({'language_name': 'es-Español'})
        lang.update({'language_code': 'ES'})

    return lang


def get_lang_value(alias_name, alias_lang, business_code):
    lang_file = f'backend/config/lang/{business_code}/{alias_lang}.json'
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


def get_alias(alias_name, business_code):
    lang_values = {}

    value = get_lang_value(alias_name, 'es-Español', business_code)
    if value:
        lang_values.update(value)
    value = get_lang_value(alias_name, 'en-English', business_code)
    if value:
        lang_values.update(value)

    return lang_values


def refresh_alias(alias_lang, alias_name, alias_value, business_code):
    lang_file = f'backend/config/lang/{business_code}/{alias_lang}.json'
    # Leer el contenido del archivo JSON
    with open(lang_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Modificar el valor deseado en el diccionario
    data[alias_name] = alias_value

    # Escribir el diccionario modificado en el archivo JSON
    with open(lang_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)


def make_dirs(local_dir):
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)


def get_media_recipient(business_code, media_user, media_type, media_recipient):
    media_dir = f'{business_constants[business_code]["media_url"]}/{media_user}/{media_type}/{media_recipient}'
    if not os.path.exists(media_dir):
        os.makedirs(media_dir)
    return media_dir


def exists_business(business_code):
    if business_code in business_codes:
        return True
    else:
        return False


def is_catalog(business_code, topic_name):
    if topic_name in business_constants[business_code]['topic_catalogs']:
        return True
    else:
        return False


def is_workflow(business_code, topic_name):
    if topic_name in business_constants[business_code]['topic_workflows']:
        return True
    else:
        return False


def get_default_menu(business_code):
    if not match_business_code_local(business_code):
        return business_constants[business_code]["side_menu"]
    else:
        return {}


def get_default_hash(business_code):
    if not match_business_code_local(business_code):
        return business_constants[business_code]["algorithm_hash"]
    else:
        return 'HS256'


def get_business_catalog(business_code):
    if business_constants[business_code]["menu_orders"] == 'si':
        return business_constants[business_code]["whatsapp_catalog"]


def get_default_user(business_code, user_id):
    dbuser: Session = get_db_conn(business_code)
    if not match_business_code_local(business_code):
        user = dbuser.query(Agent).filter(Agent.agent_number == user_id).first()
    else:
        user = dbuser.query(Admin).filter(Admin.admin_user == user_id).first()
    dbuser.close()
    return user


def get_default_business_code():
    return business_code_local


business_codes = [business_code_local]
business_constants = {}
business_enables = get_business()
for business in business_enables:
    business_codes.append(business.business_code)

    # Directorio de persistencia del índice
    index_persist_dir = f'backend/data_index/{business.business_code}'
    make_dirs(index_persist_dir)

    # Directorio de prompt
    prompt_dir = f'backend/prompt/{business.business_code}'
    make_dirs(prompt_dir)

    # Directorio de media
    media_url = f'backend/media/{business.business_code}'
    make_dirs(media_url)

    # Cagar valores de la base de datos
    db: Session = get_db_conn(business.business_code)

    # OpenAI API key
    parameter = db.query(Parameter).filter(Parameter.parameter_name == 'openai_api_key').first()
    openai_api_key = parameter.parameter_value

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

    # menu
    side_menu = {}
    parameter = db.query(Parameter).filter(Parameter.parameter_name == 'menu_orders').first()
    if parameter.parameter_value == 'si':
        side_menu['menu_orders'] = True
    else:
        side_menu['menu_orders'] = False
    parameter = db.query(Parameter).filter(Parameter.parameter_name == 'menu_petitions').first()
    if parameter.parameter_value == 'si':
        side_menu['menu_petitions'] = True
    else:
        side_menu['menu_petitions'] = False

    # Whatsapp token
    parameter = db.query(Parameter).filter(Parameter.parameter_name == 'whatsapp_id').first()
    whatsapp_id = parameter.parameter_value
    parameter = db.query(Parameter).filter(Parameter.parameter_name == 'whatsapp_url').first()
    whatsapp_url = parameter.parameter_value
    parameter = db.query(Parameter).filter(Parameter.parameter_name == 'whatsapp_token').first()
    whatsapp_token = parameter.parameter_value

    # Modificar textos(audios y traducciones)
    parameter = db.query(Parameter).filter(Parameter.parameter_name == 'messages_wait').first()
    messages_wait = int(parameter.parameter_value)
    parameter = db.query(Parameter).filter(Parameter.parameter_name == 'messages_old').first()
    messages_old = int(parameter.parameter_value)
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
    topic_names = []
    topic_catalogs = []
    topic_workflows = []
    topic_list = {}
    topic_index = {}
    topic_context = ''
    topics = db.query(Topic).order_by(Topic.topic_order).all()
    topic_len = len(topics) - 1
    for i, item in enumerate(topics):
        topic = item.topic_name
        context_value = item.topic_context
        topic_context += f'", "<{i}>: ' + context_value.replace(',', f' \\')
        topic_names.append(topic)
        if item.type_code == 'CTG':
            topic_catalogs.append(topic)
        if item.type_code == 'WFW':
            topic_workflows.append(topic)
        topic_list[str(i)] = topic
        topic_index[topic] = ''
        directory = f'{index_persist_dir}/{topic}'
        exists_index = os.path.exists(directory)
        if item.topic_rebuild:
            # Si existe el directorio
            if exists_index:
                persist_dir = os.path.join(os.getcwd(), f'{index_persist_dir}/{topic}/')
                shutil.rmtree(persist_dir)
            else:
                os.makedirs(directory)
        else:
            if item.type_code == 'SYS' and exists_index:
                persist_dir = os.path.join(os.getcwd(), f'{index_persist_dir}/{topic}/')
                shutil.rmtree(persist_dir)

    subdirectories = next(os.walk(prompt_dir))[1]
    # Eliminar los directorios que no están en la lista de topics
    for subdir in subdirectories:
        if subdir not in topic_names:
            dir_to_delete = os.path.join(os.getcwd(), f'{prompt_dir}/{subdir}/')
            shutil.rmtree(dir_to_delete)

    topic_context += f'"'
    topic_context = topic_context.replace('{alias_ai}', alias_ai)
    topic_context = topic_context.replace('{alias_business}', alias_business)
    topic_context = topic_context.replace('{alias_expert}', alias_expert)
    topic_context = topic_context.replace('{alias_user}', alias_user)
    topic_context = topic_context.replace('{alias_item}', alias_item)
    topic_context = topic_context.replace('{alias_offer}', alias_offer)
    topic_context = topic_context.replace('{alias_order}', alias_order)
    if topic_context[:3] == '", ':
        topic_context = topic_context[3:]

    behavior = db.query(Behavior).filter(Behavior.behavior_code == 'USR').first()
    behavior_user = str(behavior.behavior_description)
    behavior_user = behavior_user.replace('{alias_ai}', alias_ai)
    behavior_user = behavior_user.replace('{alias_business}', alias_business)
    behavior_user = behavior_user.replace('{alias_expert}', alias_expert)
    behavior_user = behavior_user.replace('{alias_user}', alias_user)
    behavior_user = behavior_user.replace('{alias_item}', alias_item)
    behavior_user = behavior_user.replace('{alias_offer}', alias_offer)
    behavior_user = behavior_user.replace('{alias_order}', alias_order)

    behavior = db.query(Behavior).filter(Behavior.behavior_code == 'AGT').first()
    behavior_agent = str(behavior.behavior_description)
    behavior_agent = behavior_agent.replace('{alias_ai}', alias_ai)
    behavior_agent = behavior_agent.replace('{alias_business}', alias_business)
    behavior_agent = behavior_agent.replace('{alias_expert}', alias_expert)
    behavior_agent = behavior_user.replace('{alias_user}', alias_user)
    behavior_agent = behavior_user.replace('{alias_item}', alias_item)
    behavior_agent = behavior_user.replace('{alias_offer}', alias_offer)
    behavior_agent = behavior_user.replace('{alias_order}', alias_order)

    # Languaje
    parameter = db.query(Parameter).filter(Parameter.parameter_name == 'lang_code').first()
    lang_code = parameter.parameter_value

    db.close()

    business_constants[business.business_code] = {'openai_api_key': openai_api_key, 'algorithm_hash': algorithm_hash,
                                                  'openai_model': openai_model,
                                                  'openai_engine': openai_engine, 'server_url': server_url,
                                                  'server_key': server_key, 'lang_code': lang_code,
                                                  'whatsapp_id': whatsapp_id, 'whatsapp_url': whatsapp_url,
                                                  'whatsapp_token': whatsapp_token,
                                                  'messages_translator': messages_translator,
                                                  'messages_voice': messages_voice,
                                                  'messages_wait': messages_wait,
                                                  'messages_old': messages_old,
                                                  'transcribe_api': transcribe_api,
                                                  'transcribe_format': transcribe_format, 'alias_user': alias_user,
                                                  'alias_expert': alias_expert, 'alias_order': alias_order,
                                                  'alias_item': alias_item,
                                                  'topic_workflows': topic_workflows, 'topic_catalogs': topic_catalogs,
                                                  'topic_context': topic_context, 'topic_list': topic_list,
                                                  'topic_index': topic_index, 'side_menu': side_menu,
                                                  'behavior_user': behavior_user, 'behavior_agent': behavior_agent,
                                                  'messages_historical': messages_historical, 'alias_ai': alias_ai,
                                                  'index_persist_dir': index_persist_dir, 'prompt_dir': prompt_dir,
                                                  'media_url': media_url
                                                  }
