from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from backend.router.auth.auth_router import auth_required
from backend.model.model import Order, Product
from backend.config.db import get_db_conn
from sqlalchemy.orm import Session

order_app = APIRouter()

templates = Jinja2Templates(directory='./frontend/templates')


@order_app.get('/orders', response_class=HTMLResponse)
@auth_required
def orders_list(request: Request):
    db: Session = get_db_conn()
    orders = db.query(Order).order_by(Order.order_number.asc()).all()
    db.close()
    return templates.TemplateResponse('dashboard/orders/orders.html', {'request': request, 'orders': orders, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang'))})


@order_app.get('/orders/view/{order_number}', response_class=HTMLResponse)
@auth_required
def orders_view(request: Request, order_number: str):
    permission = request.cookies.get('Permission')
    if permission == 'super':
        db: Session = get_db_conn()
        orders = db.query(Order).order_by(Order.order_number.asc()).all()
        order = db.query(Order).filter(Order.order_number == order_number).first()
        db.close()
        return templates.TemplateResponse('dashboard/orders/orders_view.html', {'request': request, 'orders': orders, 'order': order, 'permission': permission, 'language': eval(request.cookies.get('UserLang'))})


@order_app.get('/orders/{order_number}', response_class=HTMLResponse)
@auth_required
def orders_products(request: Request, order_number: str):
    db: Session = get_db_conn()
    orders = db.query(Order).order_by(Order.order_number.asc()).all()
    order_products = db.query(Product).filter(Product.order_number == order_number).all()
    db.close()
    return templates.TemplateResponse('dashboard/orders/orders_products.html', {'request': request, 'orders': orders, 'order_products': order_products, 'permission': request.cookies.get('Permission'), 'language': eval(request.cookies.get('UserLang'))})

