"""Скрипт на основе playwright считывает каталоги opt.mirfermer.ru из файла catalogs.txt и собирает ссылки со всех
имеющихся страниц в файл mirfermer_articles.txt с учетом цены или без. Цена доступна только авторизованным пользователям.
Остатки велики, этим параметром можно пренебречь"""

import time
import datetime
import requests
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright, expect


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def read_catalogs_from_txt():
    """Считывает и возвращает список каталогов из файла"""
    with open('in/catalogs.txt', 'r', encoding='utf-8') as file:
        catalogs = [f'{line}'.rstrip() for line in file]
    return catalogs


def send_logs_to_telegram(message):
    import platform
    import socket
    import os

    platform = platform.system()
    hostname = socket.gethostname()
    user = os.getlogin()

    bot_token = '6456958617:AAF8thQveHkyLLtWtD02Rq1UqYuhfT4LoTc'
    chat_id = '128592002'

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    data = {"chat_id": chat_id, "text": message + f'\n\n{platform}\n{hostname}\n{user}'}
    response = requests.post(url, data=data)
    return response.json()


class Farmer:
    playwright = None
    browser = None
    page = None
    context = None

    def __init__(self, playwright):
        self.catalogs = read_catalogs_from_txt()
        self.playwright_config(playwright=playwright)

    def playwright_config(self, playwright):
        js = """
        Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
        """
        self.playwright = playwright
        self.browser = playwright.chromium.launch(headless=False, args=['--blink-settings=imagesEnabled=false'])
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.add_init_script(js)

    def get_number_last_page(self, catalog):
        """Получаем последнюю страницу в каталоге"""
        try:
            self.page.goto(catalog, timeout=30000)
            # Находим текущий номер страницы
            current_page_element = self.page.query_selector('.navigation .current')
            current_page = int(current_page_element.inner_text()) if current_page_element else 1
            # Находим все элементы с номерами страниц
            page_numbers = self.page.query_selector_all('.navigation a')
            # Извлекаем номера страниц и находим максимальный
            max_page_number = max(current_page,
                                  *[int(page_number.inner_text()) for page_number in page_numbers if
                                    page_number.inner_text() and page_number.inner_text().isdigit()])
            return max_page_number
        except Exception as exp:
            print(f'{bcolors.FAIL}Ошибка при попытке получить последнюю страницу в каталоге: {catalog}{bcolors.ENDC}\n'
                  f'\n{exp}')

    def get_data_by_page(self):
        pass

    def get_arts_by_catalogs(self):
        max_attempts = 5
        for catalog in self.catalogs:
            print(f'Работаю с каталогом: {catalog}')
            current_page = 1
            for attempt in range(1, max_attempts + 1):
                try:
                    max_page_number = self.get_number_last_page(catalog)
                    if current_page == 1:
                        print('работа с 1 страницей')
                        self.get_data_by_page()
                        current_page += 1
                        continue
                    else:
                        if current_page != max_page_number:
                            self.page.goto(f'{catalog}/?PAGEN_4={current_page}', timeout=30000)
                            self.get_data_by_page()
                            current_page += 1
                        else:
                            print(f'Закончили работу с каталогом {catalog}, последняя страница: {current_page}')
                            break
                except Exception as exp:
                    print(f'{bcolors.WARNING}Попытка {attempt} из {max_attempts} не удалась. '
                          f'Страница: {current_page}. Ошибка: {bcolors.ENDC}\n\n{exp}')

    def start(self):
        self.get_arts_by_catalogs()
        print()


def main():
    t1 = datetime.datetime.now()
    print(f'Start: {t1}')
    try:
        with sync_playwright() as playwright:
            Farmer(playwright=playwright).start()
        print()
    except Exception as exp:
        print(exp)
        send_logs_to_telegram(message=f'Произошла ошибка!\n\n\n{exp}')
    t2 = datetime.datetime.now()
    print(f'Finish: {t2}, TIME: {t2 - t1}')
    # send_logs_to_telegram(message=f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    main()
