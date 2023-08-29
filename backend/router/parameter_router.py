import glob
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend import main
from backend.config import constants
from backend.router.auth.auth_router import auth_required
from backend.model.model import Parameter
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session

parameter_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@parameter_app.get('/{business_code}/parameters', response_class=HTMLResponse)
@auth_required
def parameters_list(request: Request, business_code: str):
    db: Session = get_db_conn(business_code)
    parameters = db.query(Parameter).order_by(Parameter.parameter_name.asc()).all()
    db.close()
    return templates.TemplateResponse('dashboard/parameters/parameters.html', {'request': request, 'parameters': parameters, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@parameter_app.get('/{business_code}/parameters/view/{parameter_name}', response_class=HTMLResponse)
@auth_required
def parameters_view(request: Request, business_code: str, parameter_name: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        parameters = db.query(Parameter).order_by(Parameter.parameter_name.asc()).all()
        parameter = db.query(Parameter).filter(Parameter.parameter_name == parameter_name).first()
        db.close()

        language = eval(request.cookies.get('UserLang'))
        combo_values = {}
        lang_alias = {}
        alias = parameter_name.split('_')
        if alias[0] == 'alias':
            lang_alias = constants.get_alias(alias[1], business_code)
        else:
            combo_values = get_combo(language, parameter_name, parameter.parameter_value)

        return templates.TemplateResponse('dashboard/parameters/parameters_view.html', {'request': request, 'parameters': parameters, 'parameter': parameter, 'lang_alias': lang_alias, 'combo_values': combo_values, 'permission': permission, 'language': language, 'business_code': business_code, 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@parameter_app.get('/{business_code}/parameters/new', response_class=HTMLResponse)
async def parameters_new(request: Request, business_code: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        parameters = db.query(Parameter).order_by(Parameter.parameter_name.asc()).all()
        db.close()
        return templates.TemplateResponse('dashboard/parameters/parameters_new.html', {'request': request, 'parameters': parameters, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@parameter_app.post('/{business_code}/parameters/new', response_class=HTMLResponse)
async def parameters_new(request: Request, business_code: str):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}

        db: Session = get_db_conn(business_code)
        new_parameter = Parameter(parameter_name=form['parameter_name'], parameter_value=form['parameter_value'])
        db.add(new_parameter)
        db.commit()
        db.close()

        redirect = RedirectResponse(url=parameter_app.url_path_for('parameters_list', business_code=business_code))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@parameter_app.get('/{business_code}/parameters/edit/{parameter_name}', response_class=HTMLResponse)
async def parameters_edit(request: Request, business_code: str, parameter_name: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        parameters = db.query(Parameter).order_by(Parameter.parameter_name.asc()).all()
        parameter = db.query(Parameter).filter(Parameter.parameter_name == parameter_name).first()
        db.close()

        language = eval(request.cookies.get('UserLang'))
        combo_values = {}
        lang_alias = {}
        alias = parameter_name.split('_')
        if alias[0] == 'alias':
            lang_alias = constants.get_alias(alias[1], business_code)
        else:
            combo_values = get_combo(language, parameter_name, parameter.parameter_value)

        return templates.TemplateResponse('dashboard/parameters/parameters_edit.html', {'request': request, 'parameters': parameters, 'parameter': parameter, 'lang_alias': lang_alias, 'combo_values': combo_values, 'permission': permission, 'language': language, 'business_code': business_code, 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@parameter_app.post('/{business_code}/parameters/edit/{parameter_name}', response_class=HTMLResponse)
async def parameters_edit(request: Request, business_code: str, parameter_name: str):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}
        if 'parameter_value' in form:
            value = form['parameter_value']
        else:
            if 'alias_value' in form:
                value = form['alias_value']

                alias = parameter_name.split('_')
                alias_s = alias[1]
                alias_p = f'{alias[1]}s'
                if 'alias_es_s' in form:
                    constants.refresh_alias('es-Español', alias_s, form['alias_es_s'], business_code)
                if 'alias_es_p' in form:
                    constants.refresh_alias('es-Español', alias_p, form['alias_es_p'], business_code)
                if 'alias_en_s' in form:
                    constants.refresh_alias('en-English', alias_s, form['alias_en_s'], business_code)
                if 'alias_en_p' in form:
                    constants.refresh_alias('en-English', alias_p, form['alias_en_p'], business_code)
            else:
                value = form['combo_value']

        db: Session = get_db_conn(business_code)
        parameter = Parameter(parameter_name=parameter_name, parameter_value=value)
        db.merge(parameter)
        db.commit()
        db.close()

        constants.business_constants[business_code][parameter_name] = value

        redirect = RedirectResponse(url=parameter_app.url_path_for('parameters_list', business_code=business_code))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


def get_combo(language, parameter_name, parameter_value):
    combo_values = []
    if parameter_name == 'lang_code':
        combo_values = get_language_names(parameter_value)
    else:
        if parameter_name == 'business_constants[business_code]["messages_translator"]' or parameter_name == 'business_constants[business_code]["messages_voice"]' or parameter_name.startswith('menu_'):
            if parameter_value == 'si':
                combo_values.append({'value': 'si', 'name': language['yes'], 'selected': True})
                combo_values.append({'value': 'no', 'name': language['no'], 'selected': False})
            else:
                combo_values.append({'value': 'si', 'name': language['yes'], 'selected': False})
                combo_values.append({'value': 'no', 'name': language['no'], 'selected': True})
        else:
            if parameter_name == 'business_constants[business_code]["transcribe_api"]':
                if parameter_value == 'openai':
                    combo_values.append({'value': 'openai', 'name': 'openai', 'selected': True})
                    combo_values.append({'value': 'google', 'name': 'google', 'selected': False})
                else:
                    combo_values.append({'value': 'openai', 'name': 'openai', 'selected': False})
                    combo_values.append({'value': 'google', 'name': 'google', 'selected': True})

    return combo_values


def get_language_names(parameter_value):
    lang_names = []
    language_list = glob.glob("backend/config/lang/*.json")
    for lang in language_list:
        filename = lang.split('\\')
        filename = filename[1].split('.')[0]
        lang_name = filename.split('-')
        if filename != parameter_value:
            lang_names.append({'value': filename, 'name': lang_name[1], 'selected': False})
        else:
            lang_names.append({'value': filename, 'name': lang_name[1], 'selected': True})

    return lang_names
