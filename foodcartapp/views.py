from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Order, OrderProduct, Product


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse(
        [
            {
                'title': 'Burger',
                'src': static('burger.jpg'),
                'text': 'Tasty Burger at your door step',
            },
            {
                'title': 'Spices',
                'src': static('food.jpg'),
                'text': 'All Cuisines',
            },
            {
                'title': 'New York',
                'src': static('tasty.jpg'),
                'text': 'Food is incomplete without a tasty dessert',
            },
        ],
        safe=False,
        json_dumps_params={
            'ensure_ascii': False,
            'indent': 4,
        },
    )


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            }
            if product.category
            else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            },
        }
        dumped_products.append(dumped_product)
    return JsonResponse(
        dumped_products,
        safe=False,
        json_dumps_params={
            'ensure_ascii': False,
            'indent': 4,
        },
    )


@api_view(['POST'])
def register_order(request):
    if 'products' not in request.data:
        return Response(
            {'products': 'Не заполнено обязательное поле products'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(request.data['products'], list):
        return Response(
            {'products': 'Поле products должно быть списком'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not request.data['products']:
        return Response(
            {'products': 'Поле products не может быть пустым'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        order_data = request.data

        order = Order.objects.create(
            first_name=order_data['firstname'],
            last_name=order_data['lastname'],
            phone_number=order_data['phonenumber'],
            address=order_data['address'],
        )

        products_in_order = []
        total_order_price = 0
        for position in order_data.get('products', []):
            product_id = position['product']
            amount = position['quantity']

            product = get_object_or_404(Product, id=product_id)

            total_position_price = amount * product.price
            total_order_price += total_position_price

            products_in_order.append(
                {
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_price': product.price,
                    'amount': amount,
                    'total_position_price': total_position_price,
                }
            )

            OrderProduct.objects.create(
                order=order,
                product=product,
                amount=amount,
            )

        finally_order_data = {
            'order_id': order.id,
            'first_name': order.first_name,
            'last_name': order.last_name,
            'phone_number': str(order.phone_number),
            'address': order.address,
            'products': products_in_order,
            'total_price': total_order_price,
        }

        return Response(finally_order_data)

    except ValueError:
        return JsonResponse(
            {
                'error': 'ValueError',
            }
        )
