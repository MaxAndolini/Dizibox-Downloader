import logging
import os
import sys
from typing import Union

import yt_dlp
import requests
import selenium.webdriver.remote.webelement
from selenium.common import NoSuchElementException
from seleniumwire import webdriver
from seleniumwire.utils import decode
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def check_exists_by_xpath(dr: webdriver.Chrome, xpath: str) -> Union[
    bool, selenium.webdriver.remote.webelement.WebElement]:
    try:
        el = dr.find_element(By.XPATH, xpath)
    except NoSuchElementException:
        return False
    return el


def finds_between(s: str, before: str, after: str) -> list:
    return [i.split(after)[0] for i in s.split(before)[1:] if after in i]


def find_between(s: str, first: str, last: str) -> str:
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ''


def progress_hook(d) -> None:
    if d['status'] == 'downloading':
        sys.stdout.write(
            '\rİndiriliyor: ' + d['_percent_str'].strip() + ' [ ' + d['_downloaded_bytes_str'].strip() + ' / ' + d[
                '_total_bytes_estimate_str'].strip() + ' ] ' + d['_speed_str'].strip() + ' Kalan Süre ' + d['_eta_str'])
    if d['status'] == 'finished':
        sys.stdout.write('\rBaşarıyla indirildi! ' + d['_percent_str'].strip() + ' ' + d[
            '_total_bytes_str'].strip() + (' Geçen Süre ' + d['_elapsed_str'].strip() if d[
                                                                                             '_elapsed_str'].strip() != 'Unknown' else '') + '\n')


if __name__ == '__main__':
    thread = 1

    while True:
        thread = input('Lütfen thread sayısını girin: ')

        if thread.isnumeric() and 0 <= int(thread):
            thread = int(thread)
            break

    print('Thread: ' + str(thread))

    while True:
        url = input('Lütfen Dizibox linki girin: ')

        if 'www.dizibox' not in url:
            continue

        mobile_emulation = {
            'deviceMetrics': {'width': 360, 'height': 920, 'pixelRatio': 3.0},
            'userAgent': 'Mozilla/5.0 (Linux; Android 4.2.1; en-us; Nexus 5 Build/JOP40D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Mobile Safari/535.19'}

        logging.getLogger('WDM').setLevel(logging.NOTSET)
        os.environ['WDM_LOG'] = 'false'
        options = Options()
        options.add_argument("--headless=chrome")
        options.add_experimental_option('mobileEmulation', mobile_emulation)
        options.add_extension('ublockorigin.crx')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        name = driver.title.replace('.', '. ').split(' -')[0]

        player = driver.find_element(By.XPATH, '//span[contains(@class,"selectBox-label")]').text
        source_text = player.split('Player: ')[1]

        iframe = driver.find_element(By.XPATH, '//iframe[contains(@src,"/player/")]')
        driver.switch_to.frame(iframe)

        download_url = ''
        body = []
        error = False

        source = check_exists_by_xpath(driver, '//iframe[contains(@src,"dbx.molystream.org/embed")]')
        vidmoly = check_exists_by_xpath(driver, '//iframe[contains(@src,"vidmoly")]')
        okru = check_exists_by_xpath(driver, '//iframe[contains(@src,"odnoklassniki.ru")]')

        if source is not False:
            driver.switch_to.frame(source)
            element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class,"playSheilaBtn")]')))
            driver.execute_script('arguments[0].click();', element)
            request = driver.wait_for_request('/sheila', timeout=30)
            body = decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity')).decode(
                'utf-8').splitlines()
        elif vidmoly:
            driver.switch_to.frame(vidmoly)
            element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class,"display") and @aria-label="Oynat"]')))
            driver.execute_script('arguments[0].click();', element)
            request = driver.wait_for_request('/master.m3u8', timeout=30)
            body = decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity')).decode(
                'utf-8').splitlines()
        elif okru:
            video_id = okru.get_attribute('src').split('videoembed/')[1]
            driver.get('https://m.ok.ru/video/' + video_id)
            element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "moviePlaybackRedirect")]')))
            video_url = element.get_attribute('href').replace('st.hls=off', 'st.hls=on')
            request = driver.wait_for_request('videoPreview', timeout=30)
            body = requests.get(video_url, headers=request.headers).text.splitlines()
        else:
            error = True

        driver.close()

        if error:
            print('Kaynak desteklenmiyor veya video yok!')
            continue

        print(name)
        print('Kaynak: ' + source_text)

        resolutions = []
        resolution = 0
        urls = []

        print('--- Çözünürlükler ---')
        count = 0
        link = False
        for line in body:
            if 'RESOLUTION=' in line:
                res = ''

                if source:
                    res = line.split('RESOLUTION=')[1]
                else:
                    res = find_between(line, 'RESOLUTION=', ',')

                resolutions.append(res)
                print('[' + str(count) + ']: ' + res)
                link = True
            elif link:
                count += 1
                urls.append(line)
                link = False

        while True:
            resolution = input('Lütfen çözünürlük seçin: ')

            if resolution.isnumeric() and 0 <= int(resolution) <= (count - 1):
                resolution = int(resolution)
                download_url = urls[resolution]
                break

        print('Seçilen: ' + resolutions[resolution])

        for file in os.listdir('.'):
            if '.part' in file:
                os.remove(file)

        if os.path.exists(name + '.mp4'):
            os.remove(name + '.mp4')

        if source:
            yt_dlp.utils.std_headers['Referer'] = download_url.split('/q')[0]
        elif vidmoly:
            yt_dlp.utils.std_headers['Referer'] = 'https://vidmoly.to/'
        elif okru:
            yt_dlp.utils.std_headers['Referer'] = 'https://m.ok.ru/'

        ydl_opts = {
            'nocheckcertificate': True,
            'outtmpl': name + '.mp4',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'noprogress': True,
            'fragment_retries': 100,
            'concurrent_fragment_downloads': thread,
            '_no_ytdl_file': True,
            'progress_hooks': [progress_hook],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([download_url])
