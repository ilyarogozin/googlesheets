import datetime
import re

from django.core.exceptions import ValidationError
from django.db import models


def validate_delivery_date(value):
    """Проверяем соответствие даты формату 01.01.1111 и актуальность времени доставки"""
    exp = r'^(\d{2})\.(\d{2})\.(\d{4})$'
    if bool(re.match(exp, value)):
        order_date = datetime.datetime.strptime(value, '%d.%m.%Y').date()
        now_date = datetime.date.today()
        if order_date > now_date:
            return value
        raise ValidationError('Дата не может быть в прошлом.')
    raise ValidationError(
        f'Дата - {value} в неправильном формате, должна быть: 01.01.1111'
    )


class Order(models.Model):
    num_order = models.PositiveIntegerField(verbose_name='Номер заказа')
    price_usd = models.PositiveIntegerField(verbose_name='Цена в долларах')
    price_rub = models.PositiveIntegerField(verbose_name='Цена в рублях')
    delivery_date = models.CharField(
        verbose_name='Дата доставки',
        max_length=10,
        validators=[validate_delivery_date]
    )
    # этот атрибут нужен чтобы не отправлять сообщение об истечении
    # срока доставки несколько раз, устанавливаем False, когда срок истёк
    is_tracked = models.BooleanField(verbose_name='Отслеживаемый', default=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
