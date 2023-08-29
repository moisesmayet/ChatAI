from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from backend import main
from backend.router.auth.auth_router import auth_required
from backend.model.model import Order, Product, Status
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session

order_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@order_app.get('/{business_code}/orders', response_class=HTMLResponse)
@auth_required
def orders_list(request: Request, business_code: str):
    db: Session = get_db_conn(business_code)
    orders = db.query(Order).order_by(Order.order_number.asc()).all()
    statuses = db.query(Status).all()
    db.close()
    return templates.TemplateResponse('dashboard/orders/orders.html', {'request': request, 'orders': orders, 'statuses': statuses, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@order_app.get('/{business_code}/orders/view/{order_number}', response_class=HTMLResponse)
@auth_required
def orders_view(request: Request, business_code: str, order_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        orders = db.query(Order).order_by(Order.order_number.asc()).all()
        order = db.query(Order).filter(Order.order_number == order_number).first()
        statuses = db.query(Status).all()
        db.close()
        return templates.TemplateResponse('dashboard/orders/orders_view.html', {'request': request, 'orders': orders, 'order': order, 'statuses': statuses, 'permission': permission, 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@order_app.get('/{business_code}/orders/{order_number}', response_class=HTMLResponse)
@auth_required
def orders_products(request: Request, business_code: str, order_number: str):
    db: Session = get_db_conn(business_code)
    orders = db.query(Order).order_by(Order.order_number.asc()).all()
    order_products = db.query(Product).filter(Product.order_number == order_number).all()
    statuses = db.query(Status).all()
    db.close()
    return templates.TemplateResponse('dashboard/orders/orders_products.html', {'request': request, 'orders': orders, 'order_products': order_products, 'statuses': statuses, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang')), 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})


@order_app.get('/{business_code}/orders/edit/{order_number}', response_class=HTMLResponse)
async def orders_edit(request: Request, business_code: str, order_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn(business_code)
        orders = db.query(Order).order_by(Order.order_number.asc()).all()
        order = db.query(Order).filter(Order.order_number == order_number).first()
        statuses = db.query(Status).all()
        db.close()

        language = eval(request.cookies.get('UserLang'))

        return templates.TemplateResponse('dashboard/orders/orders_edit.html', {'request': request, 'orders': orders, 'order': order, 'statuses': statuses, 'permission': permission, 'language': language, 'business_code': business_code, 'menu': eval(request.cookies.get('Menu')), 'business_code': business_code})

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))


@order_app.post('/{business_code}/orders/edit/{order_number}', response_class=HTMLResponse)
async def orders_edit(request: Request, business_code: str, order_number: str):
    if request.cookies.get('Permission') == 'super':
        form = await request.form()
        form = {field: form[field] for field in form}

        db: Session = get_db_conn(business_code)
        order = Order(order_number=order_number, status_code=form['status_code'], order_end=datetime.now())
        db.merge(order)
        db.commit()
        db.close()

        redirect = RedirectResponse(url=order_app.url_path_for('orders_list', business_code=business_code))
        redirect.status_code = 302
        return redirect

    return RedirectResponse(main.dashboard_app.url_path_for('signin', business_code=business_code))

