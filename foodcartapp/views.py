from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from phonenumber_field.phonenumber import to_python
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
    validation_result = validate_product_field(request, 'products')
    if validation_result:
        return validation_result

    required_fields = ['firstname', 'lastname', 'address', 'phonenumber']
    validation_result = validate_string_fields(request, required_fields)
    if validation_result:
        return validation_result

    validation_result = validate_phonenumber(request, 'phonenumber')
    if validation_result:
        return validation_result

    validation_result = validate_products_exist(request, 'products')
    if validation_result:
        return validation_result

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


def validate_product_field(request, field):
    if field not in request.data:
        return Response(
            {field: 'Обязательное поле'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if request.data[field] is None:
        return Response(
            {field: 'Это поле не может быть пустым.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not isinstance(request.data[field], list):
        return Response(
            {field: 'Ожидался list, но получены другие данные'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not request.data[field]:
        return Response(
            {field: 'Этот список не может быть пустым'},
            status=status.HTTP_400_BAD_REQUEST,
        )


def validate_string_fields(request, string_fields):
    missing_fields = []
    null_fields = []
    for field in string_fields:
        if field not in request.data:
            missing_fields.append(field)
        elif request.data[field] is None or request.data[field] == '':
            null_fields.append(field)
        elif not isinstance(request.data[field], str):
            return Response(
                {field: ': Not a valid string'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif not request.data[field]:
            missing_fields.append(field)

    if null_fields:
        fields_str = ', '.join(null_fields)
        return Response(
            {fields_str: 'Это поле не может быть пустым'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if missing_fields:
        fields_str = ', '.join(missing_fields)
        return Response(
            {fields_str: 'Обязательное поле'},
            status=status.HTTP_400_BAD_REQUEST,
        )


def validate_phonenumber(request, field):
    phonenumber_str = request.data[field].strip()
    phonenumber = to_python(phonenumber_str)
    if not phonenumber.is_valid():
        return Response(
            {field: 'Введен некорректный номер телефона'},
            status=status.HTTP_400_BAD_REQUEST,
        )


def validate_products_exist(request, field):
    requested_products = request.data.get(field)
    existing_product_ids = Product.objects.values_list(flat=True)

    for position in requested_products:
        product_id = position.get('product')
        if product_id not in existing_product_ids:
            return Response(
                {field: f'Недопустимый первичный ключ "{product_id}"'},
                status=status.HTTP_400_BAD_REQUEST,
            )
