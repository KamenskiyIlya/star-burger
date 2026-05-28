from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Sum
from phonenumber_field.modelfields import PhoneNumberField


class OrderQuerySet(models.QuerySet):
    def get_order_price(self):

        return self.annotate(
            total_price=Sum(F('products__price') * F('products__amount'))
        )


class Restaurant(models.Model):
    name = models.CharField('название', max_length=50)
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = RestaurantMenuItem.objects.filter(
            availability=True
        ).values_list('product')
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField('название', max_length=50)

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField('название', max_length=50)
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    image = models.ImageField('картинка')
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=250,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже', default=True, db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [['restaurant', 'product']]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class Order(models.Model):
    ORDER_STATUSES = {
        'NEW': 'Новый',
        'COOKING': 'Готовится',
        'DELIVER': 'Доставляется',
        'COMPLETE': 'Завершен',
    }
    PAYMENT_METHODS = {
        'NON_CASH': 'Безналичный',
        'CASH': 'Наличными',
    }

    first_name = models.CharField(
        max_length=50, verbose_name='Имя', null=False
    )
    last_name = models.CharField(
        max_length=50, verbose_name='Фамилия', null=False
    )
    phone_number = PhoneNumberField(verbose_name='Телефон', db_index=True)
    address = models.CharField(
        max_length=200,
        verbose_name='Адрес доставки',
        null=False,
        db_index=True,
    )
    status = models.CharField(
        verbose_name='Статус заказа',
        max_length=20,
        choices=ORDER_STATUSES,
        default='NEW',
        db_index=True,
    )
    comment = models.TextField(
        verbose_name='Комментарий к заказу', blank=True, default=''
    )

    created_at = models.DateTimeField(
        verbose_name='Время регистрации заказа',
        auto_now_add=True,
        db_index=True,
    )
    called_at = models.DateTimeField(
        verbose_name='Время звонка',
        db_index=True,
        blank=True,
        null=True,
    )
    delivered_at = models.DateTimeField(
        verbose_name='Время доставки',
        db_index=True,
        blank=True,
        null=True,
    )

    payment_method = models.CharField(
        max_length=20,
        verbose_name='Способ оплаты',
        choices=PAYMENT_METHODS,
        blank=True,
        null=True,
        db_index=True,
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f'Заказ #{self.id} - {self.phone_number} - {self.first_name}'


class OrderProduct(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='products'
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='orders'
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(0), MaxValueValidator(15)],
    )
    price = models.DecimalField(
        verbose_name='Цена на момент заказа',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = 'Продукт в заказе'
        verbose_name_plural = 'Продукты в заказе'
