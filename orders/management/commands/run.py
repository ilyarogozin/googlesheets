import datetime
import logging
import os
import sys
import time

import httplib2
import telegram
from apiclient import discovery
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from pycbrf.toolbox import ExchangeRates

from orders.models import Order

load_dotenv()

# файл, полученный в Google Developer Console,
# для авторизации в google sheets api
CREDENTIALS_FILE = 'creds.json'

# ID Google Sheets документа (можно взять из его URL)
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

# ID телеграм чата, куда нужно отправлять сообщение
# (установите свой id чата(посмотрите его, отправив сообщение телеграм боту t.me/userinfobot) для теста в .env файл
# и активируйте бота t.me/GoogleSheetsTestMyBot, чтобы отправка сообщений заработала)
CHAT_ID = os.getenv('CHAT_ID')

# токен для получения экземпляра телеграм бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

MESSAGE_SENT_SUCCESSFULLY = 'Сообщение "{}" отправлено успешно'
FAILURE_IN_PROGRAM = 'Сбой в работе программы: {}'
ERROR_SENDING_MESSAGE = 'Ошибка при отправке сообщения: {}'
ORDER_IS_DELETED = 'Заказ с id={} удалён.'
DELIVERY_TIME_EXPIRED = 'Срок доставки заказа {} истёк.'


def send_message(bot, message):
            """Отправляет в Telegram сообщение."""
            try:
                bot.send_message(
                    chat_id=CHAT_ID,
                    text=message
                )
            except telegram.error.TelegramError as error:
                logging.exception(ERROR_SENDING_MESSAGE.format(error))
            else:
                logging.info(MESSAGE_SENT_SUCCESSFULLY.format(message))


class Command(BaseCommand):
    def handle(self, *args, **options):
        logging.basicConfig(
            level=logging.INFO,
            format=('%(asctime)s [%(levelname)s] %(name)s,'
                    ' line %(lineno)d, %(message)s'),
            handlers=[logging.StreamHandler(stream=sys.stdout),
                      logging.FileHandler(filename=__file__ + '.log')]
        )

        class SendMessageError(Exception):
            """Кастомная ошибка при неотправленном сообщении."""
            pass

        # получаем экземпляр нашего телеграм бота
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        # авторизуемся и получаем service — экземпляр доступа к API
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_FILE,
            ['https://www.googleapis.com/auth/spreadsheets',
             'https://www.googleapis.com/auth/drive']
        )
        http_auth = credentials.authorize(httplib2.Http())
        service = discovery.build('sheets', 'v4', http=http_auth, cache_discovery=False)
        # читаем google таблицу каждые 5 минут
        # и смотрим измения/добавления/удаления строк
        while True:
            try:
                # читаем google таблицу
                table = service.spreadsheets().values().get(
                    spreadsheetId=SPREADSHEET_ID,
                    range='A2:E1000',
                    majorDimension='ROWS'
                ).execute()
                # собираем айдишники заказов в таблице, чтобы потом сравнить наличие их в БД
                table_ids = set()
                for order_id, num_order, price, delivery_date in table['values']:
                    table_ids.add(int(order_id))
                    # смотрим, есть ли этот заказ в БД, если нет, то добавляем
                    try:
                        order = Order.objects.get(id=order_id)
                    except Order.DoesNotExist:
                        # устанавливаем цену в рублях на основании актуального курса ЦБ
                        rates = ExchangeRates(str(datetime.date.today()))
                        price_rub = int(price) * int(rates['USD'].value)
                        Order.objects.create(
                            id=order_id,
                            num_order=num_order,
                            price_usd=price,
                            price_rub=price_rub,
                            delivery_date=delivery_date
                        )
                        # сразу переходим на следующую итерацию
                        continue
                    # смотрим, есть ли изменения заказа в гугл таблице, если да,
                    # то изменяем его в БД тоже
                    if order.num_order != num_order:
                        order.num_order = num_order
                    elif order.price_usd != price:
                        # если цена в долларах изменилась, то изменяем и цену
                        # в рублях соответственно по нынешнему курсу
                        order.price_usd = price
                        rates = ExchangeRates(str(datetime.date.today()))
                        order.price_rub = int(price) * int(rates['USD'].value)
                    elif order.delivery_date != delivery_date:
                        order.delivery_date = delivery_date
                        order.is_tracked = True
                    order.save()
                    # проверяем актуальность срока доставки, если истёк - пишем
                    # об этом в телеграм и устанавливаем заказ неотслеживаемым
                    if order.is_tracked:
                        order_delivery_date = datetime.datetime.strptime(
                            order.delivery_date, '%d.%m.%Y'
                        ).date()
                        if order_delivery_date < datetime.date.today():
                            send_message(
                                bot,
                                DELIVERY_TIME_EXPIRED.format(order.num_order)
                            )
                            order.is_tracked = False
                            order.save()
                # смотрим, есть ли удаленённые заказы в гугл таблице,
                # если да, то удаляем их из БД тоже и пишем об этом в телеграм
                order_ids = set(Order.objects.values_list('id', flat=True))
                deleted_orders = order_ids.difference(table_ids)
                for order_id in deleted_orders:
                    Order.objects.get(id=order_id).delete()
                    send_message(
                        bot,
                        ORDER_IS_DELETED.format(order_id)
                    )
                # ждем 5 минут
                time.sleep(300)
            # ловим все ошибки для безотказности программы
            # и отправляем их в телеграм и лог-файл
            except Exception as error:
                logging.exception(FAILURE_IN_PROGRAM.format(error))
                send_message(bot, FAILURE_IN_PROGRAM.format(error))
