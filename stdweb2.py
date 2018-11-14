# coding=utf-8

import re

import requests
from bs4 import BeautifulSoup, element

url = 'http://stdweb2.korean.go.kr/section/north_list.jsp'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                  ' Chrome/70.0.3538.77 Safari/537.36'}


class EmptyPage(Exception):
    pass


def request(page=1, letter='ㄱ'):
    """
    The generator that returns (word, part, meaning)

    :param page: 1 ~ xx
    :param letter: korean letters from 'ㄱ' to 'ㅎ'
    :return: (word, part, meaning)
    :raise EmptyPage: word not found error
    """
    data = dict(idx='', go=page, gogroup='', Letter=letter, Table='', Gubun='', SearchText='',
                TableTemp='WORD', GubunTemp='0', SearchTextTemp='')

    pattern = re.compile(
        '<p class="exp">.*?<strong>.+?<font.+?>(.+?)</font></a>.+?<br[/]?>.+?<font.+?>(.+?)</font>.+?<br[/]?>(.+?)</p>',
        re.DOTALL)

    with requests.post(url, data, headers=headers) as response:
        soup = BeautifulSoup(response.text, 'html.parser')
        empty_flag = True
        for k in soup.find_all('p', {'class': 'exp'}):
            k: element.Tag
            rex = pattern.findall(str(k))
            if rex:
                word, part, meaning_html = rex[0]
                meaning = BeautifulSoup(meaning_html, 'html.parser').text
                yield word, part, meaning

            empty_flag = False

        if empty_flag:
            raise EmptyPage('Empty page!')


if __name__ == '__main__':
    from pyexcelerate import Workbook
    import json

    data = []
    data_json = []

    n = 1
    for letter in 'ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ':
        for i in range(1, 1000):
            try:
                for word, part, meaning in request(i, letter):
                    data.append([n, word, meaning.replace('=', "'="), letter])
                    data_json.append([n, word, meaning, letter])
                    print(word, part, meaning)
                    n += 1

            except EmptyPage:
                pass

    wb = Workbook()
    wb.new_sheet("", data=data)
    wb.save("output.xlsx")

    with open('output.json', 'w') as f:
        json.dump(data_json, f)
