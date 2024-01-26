from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from backend import main
from backend.router.auth.auth_router import auth_required
from backend.model.model import Petition, Product, Status
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session

petition_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@petition_app.get('/{business_code}/petitions', response_class=HTMLResponse)
@auth_required
def petitions_list(request: Request, business_code: str):
    db: Session = get_db_conn(business_code)
    search = request.query_params.get('search', '')
    petitions = db.query(Petition).filter(Petition.user_number.like(f"%{search}%")).order_by(Petition.petition_date.desc()).all()
    statuses = db.query(Status).all()
    db.close()
    return templates.TemplateResponse('dashboard/petitions/petitions.html', {'request': request, 'petitions': petitions, 'statuses': statuses, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code, 'search': search})


@petition_app.get('/{business_code}/petitions/view/{petition_number}', response_class=HTMLResponse)
@auth_required
def petitions_view(request: Request, business_code: str, petition_number: str):
    permission = request.cookies.get('Permission')
    db: Session = get_db_conn(business_code)
    petitions = db.query(Petition).order_by(Petition.petition_date.desc()).all()
    petition = db.query(Petition).filter(Petition.petition_number == petition_number).first()
    statuses = db.query(Status).all()
    db.close()
    return templates.TemplateResponse('dashboard/petitions/petitions_view.html', {'request': request, 'petitions': petitions, 'petition': petition, 'statuses': statuses, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@petition_app.get('/{business_code}/petitions/edit/{petition_number}', response_class=HTMLResponse)
async def petitions_edit(request: Request, business_code: str, petition_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        petitions = db.query(Petition).order_by(Petition.petition_date.desc()).all()
        petition = db.query(Petition).filter(Petition.petition_number == petition_number).first()
        statuses = db.query(Status).all()
        db.close()

        language = eval(request.cookies.get('UserLang'))

        return templates.TemplateResponse('dashboard/petitions/petitions_edit.html', {'request': request, 'petitions': petitions, 'petition': petition, 'statuses': statuses, 'permission': permission, 'language': language, 'business_code': business_code, 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@petition_app.post('/{business_code}/petitions/edit/{petition_number}', response_class=HTMLResponse)
async def petitions_edit(request: Request, business_code: str, petition_number: str):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}

        db: Session = get_db_conn(business_code)
        petition = Petition(petition_number=petition_number, status_code=form['status_code'], petition_end=datetime.now())
        db.merge(petition)
        db.commit()
        db.close()

        redirect = RedirectResponse(url=petition_app.url_path_for('petitions_list', business_code=business_code))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))

