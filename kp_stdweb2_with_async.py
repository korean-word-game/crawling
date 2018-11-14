# coding=utf-8

import re
import asyncio
import uuid
import os
import json

import aiohttp
import aiofiles
from bs4 import BeautifulSoup, element
from tenacity import retry

url = 'http://stdweb2.korean.go.kr/section/north_list.jsp'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                  ' Chrome/70.0.3538.77 Safari/537.36'}
pattern = re.compile(
    '<p class="exp">.*?<strong>.+?<font.+?>(.+?)</font></a>.+?<br[/]?>.+?<font.+?>(.+?)</font>.+?<br[/]?>(.+?)</p>',
    re.DOTALL)


class EmptyPage(Exception):
    pass


@retry
async def http_request(page=1, letter='ㄱ'):
    data = dict(idx='', go=page, gogroup='', Letter=letter, Table='', Gubun='', SearchText='',
                TableTemp='WORD', GubunTemp='0', SearchTextTemp='')

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers) as response:
            return await response.text()


def parse(html):
    result = []
    soup = BeautifulSoup(html, 'html.parser')
    for k in soup.find_all('p', {'class': 'exp'}):
        k: element.Tag
        rex = pattern.findall(str(k))
        if rex:
            word, part, meaning_html = rex[0]
            meaning = BeautifulSoup(meaning_html, 'html.parser').text
            result.append((word, part, meaning))
    return result


async def async_parse(html):
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, parse, html)
    if not data:
        raise EmptyPage()
    return json.dumps(data)


async def dump_json(data: str, target_dir='tmp'):
    filename = '{}.json'.format(uuid.uuid4().hex)
    file_path = os.path.join(target_dir, filename)

    async with aiofiles.open(file_path, mode='w') as f:
        await f.write(data)

    return file_path


async def request(semaphore: asyncio.Semaphore, target_dir, page, letter):
    async with semaphore:
        print('request {}\t{} ...'.format(letter, page))
        html = await http_request(page, letter)
    data = await async_parse(html)
    await dump_json(data, target_dir)


async def run(target_dir):
    if not os.path.isdir(target_dir):
        os.mkdir(target_dir)

    semaphore = asyncio.Semaphore(100)

    letters = list('ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ')
    pages = {k: v for k, v in zip(letters, (881, 260, 495, 696, 333, 594, 530, 728, 620, 218, 66, 113, 147, 398))}

    jobs = []
    for letter in letters:
        for i in range(1, pages[letter] + 1):
            jobs.append(request(semaphore, target_dir, i, letter))

    await asyncio.gather(*jobs)


def merge_json(target_dir, output):
    data = []

    for filename in os.listdir(target_dir):
        file_path = os.path.join(target_dir, filename)
        with open(file_path, 'r') as f:
            data.extend(json.load(f))

    print(len(data))
    with open(output, 'w') as f:
        json.dump(data, f)


if __name__ == '__main__':
    target_dir = 'tmp'
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(target_dir))
    merge_json(target_dir, 'kp_async_output.json')
