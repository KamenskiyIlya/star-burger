from django.contrib import admin
from django.shortcuts import reverse
from django.templatetags.static import static
from django.utils.html import format_html

from .models import (
    Order,
    OrderProduct,
    Product,
    ProductCategory,
    Restaurant,
    RestaurantMenuItem,
)


class RestaurantMenuItemInline(admin.TabularInline):
    model = RestaurantMenuItem
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    search_fields = [
        'name',
        'address',
        'contact_phone',
    ]
    list_display = [
        'name',
        'address',
        'contact_phone',
    ]
    inlines = [RestaurantMenuItemInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'get_image_list_preview',
        'name',
        'category',
        'price',
    ]
    list_display_links = [
        'name',
    ]
    list_filter = [
        'category',
    ]
    search_fields = [
        # FIXME SQLite can not convert letter case for cyrillic words properly, so search will be buggy.
        # Migration to PostgreSQL is necessary
        'name',
        'category__name',
    ]

    inlines = [RestaurantMenuItemInline]
    fieldsets = (
        (
            'Общее',
            {
                'fields': [
                    'name',
                    'category',
                    'image',
                    'get_image_preview',
                    'price',
                ]
            },
        ),
        (
            'Подробно',
            {
                'fields': [
                    'special_status',
                    'description',
                ],
                'classes': ['wide'],
            },
        ),
    )

    readonly_fields = [
        'get_image_preview',
    ]

    class Media:
        css = {"all": (static("admin/foodcartapp.css"))}

    def get_image_preview(self, obj):
        if not obj.image:
            return 'выберите картинку'
        return format_html(
            '<img src="{url}" style="max-height: 200px;"/>', url=obj.image.url
        )

    get_image_preview.short_description = 'превью'

    def get_image_list_preview(self, obj):
        if not obj.image or not obj.id:
            return 'нет картинки'
        edit_url = reverse('admin:foodcartapp_product_change', args=(obj.id,))
        return format_html(
            '<a href="{edit_url}"><img src="{src}" style="max-height: 50px;"/></a>',
            edit_url=edit_url,
            src=obj.image.url,
        )

    get_image_list_preview.short_description = 'превью'


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    extra = 0
    readonly_fields = ['price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'phone_number',
        'address',
        'first_name',
        'last_name',
        'total_price_display',
    ]
    list_display_links = [
        'id',
        'phone_number',
    ]
    readonly_fields = [
        'total_price_display',
    ]
    inlines = [OrderProductInline]
    search_fields = ['id', 'phone_number', 'address']

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.price = instance.product.price
            instance.save()
        formset.save_m2m()

    def total_price_display(self, obj):
        total_price = sum(
            position.price * position.amount for position in obj.products.all()
        )
        return f'{total_price} руб.'

    total_price_display.short_description = 'Общая сумма'


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    pass
