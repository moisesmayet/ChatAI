from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.router.auth.auth_router import auth_required
from backend.model.model import Business
from backend.config.db import get_local_db_conn
from sqlalchemy.orm import Session

business_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@business_app.get('/admin/business', response_class=HTMLResponse)
@auth_required
def business_list(request: Request):
    db: Session = get_local_db_conn()
    business_all = db.query(Business).order_by(Business.business_code.asc()).all()
    db.close()
    return templates.TemplateResponse('admin/business/business.html',
                                      {'request': request, 'business_all': business_all,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@business_app.get('/admin/business/view/{business_id}', response_class=HTMLResponse)
@auth_required
def business_view(request: Request, business_id: str):
    db: Session = get_local_db_conn()
    business_all = db.query(Business).order_by(Business.business_code.asc()).all()
    business = db.query(Business).filter(Business.business_code == business_id).first()
    db.close()
    return templates.TemplateResponse('admin/business/business_view.html',
                                      {'request': request, 'business_all': business_all, 'business': business,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@business_app.get('/admin/business/new', response_class=HTMLResponse)
async def business_new(request: Request):
    db: Session = get_local_db_conn()
    business_all = db.query(Business).order_by(Business.business_code.asc()).all()
    db.close()
    return templates.TemplateResponse('admin/business/business_new.html',
                                      {'request': request, 'business_all': business_all,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@business_app.post('/admin/business/new', response_class=HTMLResponse)
async def business_new(request: Request):
    form = await request.form()
    form = {field: form[field] for field in form}

    db: Session = get_local_db_conn()
    new_business = Business(business_code=form['business_code'], business_description=form['business_description'])
    db.add(new_business)
    db.commit()
    db.close()

    redirect = RedirectResponse(url=business_app.url_path_for('business_list'))
    redirect.status_code = 302
    return redirect


@business_app.get('/admin/business/edit/{business_id}', response_class=HTMLResponse)
async def business_edit(request: Request, business_id: str):
    db: Session = get_local_db_conn()
    business_all = db.query(Business).order_by(Business.business_code.asc()).all()
    business = db.query(Business).filter(Business.business_code == business_id).first()
    db.close()
    return templates.TemplateResponse('admin/business/business_edit.html',
                                      {'request': request, 'business_all': business_all, 'business': business,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@business_app.post('/admin/business/edit/{business_id}', response_class=HTMLResponse)
async def business_edit(request: Request, business_id: str):
    form = await request.form()
    form = {field: form[field] for field in form}

    db: Session = get_local_db_conn()
    business = Business(business_code=business_id, business_description=form['business_description'])
    db.merge(business)
    db.commit()
    db.close()

    redirect = RedirectResponse(url=business_app.url_path_for('business_list'))
    redirect.status_code = 302
    return redirect


@business_app.get('/admin/business/delete/{business_id}', response_class=HTMLResponse)
async def business_delete(request: Request, business_id: str):
    db: Session = get_local_db_conn()
    business_all = db.query(Business).order_by(Business.business_code.asc()).all()
    business = db.query(Business).filter(Business.business_code == business_id).first()
    db.close()
    return templates.TemplateResponse('admin/business/business_delete.html',
                                      {'request': request, 'business_all': business_all, 'business': business,
                                       'language': eval(request.cookies.get('UserLang')),
                                       'menu': eval(request.cookies.get('Menu'))})


@business_app.post('/admin/business/delete/{business_id}', response_class=HTMLResponse)
async def business_delete(request: Request, business_id: str):
    db: Session = get_local_db_conn()
    business = db.query(Business).filter(Business.business_code == business_id).first()
    db.delete(business)
    db.commit()
    db.close()

    redirect = RedirectResponse(url=business_app.url_path_for('business_list'))
    redirect.status_code = 302
    return redirect
