import logging
import os

import youtube_dl
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def my_hook(d):
    if d['status'] == 'finished':
        print('Başarıyla indirildi!')


if __name__ == '__main__':
    while True:
        url = input('Lütfen Dizibox linki girin: ')

        if 'www.dizibox' in url is False:
            continue

        logging.getLogger('WDM').setLevel(logging.NOTSET)
        os.environ['WDM_LOG'] = 'false'
        options = Options()
        options.headless = True
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        name = driver.title.replace('.', '. ').split(' -')[0]
        iframe = driver.find_element(By.XPATH, '//iframe[contains(@src,"king")]')
        driver.switch_to.frame(iframe)
        link = driver.find_element(By.XPATH, '//iframe[contains(@src,"dbx.molystream.org/embed")]').get_attribute('src')
        driver.close()

        print(name)
        print('İndiriliyor...')

        youtube_dl.utils.std_headers['Referer'] = 'https://dbx.molystream.org'

        ydl_opts = {
            'nocheckcertificate': True,
            'outtmpl': name + '.mp4',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [my_hook]
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link + '/sheila'])
