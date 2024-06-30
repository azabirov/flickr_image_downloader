import os
import asyncio
import aiohttp
import argparse
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Настройка аргументов командной строки
parser = argparse.ArgumentParser(description='Скачивание фотографий с Flickr')
parser.add_argument('--url', type=str, help='URL страницы пользователя Flickr')
parser.add_argument('--start_page', type=int, default=1, help='Номер страницы, с которой начать скачивание')
args = parser.parse_args()

# Проверка на наличие URL
if not args.url:
    args.url = input("Введите URL страницы пользователя Flickr: ")

url = args.url
start_page = args.start_page
os.makedirs("flickr_images", exist_ok=True)

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument('--no-proxy-server')
chrome_options.add_argument('--proxy-server="direct://"')
chrome_options.add_argument('--proxy-bypass-list=*')

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wait_for_page_load(driver, url, timeout=30):
    driver.get(url)
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

def scroll_to_bottom(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        import time
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def get_total_pages(driver):
    try:
        time.sleep(5)  # Добавляем задержку
        wait_for_page_load(driver, url)
        scroll_to_bottom(driver)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.view.pagination-view"))
        )
        pagination = driver.find_element(By.CSS_SELECTOR, "div.view.pagination-view")
        pages = pagination.find_elements(By.CSS_SELECTOR, "a[data-track]")
        return max(int(page.text) for page in pages if page.text.isdigit())
    except Exception as e:
        print(f"Ошибка при определении общего количества страниц: {e}")
        return 1

def get_image_page_links(driver, page_url):
    driver.get(page_url)
    scroll_to_bottom(driver)
    photo_links = driver.find_elements(By.CSS_SELECTOR, "a.overlay")
    return [a.get_attribute('href') for a in photo_links]

def get_image_download_link(driver, photo_page_url):
    driver.get(photo_page_url)
    img = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "img.main-photo"))
    )
    return img.get_attribute('src')

async def download_image(session, image_url):
    try:
        async with session.get(image_url) as response:
            if response.status == 200:
                image_name = os.path.join("flickr_images", image_url.split('/')[-1])
                with open(image_name, 'wb') as f:
                    f.write(await response.read())
                print(f"Успешно скачано: {image_name}")
    except Exception as e:
        print(f"Ошибка при скачивании {image_url}: {e}")

async def process_page(driver, page_url, session):
    photo_page_links = get_image_page_links(driver, page_url)
    tasks = []
    for photo_page_link in photo_page_links:
        image_download_link = get_image_download_link(driver, photo_page_link)
        if image_download_link:
            task = asyncio.create_task(download_image(session, image_download_link))
            tasks.append(task)
    await asyncio.gather(*tasks)

async def main():
    driver = webdriver.Chrome(options=chrome_options)
    try:
        total_pages = get_total_pages(driver)
        print(f"Всего страниц: {total_pages}")

        async with aiohttp.ClientSession() as session:
            for page_num in range(start_page, total_pages + 1):
                page_url = url + f'page{page_num}/'
                print(f"Обработка страницы: {page_url}")
                await process_page(driver, page_url, session)

        print("Скачивание завершено.")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    asyncio.run(main())
