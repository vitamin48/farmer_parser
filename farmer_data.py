"""
Скрипт на основе playwright считывает ссылки на товары opt.mirfermer.ru из файла out/articles_farmer.txt,
переходит по ним, предварительно авторизуяюсь, считыват информацию каждого товара, если брэнда товара нет в файле
 in/bad_brand.txt, записывает результаты в файлы Json и XLS.

Помимо результирующего файла XLS, формируются дополнительные файлы:
out/articles_with_bad_req.txt - для ссылок, которые не удалось загрузить, либо товар из списка нежелательных
брэндов
in/catalogs.txt - список каталогов сайта
"""

from tqdm import tqdm
import datetime
import requests
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright, expect
import json
from bs4 import BeautifulSoup
import pickle
import re
import ast

from farmer_arts import bcolors, send_logs_to_telegram


def read_articles_from_txt():
    """Считывает и возвращает список ссылок на товары из файла"""
    with open('out/articles_farmer.txt', 'r', encoding='utf-8') as file:
        articles = [f'{line}'.rstrip() for line in file]
    return articles


def add_bad_req(art, error=''):
    with open('out/articles_with_bad_req.txt', 'a') as output:
        if error == '':
            output.write(f'{art} + \n')
        else:
            output.write(f'{error}\t{art}\n')


def write_json(res_dict):
    with open('out/data.json', 'w', encoding='utf-8') as json_file:
        json.dump(res_dict, json_file, indent=2, ensure_ascii=False)


class FarmerData:
    playwright = None
    browser = None
    page = None
    context = None

    def __init__(self, playwright):
        self.res_list = []
        self.res_dict = {}
        self.articles = read_articles_from_txt()
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

    def get_data_by_page(self, art):
        soup = BeautifulSoup(self.page.content(), 'lxml')
        # Удаляем каждый найденный абзац с атрибутом style="display: none"
        hidden_paragraphs = soup.find_all('p', {'style': 'display: none'})
        for paragraph in hidden_paragraphs:
            paragraph.decompose()
        "Находим код (code)"
        code = soup.find('span', class_='c-article__value js-article__value').text.strip()
        "Находим название (name)"
        name = soup.find('h1', {'style': 'padding-top: 0; margin-top: 0'}).text
        "Находим остаток (stock)"
        stock = soup.find('span', class_='element_quantity')
        if stock:
            stock = stock.text.strip()
        else:
            stock = '-'
        "Находим описание (description)"
        detailtext_div = soup.find('div', class_='tab-pane-in2')
        description = detailtext_div.get_text(strip=True)
        "Находим блок характеристики (characteristics) и записываем все значения в словарь (characteristics_dict)"
        characteristics = soup.find_all('span', class_='c-gruppedprops__prop')
        characteristics_dict = {}
        for characteristic in characteristics:
            name_ch = characteristic.find('span', class_='c-gruppedprops__prop-name').text
            value = characteristic.find('span', class_='c-gruppedprops__prop-value').text.strip()
            value = re.sub(r'[^0-9.]', '', value)
            characteristics_dict[name_ch] = value
        "Находим изображения из JavaScript кода. Из HTML bs4 не ищет."
        img_lst = []
        # Найти строку, содержащую информацию об изображениях
        script_pattern = re.compile(r'RSGoPro_Pictures\[\d+\]\s*=\s*({.+?});', re.DOTALL)
        script_matches = script_pattern.finditer(str(soup))

        for script_match in script_matches:
            # Извлечь данные из строки и преобразовать их в объект Python с помощью ast.literal_eval
            pictures_data = ast.literal_eval(script_match.group(1))

            # Пройти по всем товарам и извлечь изображения
            for product_id, product_images in pictures_data.items():
                for image_data in product_images:
                    image_url = image_data.get('SRC_ORIGINAL') or image_data.get('SRC')
                    img_lst.append(image_url)
        "Формируем результирующий словарь с данными"
        self.res_dict[code] = {'name': name, 'stock': stock, 'description': description,
                               'characteristics': characteristics_dict,
                               'img_url': img_lst, 'art_url': art}
        write_json(res_dict=self.res_dict)
        # print()

    def get_data_from_catalogs(self):
        """Перебор по ссылкам на товары, получение данных"""
        for art in tqdm(self.articles):
            retry_count = 3
            while retry_count > 0:
                try:
                    self.page.goto(art, timeout=30000)
                    self.get_data_by_page(art)
                    break
                except Exception as exp:
                    print(f'{bcolors.WARNING}Ошибка при загрузке страницы {art}: {bcolors.ENDC}\n{str(exp)}')
                    retry_count -= 1
                    if retry_count > 0:
                        print(f'Повторная попытка ({retry_count} осталось)')
                    else:
                        print(f'{bcolors.FAIL}Превышено количество попыток для товара, в файл добавлено:{bcolors.ENDC}'
                              f'\n{art}')
                        add_bad_req(art)
                        break

    def start(self):
        self.get_data_from_catalogs()


def main():
    t1 = datetime.datetime.now()
    print(f'Start: {t1}')
    try:
        with sync_playwright() as playwright:
            FarmerData(playwright=playwright).start()
        print(f'Успешно')
    except Exception as exp:
        print(exp)
        send_logs_to_telegram(message=f'Произошла ошибка!\n\n\n{exp}')
    t2 = datetime.datetime.now()
    print(f'Finish: {t2}, TIME: {t2 - t1}')
    # send_logs_to_telegram(message=f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    main()
