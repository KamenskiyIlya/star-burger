from collections import defaultdict

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Case, IntegerField, Prefetch, Value, When
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from requests.exceptions import RequestException

from foodcartapp.models import (
    Order,
    OrderProduct,
    Product,
    Restaurant,
    RestaurantMenuItem,
)
from utils.geocoding import calculate_distance, get_coordinates


class Login(forms.Form):
    username = forms.CharField(
        label='Логин',
        max_length=75,
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Укажите имя пользователя',
            }
        ),
    )
    password = forms.CharField(
        label='Пароль',
        max_length=75,
        required=True,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Введите пароль'}
        ),
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={'form': form})

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(
            request,
            "login.html",
            context={
                'form': form,
                'ivalid': True,
            },
        )


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {
            item.restaurant_id: item.availability
            for item in product.menu_items.all()
        }
        ordered_availability = [
            availability.get(restaurant.id, False)
            for restaurant in restaurants
        ]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(
        request,
        template_name="products_list.html",
        context={
            'products_with_restaurant_availability': products_with_restaurant_availability,
            'restaurants': restaurants,
        },
    )


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(
        request,
        template_name="restaurants_list.html",
        context={
            'restaurants': Restaurant.objects.all(),
        },
    )


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = (
        Order.objects.exclude(status='COMPLETE')
        .get_order_price()
        .select_related('restaurant')
        .prefetch_related(
            Prefetch(
                'products',
                queryset=OrderProduct.objects.select_related('product'),
            )
        )
        .annotate(
            status_order=Case(
                When(status='NEW', then=Value(1)),
                When(status='COOKING', then=Value(2)),
                When(status='DELIVER', then=Value(3)),
                default=Value(4),
                output_field=IntegerField(),
            )
        )
        .order_by('status_order', '-id')
    )

    all_product_ids = set()
    order_with_products = {}

    for order in orders:
        product_ids = [
            position.product_id for position in order.products.all()
        ]
        order_with_products[order.id] = product_ids
        all_product_ids.update(product_ids)

    menu_items = RestaurantMenuItem.objects.filter(
        product_id__in=all_product_ids,
        availability=True,
    ).values_list('product_id', 'restaurant_id')

    restaurants_by_product = defaultdict(set)
    for product_id, restaurant_id in menu_items:
        restaurants_by_product[product_id].add(restaurant_id)

    order_available_restaurant_ids = {}
    all_restaurant_ids = set()

    for order in orders:
        product_ids = order_with_products.get(order.id, [])

        if not product_ids:
            order_available_restaurant_ids[order.id] = []
            continue

        restaurants_not_cook = False
        for product_id in product_ids:
            if product_id not in restaurants_by_product:
                restaurants_not_cook = True
                break

        if restaurants_not_cook:
            order_available_restaurant_ids[order.id] = []
            continue

        available_restaurants_id_sets = [
            restaurants_by_product[product_id] for product_id in product_ids
        ]
        available_restaurants_ids = set.intersection(
            *available_restaurants_id_sets
        )

        order_available_restaurant_ids[order.id] = list(
            available_restaurants_ids
        )
        all_restaurant_ids.update(available_restaurants_ids)

    restaurant_by_id = {
        restaurant.id: restaurant
        for restaurant in Restaurant.objects.filter(id__in=all_restaurant_ids)
    }

    yandex_token = settings.YANDEX_GEOCODER_API_KEY

    for order in orders:
        restaurant_ids = order_available_restaurant_ids.get(order.id, [])
        restaurants = [
            restaurant_by_id[restaurant_id]
            for restaurant_id in restaurant_ids
            if restaurant_id in restaurant_by_id
        ]

        order_coords = None
        try:
            order_coords = get_coordinates(yandex_token, order.address)
        except RequestException as e:
            print(f'Ошибка геокодера для заказа {order.id}: {e}')
            order.restaurants_with_distance = []

        restaurants_with_distance = []
        for restaurant in restaurants:
            restaurant_coords = None
            try:
                restaurant_coords = get_coordinates(
                    yandex_token, restaurant.address
                )
            except RequestException as e:
                print(f'Ошибка геокодера для заказа {order.id}: {e}')
                order.restaurants_with_distance = []

            distance = None
            if order_coords and restaurant_coords:
                distance = calculate_distance(order_coords, restaurant_coords)

            restaurants_with_distance.append(
                {
                    'restaurant': restaurant,
                    'distance': distance,
                }
            )

        restaurants_with_distance.sort(
            key=lambda restaurant: (
                restaurant['distance'] is None,
                restaurant['distance'] or 0,
            )
        )
        order.restaurants_with_distance = restaurants_with_distance

    return render(
        request,
        template_name='order_items.html',
        context={
            'orders': orders,
        },
    )
