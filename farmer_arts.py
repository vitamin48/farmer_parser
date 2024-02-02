"""Скрипт на основе playwright считывает каталоги opt.mirfermer.ru из файла catalogs.txt и собирает ссылки со всех
имеющихся страниц в файл mirfermer_articles.txt с учетом цены или без. Цена доступна только авторизованным пользователям.
Остатки велики, этим параметром можно пренебречь"""

from tqdm import tqdm
import datetime
import requests
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright, expect
import json
from bs4 import BeautifulSoup


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
        self.res_list = []
        self.res_dict = {'name': None, 'url': None}
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
        except TypeError:
            print(f'{bcolors.WARNING}В каталоге 1 страница товаров? Лучше перепроверить!{bcolors.ENDC}')
            return 1
        except Exception as exp:
            print(f'{bcolors.FAIL}Ошибка при попытке получить последнюю страницу в каталоге: {catalog}{bcolors.ENDC}\n'
                  f'\n{exp}')

    def get_data_by_page(self):
        soup = BeautifulSoup(self.page.content(), 'lxml')
        # Найти все блоки элементов внутри класса 'list-showcase__element'
        elements = soup.find('div', class_='list-showcase view-showcase row')
        for element in elements.find_all('div', class_='js-element'):
            # Извлечь имя товара
            name = element.find('div', class_='list-showcase__name').text.strip()
            # Извлечь ссылку на товар
            link = element.find('div', class_='list-showcase__name').find('a')['href']
            link = f'https://opt.mirfermer.ru{link}'
            data = {'name': name, 'url': link}
            self.res_list.append(data)
            with open('out/articles_farmer.txt', 'a') as output:
                output.write(f'{link}\n')
            # self.res_dict['name'] = name
            # self.res_dict['url'] = link
            # self.res_list.append(self.res_dict)
            with open('out/data.json', 'w', encoding='utf-8') as json_file:
                json.dump(self.res_list, json_file, indent=2, ensure_ascii=False)
            # self.res_dict = {'name': name, 'url': link}

    def get_arts_by_catalogs(self):
        for catalog in self.catalogs:
            print(f'Работаю с каталогом: {catalog}')
            max_page_number = self.get_number_last_page(catalog)
            for page_number in tqdm(range(1, max_page_number + 1)):
                url = f'{catalog}/?PAGEN_4={page_number}'
                retry_count = 3
                while retry_count > 0:
                    try:
                        self.page.goto(url, timeout=30000)
                        self.get_data_by_page()
                        break
                    except Exception as exp:
                        print(f'Ошибка при загрузке страницы {url}: \n{str(exp)}')
                        retry_count -= 1
                        if retry_count > 0:
                            print(f'Повторная попытка ({retry_count} осталось)')
                        else:
                            print('Превышено количество попыток.')
                            break

    def start(self):
        self.get_arts_by_catalogs()


def main():
    t1 = datetime.datetime.now()
    print(f'Start: {t1}')
    try:
        with sync_playwright() as playwright:
            Farmer(playwright=playwright).start()
        print(f'Успешно')
    except Exception as exp:
        print(exp)
        send_logs_to_telegram(message=f'Произошла ошибка!\n\n\n{exp}')
    t2 = datetime.datetime.now()
    print(f'Finish: {t2}, TIME: {t2 - t1}')
    # send_logs_to_telegram(message=f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    main()