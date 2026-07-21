from django.db import transaction
from django.http import JsonResponse
from django.templatetags.static import static
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.serializers import CharField, IntegerField, ModelSerializer

from .models import Order, OrderProduct, Product


class OrderProductSerializer(ModelSerializer):
    quantity = IntegerField(source='amount')

    class Meta:
        model = OrderProduct
        fields = ['product', 'quantity']


class OrderSerializer(ModelSerializer):
    firstname = CharField(source='first_name')
    lastname = CharField(source='last_name')
    phonenumber = PhoneNumberField(source='phone_number')
    products = OrderProductSerializer(
        many=True, allow_empty=False, write_only=True
    )

    class Meta:
        model = Order
        fields = [
            'id',
            'firstname',
            'lastname',
            'phonenumber',
            'address',
            'products',
        ]


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
@transaction.atomic
def register_order(request):
    serializer = OrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    validated_data = serializer.validated_data

    order = Order.objects.create(
        first_name=validated_data['first_name'],
        last_name=validated_data['last_name'],
        phone_number=validated_data['phone_number'],
        address=validated_data['address'],
    )

    for position in validated_data['products']:
        OrderProduct.objects.create(
            order=order,
            product=position['product'],
            amount=position['amount'],
            price=position['product'].price,
        )

    response_serializer = OrderSerializer(order)
    return Response(response_serializer.data)
