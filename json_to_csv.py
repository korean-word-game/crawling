# coding=utf-8
import json
import csv
import re

korean_set = list(range(ord('가'), ord('힣') + 1))
pattern_is_not_hangul = re.compile('[^가-힣]')
pattern_special = re.compile('(!-/|:-@|\[-`)')


def is_available_word(word, part):
    if len(word) < 2:
        return False
    if pattern_is_not_hangul.search(word):
        return False
    if not part == '명사':
        return False


with open('async_output.json', 'r', encoding='utf-8') as f:
    table = json.load(f)

word_dict = {}
for word, part, meaning in table:
    word = pattern_special.sub('', word)  # replace special character to none
    if is_available_word(word, part):
        if word not in word_dict:
            word_dict[word] = meaning

with open('sqlite_input.csv', 'w', newline='', encoding='utf-8') as csv_file:
    writer = csv.writer(csv_file, delimiter='^', quotechar='"')
    for word, meaning in word_dict.items():
        writer.writerow([word, meaning, 0, 1])  # 북한어
