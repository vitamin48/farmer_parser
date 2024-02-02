"""Сохранение супа в файл pickle"""

from playwright.sync_api import Playwright, sync_playwright
from bs4 import BeautifulSoup
import pickle
import re
import json
import ast

URL = 'https://opt.mirfermer.ru/catalog/posadochnyy_material_1/luk_sevok_chesnok/luk_sevok_rossiya_/luk_sevok_rozanna_rozovyy_10_21_10kg_/'


def get_page_content():
    with sync_playwright() as playwright:
        js = """
        Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
        """
        playwright = playwright
        browser = playwright.chromium.launch(headless=False, args=['--blink-settings=imagesEnabled=false'])
        context = browser.new_context()
        page = context.new_page()
        page.add_init_script(js)
        page.goto(URL)
        content_data = page.content()
        context.close()
        browser.close()
    return content_data


def save_content():
    content = get_page_content()
    with open('content.pickle', 'wb') as file:
        pickle.dump(content, file)


def load_content():
    with open('content.pickle', 'rb') as file:
        content = pickle.load(file)
    soup = BeautifulSoup(content, 'lxml')
    parse_content(soup)


def parse_content(soup):
    res_dict = {}
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
    res_dict[code] = {'name': name, 'stock': stock, 'description': description, 'characteristics': characteristics_dict,
                      'img_url': img_lst}

    print()


if __name__ == '__main__':
    """Если нужно загрузить и сохранить контент страницы, выбираем save_content(), для загрузки - load_content()"""
    # save_content()
    load_content()
