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

url = 'http://stdweb2.korean.go.kr/search/List_dic.jsp'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                  ' Chrome/70.0.3538.77 Safari/537.36'}
pattern_word = re.compile(
    '<p class="exp">.*?<font.*?>(?P<word>.+?)</font>.*?<br.*?>.*?'
    '(<font.*?>(?P<part>.*?)</font>.*?)?<br.*?>(?P<meaning>.+?)</p>',
    re.DOTALL)
pattern_num = re.compile(r'<span class="tb12">.*?[(](\d+?)건[)]</span>', re.DOTALL)


class EmptyPage(Exception):
    pass


@retry
async def http_request(page=1, letter='ㄱ', num_per_page=10):
    _page_div, _page_mod = divmod(page, 10)
    if _page_mod == 1:
        gogroup = _page_div + 1
        page = ''
    else:
        gogroup = ''

    data = dict(go=page, gogroup=gogroup, PageRow=num_per_page, SearchPart='Jaso', Table='words|word', Gubun=0,
                Jaso1=letter, JasoSearch='[{}/?/?]'.format(letter), focus_name='SearchText')

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers, timeout=300) as response:
            if not response.status == 200:
                raise Exception('bad status code: {}'.format(response.status))
            return await response.text()


def _get_word_num(html):
    rex = pattern_num.search(html)
    if rex:
        return int(rex.group(1))


def parse(html):
    result = []
    rex = pattern_word.findall(html)
    for k in rex:
        word = BeautifulSoup(k[0], 'html.parser').text
        part = k[2]
        meaning = BeautifulSoup(k[3], 'html.parser').text
        result.append((word, part, meaning))

    return result


async def async_parse(html):
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, parse, html)
    if not data:
        raise EmptyPage()
    return json.dumps(data)


async def async_dump_json(data: str, target_dir='tmp'):
    if not os.path.isdir(target_dir):
        os.mkdir(target_dir)
    filename = '{}.json'.format(uuid.uuid4().hex)
    file_path = os.path.join(target_dir, filename)

    async with aiofiles.open(file_path, mode='w') as f:
        await f.write(data)

    return file_path


async def request(semaphore: asyncio.Semaphore, target_dir, letter, num_per_page=1000):
    loop = asyncio.get_event_loop()
    async with semaphore:
        print('request {}\t({}/?) ...'.format(letter, 1))
        html = await http_request(1, letter, num_per_page)

    word_num = await loop.run_in_executor(None, _get_word_num, html)
    if word_num:
        print('{} 개수 {} 개'.format(letter, word_num))
        page_cnt, page_mod = divmod(word_num, num_per_page)
        if page_mod:
            page_cnt += 1

        data = await async_parse(html)
        await async_dump_json(data, target_dir)

        for page in range(2, page_cnt + 1):
            async with semaphore:
                print('request {}\t({}/{}) ...'.format(letter, page, page_cnt))
                html = await http_request(page, letter, num_per_page)

            try:
                data = await async_parse(html)
                await async_dump_json(data, target_dir)
            except EmptyPage:
                print('단어 없음: {}'.format(letter))


async def run(target_dir):
    semaphore = asyncio.Semaphore(25)

    jobs = []
    for letter in 'ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㅃㅉㄸㄲㅆ':
        jobs.append(request(semaphore, target_dir, letter, 1000))

    await asyncio.gather(*jobs)


def merge_json(target_dir):
    if os.path.isdir(target_dir):
        data = []

        for filename in os.listdir(target_dir):
            file_path = os.path.join(target_dir, filename)
            with open(file_path, 'r') as f:
                data.extend(json.load(f))

        with open('async_output.json', 'w') as f:
            json.dump(data, f)


if __name__ == '__main__':
    target_dir = 'tmp'

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(target_dir))
    merge_json(target_dir)
