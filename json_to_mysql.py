# coding=utf-8
import json
import os
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from aiomysql.sa import create_engine as _aio_mysql_create_engine
from dotenv import load_dotenv

from models import *

load_dotenv()

korean_set = list(range(ord('가'), ord('힣') + 1))
pattern_is_not_hangul = re.compile('[^가-힣]')
pattern_special = re.compile('([!-/]|[:-@]|[\[-`])')


def is_available_word(word, part):
    if len(word) < 2:
        return False
    if pattern_is_not_hangul.search(word):
        return False
    if not part == '명사':
        return False

    return True


def aio_create_engine():
    return _aio_mysql_create_engine(user=os.environ['mysql_user'], db=os.environ['mysql_db'],
                                    host=os.environ['mysql_host'], password=os.environ['mysql_pass'])


engine = create_engine('mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8'.format(
    user=os.environ['mysql_user'],
    db=os.environ['mysql_db'],
    host=os.environ['mysql_host'],
    password=os.environ['mysql_pass'],
    port=os.environ['mysql_port'])
)
session_maker = sessionmaker(bind=engine)

print('read json ...')
with open('async_output.json', 'r') as f:
    d = json.load(f)

print('get word already in ...')
session = session_maker()
already = set(row.text for row in session.query(MainWord.text).filter(MainWord.type_id == 2).all())

print('make dictionary ...')
word_dict = {}
for word, part, meaning in d:
    word = pattern_special.sub('', word)  # replace special character to none

    if is_available_word(word, part):
        if '의 북한어' not in meaning:  # 북한어 제외
            if word not in word_dict:
                word_dict[word] = meaning

for word in word_dict.keys():
    if word not in already:
        print(word)
        row = MainWord(text=word, info=word_dict[word], rank=0, type_id=2, first_char=word[0])
        session.add(row)

print('insert db ...')
session.commit()
