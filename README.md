# GOOGLE SHEETS TEST PROJECT

# Как запустить проект:
- Установите Docker, инструкция:
https://docs.docker.com/get-docker/

- Установите docker-compose, инструкция:
https://docs.docker.com/compose/install/

- Клонируйте репозиторий:
```
git clone git@github.com:ilyarogozin/googlesheets.git
```

- Создайте файл окружения .env, который будет содержать:
```
SECRET_KEY='y7=+7*66)z9^tl&uj7)844+(*nqm%e+6a_61xo*h%_0+-@!hhv'
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
ALLOWED_HOSTS='127.0.0.1 localhost'
CHAT_ID='<id вашего чата в телеграме>>'
SPREADSHEET_ID='1uA_FvQ_metf0MDKgyMRhNok0_Y-nktspVhbkM1b9AMM'
TELEGRAM_TOKEN='5322391216:AAGzwADg6X99--X-RQ9AA8XPRjUMy-mpsWQ'
```

- Соберите контейнеры и запустите их:
```
docker-compose up -d --build
```

- Выполните миграции:
```
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

- Запустите скрипт:
```
docker-compose exec web python manage.py run
```
