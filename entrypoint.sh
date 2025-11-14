#!/usr/bin/env bash
set -e

# Выполняем миграции
python manage.py migrate

# Создаём суперпользователя и загружаем мок-данные из CSV
python manage.py start

# Запускаем сервер
exec python manage.py runserver 0.0.0.0:8000