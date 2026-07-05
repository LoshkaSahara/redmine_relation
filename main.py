import requests
import os
from urllib.parse import urlparse
import configparser


# Просим пользователя ввести данные и создаём файл с этими данными
if not (os.path.exists("settings.ini")):
    redmine_url = input(
        "Введите адрес вашего Redmine.\nПример: https://redmine.my_domain.com\nВаш адрес: ")
    api_key = input(
        "Введите ваш ключ API (его можно получить по адресу https://redmine.my_domain.com/my/account)\nВаш ключ API: ")

    # Парсим адрес redmine пользователя. Получаем из него протокол и домен
    parsed_url = urlparse(redmine_url)
    server_protocol = parsed_url.scheme
    server_domain = parsed_url.netloc

    # 1. Создаём объект ConfigParser
    config = configparser.ConfigParser()

    # 2. Добавляем секции и данные

    config['SETTINGS'] = {
        # 'server_protocol': server_protocol,
        # 'server_domain': server_domain,
        "URL": f"{server_protocol}://{server_domain}",
        'API_KEY': api_key
    }

    with open("settings.ini", "w", encoding='utf-8') as f:
        config.write(f)


# Подключаем файл с данными пользователя

config.read("settings.ini", encoding='utf-8')
API_KEY = config["SETTINGS"]["api_key"]
URL = config["SETTINGS"]["url"]


# Добавления ключа API в заголовок
headers = {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": API_KEY
}

# Получение номеров задач: из какой скопировать в какую
idFrom = int(
    input("Введите ID задачи, из которой хотите скопировать все связанные задачи: "))
idTo = int(input(
    "Введите ID задачи в которую Вы хотите скопировать все связанные задачи: "))


# Получение всех связанных задач из --idFrom--
responseGet = requests.get(
    f"{URL}/issues/{idFrom}/relations.json", headers=headers)
print(f"Статус код: {responseGet.status_code}")
print(f"Полученный ответ GET запроса: {responseGet.json()}")

# Перевод полученного json в массив
issues = responseGet.json()["relations"]
issuesId = []

# Добавление всех значений ключа --issue_to_id-- в массив --issuesId[]--
for i in range(len(issues)):
    issuesId.append(issues[i]["issue_to_id"])
    # print(issuesId[i])

# Для каждого элемента --issuesId[]-- выполняется отправка запроса POST
for target_id in issuesId:
    payload = {
        "relation": {
            "issue_to_id": target_id,
            "relation_type": "relates"
        }
    }
    responsePost = requests.post(f"{URL}/issues/{idTo}/relations.json", headers=headers,
                                 json=payload)
    print(f"Статус код: {responsePost.status_code}")
    print(f"Полученный ответ POST запроса: {responsePost.text}")
