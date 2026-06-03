from django.db import models


class GeoPoint(models.Model):
    address = models.CharField(
        verbose_name='Адрес',
        max_length=200,
        unique=True,
    )
    lon = models.FloatField(
        verbose_name='Долгота',
    )
    lat = models.FloatField(
        verbose_name='Широта',
    )

    last_updated = models.DateTimeField(
        verbose_name='Дата последнего обновления',
        auto_now=True,
    )

    class Meta:
        verbose_name = 'Сохраненные координаты'
        verbose_name_plural = 'Сохраненные координаты'

    def __str__(self):
        return f'{self.address} ({self.lon}, {self.lat})'
