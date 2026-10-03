import requests
import os
from urllib.parse import urlparse
import configparser
import time
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.console import Console
from rich.panel import Panel
from rich.align import Align

# Создаём объект ConfigParser
config = configparser.ConfigParser()
console = Console()



# Просим пользователя ввести данные и создаём файл с этими данными
if not (os.path.exists("settings.ini")):
    centered_text_settings = Align.center("[bold magenta]Настройка подключения к Redmine[/bold magenta]")
    console.print(Panel(centered_text_settings))
    redmine_url = input(
        "Введите адрес вашего Redmine.\nПример: https://redmine.my_domain.com\nВаш адрес: ").strip()
    api_key = input(
        "Введите ваш ключ API (его можно получить по адресу https://redmine.my_domain.com/my/account)\nВаш ключ API: ").strip()

    # Парсим адрес redmine пользователя. Получаем из него протокол и домен
    parsed_url = urlparse(redmine_url)
    server_protocol = parsed_url.scheme
    server_domain = parsed_url.netloc

    # Добавляем секции и данные

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


# ================================== Объявление сессии ==================================
with requests.Session() as session:
    centered_text = Align.center("[bold magenta]Связывание задач[/bold magenta]")
    console.print(Panel(centered_text))
    # console.print(Panel("[bold magenta]Связывание задач[/bold magenta]", expand=False))
    # Добавления ключа API в заголовок сессии
    session.headers.update({
        "Content-Type": "application/json",
        "X-Redmine-API-Key": API_KEY
    })

    # Получение номеров задач: из какой скопировать в какую
    idFrom = int(
        input("Введите ID задачи, из которой хотите скопировать все связанные задачи: ").strip())
    idTo = int(input(
        "Введите ID задачи, в которую хотите скопировать все связанные задачи: ").strip())


    # Получение всех связанных задач из --idFrom--
    responseGet = session.get(
        f"{URL}/issues/{idFrom}/relations.json")
    # print(f"Статус код: {responseGet.status_code}")
    # print(f"Полученный ответ GET запроса: {responseGet.json()}")

    # Перевод полученного json в массив
    issues = responseGet.json()["relations"]
    issuesId = []

    # Добавление всех значений ключа --issue_to_id-- в массив --issuesId[]--
    # Собираем ID всех связанных задач, исключая саму задачу idFrom
    for rel in issues:
        if rel["issue_to_id"] != idFrom:
            # Если в 'куда' не мы, значит связанная задача — это 'куда'
            issuesId.append(rel["issue_to_id"])
        else:
            # Если в 'куда' мы, значит связанная задача — это 'откуда'
            issuesId.append(rel["issue_id"])

    # Делайм запрос к каждой связанной задаче и получаем её статус
    checkStatusList = []
    open_amount = 0
    closed_amount = 0
    total_tasks = len(issuesId)
    
    with Progress(
        TextColumn("[progress.description]{task.description}"), # Колонка для нашего меняющегося текста
        BarColumn(),               # Сама полоска
        TaskProgressColumn(),      # Процент (%)
        TimeRemainingColumn(),     # Время до конца
    ) as progress:

        # Создаем задачу. Пока оставляем описание пустым, так как будем менять его в цикле.
        task_id = progress.add_task("", total=total_tasks)

        # Используем enumerate, чтобы получить индекс текущего элемента (начиная с 1)
        for i, checkId in enumerate(issuesId, 1):
            
            # ОБНОВЛЕНИЕ ТЕКСТА:
            # Здесь мы динамически меняем описание задачи в реальном времени
            progress.update(
                task_id, 
                description=f"[cyan]Обработка задачи {i} из {total_tasks} (ID: {checkId}): "
            )

            # --- Твой основной код без изменений ---
            checkStatusGet = session.get(f"{URL}/issues/{checkId}.json")
            data = checkStatusGet.json().get("issue", {})
            issue_name = data.get("subject", "Без названия")
            status_name = data.get("status", {}).get("name", "Неизвестно")
            
            checkStatusList.append({"id": checkId, "status": status_name, "name": issue_name})
            
            if status_name != "Закрыт":
                open_amount += 1
            else:
                closed_amount += 1
            
            time.sleep(0.2)
            # ---------------------------------------

            # Двигаем саму полоску вперед на 1 шаг
            progress.update(task_id, advance=1)

    print(f"Всего задач / открытых задач / закрытых задач:\n{len(checkStatusList)} / {open_amount} / {closed_amount}")
    
    chooseStatus = int(input(
        "Выберите, задачи с каким статусом вы хотите привязать:\n1 - Все задачи\n2 - Только открытые\n3 - Только закрытые\nВведите чилсло: ").strip())

    # Фильтрация статуса задачи
    if chooseStatus == 1: # Связать ВСЕ задачи
        # Для каждого элемента --issuesId[]-- выполняется отправка запроса POST
        console.print("─" * 120, style="grey37")
        for target_id in checkStatusList:
            payload = {
                "relation": {
                    "issue_to_id": target_id.get("id"),
                    "relation_type": "relates"
                }
            }
            responsePost = session.post(
                f"{URL}/issues/{idTo}/relations.json", json=payload)

            task_url = f"{URL}/issues/{target_id.get("id")}"
            console.print(f"Номер задачи: [blue underline][link={task_url}]{target_id.get("id")}[/]")
            print(f"Имя задачи: {target_id.get("name")}")
            console.print(f"Статус задачи: {target_id.get("status")}")
            console.print(f"[{'green bold' if responsePost.status_code == 201 else 'red bold'}]Статус код: {responsePost.status_code}: {responsePost.reason}[/]")
            # print(f"Полученный ответ POST запроса: {responsePost.text}")
            console.print("─" * 120, style="grey37")
            time.sleep(0.2)

        print("\n")
        print("Связывание всех задач закончено!")
        input("Нажмите Enter для закрытия:")
    elif chooseStatus == 2: # Связать задачи со статусом "Новый"
        console.print("─" * 120, style="grey37")
        for issueStatus in checkStatusList:
            if issueStatus["status"] != "Закрыт":
                payload = {
                    "relation": {
                        "issue_to_id": issueStatus["id"],
                        "relation_type": "relates"
                    }
                }
                responsePost = session.post(
                    f"{URL}/issues/{idTo}/relations.json", json=payload)
                
                task_url = f"{URL}/issues/{issueStatus.get("id")}"
                console.print(f"Номер задачи: [blue underline][link={task_url}]{issueStatus["id"]}[/]")
                print(f"Имя задачи: {issueStatus.get("name")}")
                print(f"Статус задачи: {issueStatus["status"]}")
                console.print(f"[{'green bold' if responsePost.status_code == 201 else 'red bold'}]Статус код: {responsePost.status_code}: {responsePost.reason}[/]")
                # print(f"Полученный ответ POST запроса: {responsePost.text}")
                console.print("─" * 120, style="grey37")
                time.sleep(0.2)
                
        print("\n")
        print(
            f'Связывание открытых закончено!')
        input("Нажмите Enter для закрытия:")
    elif chooseStatus == 3: # Связать задачи со статусом "Закрыто"
        console.print("─" * 120, style="grey37")
        for issueStatus in checkStatusList:
            if issueStatus["status"] == "Закрыт":
                payload = {
                    "relation": {
                        "issue_to_id": issueStatus["id"],
                        "relation_type": "relates"
                    }
                }
                responsePost = session.post(
                    f"{URL}/issues/{idTo}/relations.json", json=payload)
                
                task_url = f"{URL}/issues/{issueStatus.get("id")}"
                console.print(f"Номер задачи: [blue underline][link={task_url}]{issueStatus["id"]}[/]")
                console.print(f"Имя задачи: {issueStatus.get("name")}")
                print(f"Статус задачи: {issueStatus["status"]}")
                console.print(f"[{'green bold' if responsePost.status_code == 201 else 'red bold'}]Статус код: {responsePost.status_code}: {responsePost.reason}[/]")
                # print(f"Полученный ответ POST запроса: {responsePost.text}")
                console.print("─" * 120, style="grey37")
                time.sleep(0.2)
                
        print("\n")
        print(
            f'Связывание закрытых задач закончено!')
        input("Нажмите Enter для закрытия:")


# ================================== Конец сессии ==================================

# ======================== Сообщение о конце работы скрипта ========================
