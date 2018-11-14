# coding=utf-8

import re
import asyncio
import uuid
import os
import json

import aiohttp
import aiofiles
from bs4 import BeautifulSoup, element
from async_retrying import retry

url = 'http://stdweb2.korean.go.kr/search/List_dic.jsp'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                  ' Chrome/70.0.3538.77 Safari/537.36'}
pattern_word = re.compile(
    '<p class="exp">.*?<strong><font.*?>(.+?)</font></strong>.*?<br [/]?>.*?<font.*?>(.*?)</font>.*?<br />(.+?)</p>',
    re.DOTALL)
pattern_num = re.compile(r'<span class="tb12">.*?[(](\d+?)건[)]</span>', re.DOTALL)


class EmptyPage(Exception):
    pass


@retry
async def http_request(page=1, letter='가', num_per_page=1000):
    data = dict(gogroup=page, PageRow=num_per_page, JasoCnt=0, SearchPart='Simple', ResultRows=0, arrSearchLen=0,
                Table='words|word', Gubun=1, SearchText=letter, SpCode=1)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers) as response:
            return await response.text()


def _get_word_num(html):
    rex = pattern_num.search(html)
    if rex:
        return int(rex.group(1))


@retry
async def set_word_num(semaphore: asyncio.Semaphore, d: dict, letter):
    loop = asyncio.get_event_loop()
    async with semaphore:
        html = await http_request(letter=letter, num_per_page=1)
    num = await loop.run_in_executor(None, _get_word_num, html)
    if num:
        d[letter] = num


def parse(html):
    result = []
    for word, part, meaning_html in pattern_word.findall(html):
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
    try:
        data = await async_parse(html)
        await dump_json(data, target_dir)
    except EmptyPage:
        pass


async def run():
    target_dir = 'tmp'
    if not os.path.isdir(target_dir):
        os.mkdir(target_dir)

    semaphore = asyncio.Semaphore(100)

    letters = [chr(i) for i in range(ord('가'), ord('힣') + 1)]

    # # get word nums
    # print('get word nums ...')
    # jobs = []
    # word_nums = {}
    # for letter in letters:
    #     jobs.append(set_word_num(semaphore, word_nums, letter))
    # await asyncio.gather(*jobs)
    # page_nums = {}
    # for k, v in word_nums.items():
    #     cnt, mod = divmod(v, 1000)
    #     if mod:
    #         cnt += 1
    #     page_nums[k] = cnt
    # print(page_nums)

    page_nums = {'뺍': 1, '잔': 1, '잗': 1, '뺑': 1, '잙': 1, '잘': 1, '잡': 1, '키': 1, '잠': 1, '킥': 1, '킨': 1, '잣': 1, '잩': 1,
                 '떤': 1, '잦': 1, '킬': 1, '장': 3, '킴': 1, '잫': 1, '떠': 1, '떡': 1, '재': 2, '잭': 1, '뺨': 1, '킵': 1, '킷': 1,
                 '잰': 1, '떨': 1, '잴': 1, '킹': 1, '떫': 1, '탈': 1, '떰': 1, '잼': 1, '견': 1, '잽': 1, '잿': 1, '겿': 1, '겪': 1,
                 '겯': 1, '결': 1, '쟁': 1, '쟈': 1, '쟉': 1, '경': 2, '뻔': 1, '쟝': 1, '뻐': 1, '계': 2, '쟘': 1, '뻗': 1, '뻘': 1,
                 '뗀': 1, '떵': 1, '곗': 1, '뗏': 1, '뗑': 1, '곁': 1, '곬': 1, '곡': 1, '고': 4, '곤': 1, '곧': 1, '골': 1, '곷': 1,
                 '곪': 1, '곰': 1, '곱': 1, '겸': 1, '곻': 1, '쟐': 1, '겻': 1, '겹': 1, '곳': 1, '곶': 1, '공': 3, '뻑': 1, '쟨': 1,
                 '곽': 1, '뻰': 1, '뻣': 1, '과': 1, '뻬': 1, '뻥': 1, '뻭': 1, '뻽': 1, '턴': 1, '떽': 1, '떼': 1, '터': 1, '턱': 1,
                 '턍': 1, '털': 1, '저': 1, '똔': 1, '텀': 1, '적': 1, '전': 4, '젉': 1, '젇': 1, '젊': 1, '뼁': 1, '텅': 1, '뼉': 1,
                 '똘': 1, '텃': 1, '또': 1, '절': 1, '관': 2, '괌': 1, '텍': 1, '텁': 1, '뼈': 1, '뼐': 1, '점': 1, '젖': 1, '괄': 1,
                 '젝': 1, '정': 3, '텝': 1, '텐': 1, '뼘': 1, '제': 2, '젙': 1, '텔': 1, '뼝': 1, '텟': 1, '젤': 1, '뼛': 1, '텡': 1,
                 '템': 1, '텩': 1, '젬': 1, '테': 1, '젹': 1, '괸': 1, '톈': 1, '괫': 1, '굄': 1, '뙈': 1, '젼': 1, '굉': 1, '뽄': 1,
                 '졀': 1, '뽁': 1, '졍': 1, '뽈': 1, '뽑': 1, '뽕': 1, '졔': 1, '굮': 1, '토': 1, '졉': 1, '뙷': 1, '뙤': 1, '톨': 1,
                 '텬': 1, '톰': 1, '통': 1, '군': 1, '톺': 1, '구': 3, '굴': 1, '국': 1, '굳': 1, '족': 1, '좁': 1, '궉': 1, '좌': 1,
                 '종': 2, '졸': 1, '궂': 1, '권': 1, '젱': 1, '좡': 1, '궈': 1, '뾩': 1, '좨': 1, '뚜': 1, '뚬': 1, '뚤': 1, '궐': 1,
                 '텨': 1, '궤': 1, '뾰': 1, '뚫': 1, '뚱': 1, '퇴': 1, '젯': 1, '젓': 1, '죄': 1, '텋': 1, '궹': 1, '귀': 1, '툇': 1,
                 '뿌': 1, '뿍': 1, '툐': 1, '접': 1, '죠': 1, '죡': 1, '뿡': 1, '뛔': 1, '툭': 1, '똬': 1, '죵': 1, '투': 1, '뛰': 1,
                 '준': 1, '툼': 1, '주': 3, '줌': 1, '귤': 1, '뜀': 1, '글': 1, '긑': 1, '중': 2, '줍': 1, '긁': 1, '균': 1, '긄': 1,
                 '죽': 1, '퉤': 1, '똥': 1, '튀': 1, '튐': 1, '튕': 1, '뜾': 1, '뜬': 1, '긼': 1, '뜰': 1, '쥉': 1, '깅': 1, '뜸': 1,
                 '쀼': 1, '기': 4, '뜻': 1, '긷': 1, '뜽': 1, '쁘': 1, '띔': 1, '길': 1, '긶': 1, '긿': 1, '김': 1, '쥠': 1, '깊': 1,
                 '깍': 1, '쥣': 1, '트': 1, '뜯': 1, '쥥': 1, '쥰': 1, '띨': 1, '쥭': 1, '즁': 1, '즉': 1, '틀': 1, '깝': 1, '툰': 1,
                 '락': 1, '틔': 1, '존': 1, '조': 3, '굶': 1, '틧': 1, '괘': 1, '젠': 1, '즈': 1, '란': 1, '즑': 1, '랄': 1, '즌': 1,
                 '즐': 1, '랍': 1, '즘': 1, '삔': 1, '삑': 1, '랑': 1, '즛': 1, '삠': 1, '즙': 1, '광': 1, '래': 1, '랠': 1, '똑': 1,
                 '괏': 1, '띠': 1, '깎': 1, '깡': 1, '깔': 1, '깜': 1, '깟': 1, '긍': 1, '삥': 1, '팁': 1, '틱': 1, '램': 1, '팃': 1,
                 '삭': 1, '꺅': 1, '사': 5, '삸': 1, '티': 1, '팅': 1, '삳': 1, '팀': 1, '팎': 1, '파': 1, '샆': 1, '틴': 1, '삘': 1,
                 '삷': 1, '랏': 1, '삯': 1, '직': 1, '팔': 1, '틸': 1, '살': 1, '샃': 1, '판': 1, '람': 1, '증': 1, '삐': 1, '삽': 1,
                 '랙': 1, '껀': 1, '삿': 1, '랜': 1, '껄': 1, '징': 1, '꺼': 1, '샐': 1, '새': 1, '질': 1, '팍': 1, '꺾': 1, '상': 3,
                 '짐': 1, '껓': 1, '꺽': 1, '랴': 1, '색': 1, '랭': 1, '샘': 1, '짚': 1, '팝': 1, '짙': 1, '껨': 1, '껍': 1, '껌': 1,
                 '팸': 1, '껙': 1, '께': 1, '량': 1, '팜': 1, '패': 1, '팰': 1, '팥': 1, '샙': 1, '짬': 1, '째': 1, '팬': 1, '짭': 1,
                 '짤': 1, '껏': 1, '섀': 1, '렌': 1, '레': 1, '렙': 1, '꼉': 1, '쨍': 1, '섟': 1, '섨': 1, '짱': 1, '팡': 1, '섞': 1,
                 '석': 1, '섰': 1, '섣': 1, '선': 2, '략': 1, '설': 1, '섬': 1, '펀': 1, '랩': 1, '펌': 1, '셉': 1, '롄': 1, '섯': 1,
                 '렬': 1, '섶': 1, '꼭': 1, '세': 2, '꼬': 1, '꼽': 1, '꼼': 1, '꼿': 1, '꽁': 1, '셗': 1, '셥': 1, '짜': 1, '셦': 1,
                 '션': 1, '펙': 1, '페': 1, '짗': 1, '로': 1, '펠': 1, '록': 1, '펩': 1, '셤': 1, '꽝': 1, '셩': 1, '솀': 1, '롬': 1,
                 '샅': 1, '펴': 1, '쩡': 1, '솁': 1, '평': 1, '꽹': 1, '솎': 1, '솘': 1, '손': 1, '솕': 1, '소': 3, '솓': 1, '솔': 1,
                 '솜': 1, '꾐': 1, '속': 1, '솟': 1, '솧': 1, '삶': 1, '포': 1, '폭': 1, '삵': 1, '뢰': 1, '폴': 1, '쪼': 1, '쪽': 1,
                 '뢴': 1, '롱': 1, '셸': 1, '쫄': 1, '폿': 1, '퐁': 1, '폼': 1, '꾸': 1, '쇄': 1, '편': 1, '펜': 1, '쫏': 1, '료': 1,
                 '쇠': 1, '쇤': 1, '룡': 1, '룬': 1, '루': 1, '룩': 1, '룰': 1, '꿈': 1, '룻': 1, '쇽': 1, '숀': 1, '꿍': 1, '꿩': 1,
                 '꿱': 1, '뀀': 1, '푄': 1, '숄': 1, '꿸': 1, '푀': 1, '뤄': 1, '숏': 1, '뀅': 1, '숗': 1, '숑': 1, '쬐': 1, '뀌': 1,
                 '수': 4, '숙': 1, '순': 1, '숟': 1, '표': 1, '숩': 1, '푯': 1, '푼': 1, '푿': 1, '푹': 1, '풀': 1, '푸': 1, '숫': 1,
                 '풋': 1, '품': 1, '숨': 1, '풍': 1, '쩔': 1, '숭': 1, '숳': 1, '껭': 1, '런': 1, '숲': 1, '륄': 1, '쭈': 1, '껑': 1,
                 '샌': 1, '쭉': 1, '쉑': 1, '삼': 2, '산': 2, '끅': 1, '끄': 1, '쉐': 1, '짝': 1, '집': 1, '짓': 1, '숯': 1, '끊': 1,
                 '끌': 1, '끈': 1, '끝': 1, '쉡': 1, '류': 1, '륙': 1, '륜': 1, '륭': 1, '쉼': 1, '륵': 1, '르': 1, '지': 3, '진': 2,
                 '쭐': 1, '뤼': 1, '샋': 1, '끽': 1, '낀': 1, '끼': 1, '퓌': 1, '낄': 1, '퓐': 1, '낍': 1, '끕': 1, '낌': 1, '슁': 1,
                 '낑': 1, '낚': 1, '나': 2, '끓': 1, '끔': 1, '슌': 1, '슈': 1, '름': 1, '릉': 1, '슝': 1, '슘': 1, '슐': 1, '슛': 1,
                 '숱': 1, '쉬': 1, '슥': 1, '스': 1, '쉴': 1, '퓰': 1, '쉰': 1, '프': 1, '낛': 1, '난': 1, '플': 1, '픈': 1, '슭': 1,
                 '쉽': 1, '낙': 1, '낡': 1, '낟': 1, '습': 1, '날': 1, '낫': 1, '슴': 1, '낯': 1, '낮': 1, '슻': 1, '릴': 1, '쉿': 1,
                 '슉': 1, '를': 1, '승': 1, '남': 1, '낱': 1, '싄': 1, '끙': 1, '싁': 1, '립': 1, '낼': 1, '싀': 1, '링': 1, '냏': 1,
                 '슬': 1, '마': 2, '맔': 1, '막': 1, '만': 1, '퓨': 1, '픐': 1, '쯔': 1, '냄': 1, '내': 2, '말': 1, '픗': 1, '맣': 1,
                 '맏': 1, '많': 1, '맛': 1, '냐': 1, '픤': 1, '맑': 1, '끎': 1, '냉': 1, '매': 1, '냠': 1, '맥': 1, '맙': 1, '냥': 1,
                 '낳': 1, '낸': 1, '슷': 1, '끗': 1, '맬': 1, '맴': 1, '맘': 1, '냬': 1, '림': 1, '싥': 1, '쯜': 1, '률': 1, '시': 3,
                 '싯': 1, '실': 1, '심': 1, '싣': 1, '쯤': 1, '냅': 1, '맗': 1, '싱': 1, '싫': 1, '싸': 1, '맵': 1, '싹': 1, '맺': 1,
                 '맷': 1, '냇': 1, '필': 1, '먀': 1, '쯩': 1, '핌': 1, '맹': 1, '리': 1, '핀': 1, '맞': 1, '십': 1, '망': 1, '맡': 1,
                 '핑': 1, '피': 1, '학': 1, '핟': 1, '핍': 1, '하': 2, '할': 1, '싼': 1, '린': 1, '낭': 1, '납': 1, '맨': 1, '핏': 1,
                 '핡': 1, '픽': 1, '쌀': 1, '쌘': 1, '쌈': 1, '신': 2, '찐': 1, '찌': 1, '쌕': 1, '넋': 1, '넘': 1, '넥': 1, '항': 1,
                 '찢': 1, '쌧': 1, '합': 1, '해': 2, '핼': 1, '햄': 1, '찝': 1, '쌔': 1, '넌': 1, '햇': 1, '햅': 1, '쌸': 1, '핵': 1,
                 '넣': 1, '썍': 1, '네': 1, '쌩': 1, '넬': 1, '쌤': 1, '넝': 1, '핸': 1, '녓': 1, '착': 1, '핫': 1, '멈': 1, '찰': 1,
                 '찹': 1, '챈': 1, '채': 1, '멫': 1, '멋': 1, '참': 1, '멎': 1, '념': 1, '멘': 1, '향': 1, '찾': 1, '녜': 1, '녕': 1,
                 '썬': 1, '멧': 1, '멱': 1, '챗': 1, '며': 1, '챙': 1, '넓': 1, '헉': 1, '녑': 1, '놁': 1, '험': 1, '헐': 1, '척': 1,
                 '허': 1, '멸': 1, '썹': 1, '철': 1, '녯': 1, '논': 1, '놀': 1, '첨': 1, '명': 1, '면': 1, '놈': 1, '몌': 1, '농': 1,
                 '높': 1, '놰': 1, '쎅': 1, '천': 2, '헙': 1, '헛': 1, '처': 1, '헥': 1, '찔': 1, '체': 1, '헬': 1, '몯': 1, '첼': 1,
                 '몰': 1, '헴': 1, '헵': 1, '몸': 1, '몹': 1, '쳇': 1, '혁': 1, '현': 1, '못': 1, '혓': 1, '협': 1, '쏠': 1, '형': 1,
                 '쳠': 1, '쏩': 1, '쏨': 1, '혜': 1, '한': 2, '혬': 1, '뇟': 1, '뇡': 1, '쏴': 1, '뇌': 1, '뇔': 1, '뇨': 1, '호': 2,
                 '홉': 1, '홍': 1, '홋': 1, '확': 1, '환': 1, '화': 2, '뇽': 1, '홀': 1, '초': 2, '뫼': 1, '쐑': 1, '묑': 1, '촏': 1,
                 '촌': 1, '눛': 1, '촐': 1, '누': 1, '촙': 1, '묀': 1, '묏': 1, '가': 4, '촛': 1, '탄': 1, '눋': 1, '묘': 1, '각': 1,
                 '눙': 1, '눗': 1, '황': 1, '횃': 1, '쐬': 1, '묫': 1, '뭄': 1, '문': 2, '묻': 1, '묶': 1, '묵': 1, '무': 3, '물': 2,
                 '횔': 1, '뭀': 1, '획': 1, '횟': 1, '최': 1, '쵯': 1, '쵹': 1, '첵': 1, '목': 1, '모': 2, '몬': 1, '헤': 1, '쑨': 1,
                 '뉵': 1, '쑤': 1, '늄': 1, '헝': 1, '훈': 1, '훑': 1, '훔': 1, '느': 1, '늑': 1, '햐': 1, '함': 1, '쌍': 1, '쑷': 1,
                 '탐': 1, '쑹': 1, '탑': 1, '넉': 1, '찦': 1, '차': 1, '찡': 1, '택': 1, '춋': 1, '춍': 1, '태': 1, '넢': 1, '너': 1,
                 '찜': 1, '널': 1, '추': 1, '탠': 1, '뮈': 1, '탤': 1, '축': 1, '뮌': 1, '쵸': 1, '춘': 1, '찍': 1, '출': 1, '뮐': 1,
                 '탭': 1, '탬': 1, '식': 1, '춤': 1, '훠': 1, '쒜': 1, '훰': 1, '훤': 1, '훌': 1, '훅': 1, '훗': 1, '훨': 1, '뉴': 1,
                 '는': 1, '훼': 1, '늧': 1, '뮬': 1, '늙': 1, '충': 1, '늘': 1, '뮤': 1, '늠': 1, '늣': 1, '능': 1, '탕': 1, '탓': 1,
                 '늦': 1, '행': 1, '늪': 1, '휀': 1, '늬': 1, '갗': 1, '갏': 1, '갌': 1, '쒸': 1, '췌': 1, '갇': 1, '늴': 1, '타': 1,
                 '강': 2, '같': 1, '갓': 1, '갖': 1, '갈': 1, '탯': 1, '탱': 1, '값': 1, '갑': 1, '감': 2, '믄': 1, '간': 1, '늿': 1,
                 '믈': 1, '갚': 1, '므': 1, '믌': 1, '휑': 1, '믓': 1, '휘': 1, '니': 1, '님': 1, '휠': 1, '믠': 1, '닛': 1, '휨': 1,
                 '닝': 1, '닙': 1, '휫': 1, '닌': 1, '다': 2, '닦': 1, '뉫': 1, '뉨': 1, '쳐': 1, '닥': 1, '닢': 1, '휜': 1, '닉': 1,
                 '뭉': 1, '쓩': 1, '취': 1, '밄': 1, '쓸': 1, '밇': 1, '휴': 1, '훋': 1, '훙': 1, '후': 1, '미': 2, '믹': 1, '휼': 1,
                 '쓰': 1, '쓴': 1, '믯': 1, '민': 1, '흑': 1, '믿': 1, '씀': 1, '흘': 1, '씁': 1, '흉': 1, '흐': 1, '쓿': 1, '밍': 1,
                 '바': 2, '흙': 1, '밀': 1, '츈': 1, '밑': 1, '닼': 1, '닫': 1, '닻': 1, '츄': 1, '밠': 1, '닷': 1, '츠': 1, '댈': 1,
                 '흭': 1, '댑': 1, '댕': 1, '씬': 1, '갤': 1, '밤': 1, '발': 1, '밧': 1, '희': 1, '갠': 1, '방': 2, '댱': 1, '백': 2,
                 '츩': 1, '악': 1, '씹': 1, '배': 2, '아': 3, '츤': 1, '츰': 1, '뱜': 1, '앒': 1, '뱃': 1, '객': 1, '앏': 1, '앉': 1,
                 '뱁': 1, '뱐': 1, '앝': 1, '앍': 1, '츼': 1, '개': 2, '액': 1, '뱌': 1, '덜': 1, '치': 1, '답': 1, '츙': 1, '덛': 1,
                 '닭': 1, '흄': 1, '앰': 1, '얖': 1, '얄': 1, '덩': 1, '캠': 1, '덫': 1, '칡': 1, '얀': 1, '칼': 1, '덧': 1, '캄': 1,
                 '칩': 1, '얇': 1, '덭': 1, '양': 2, '덱': 1, '얌': 1, '뎁': 1, '번': 1, '뎀': 1, '캑': 1, '캅': 1, '벅': 1, '범': 1,
                 '캡': 1, '벗': 1, '침': 1, '뎧': 1, '벙': 1, '뎔': 1, '벚': 1, '뎡': 1, '얕': 1, '벡': 1, '어': 2, '캥': 1, '얭': 1,
                 '억': 1, '얹': 1, '벵': 1, '얻': 1, '얼': 1, '벨': 1, '볌': 1, '업': 1, '엊': 1, '돆': 1, '없': 1, '엘': 1, '에': 1,
                 '병': 1, '커': 1, '볍': 1, '엠': 1, '돤': 1, '컬': 1, '역': 1, '여': 2, '돓': 1, '돝': 1, '돛': 1, '컵': 1, '도': 3,
                 '돋': 1, '변': 1, '벳': 1, '뎜': 1, '칰': 1, '앵': 1, '캬': 1, '컷': 1, '캉': 1, '밋': 1, '엻': 1, '엽': 1, '케': 1,
                 '봋': 1, '봄': 1, '봅': 1, '돌': 1, '봇': 1, '봏': 1, '옘': 1, '옐': 1, '봉': 1, '됨': 1, '켕': 1, '예': 1, '켜': 1,
                 '켐': 1, '볶': 1, '된': 1, '될': 1, '되': 1, '됫': 1, '됴': 1, '켣': 1, '옦': 1, '옙': 1, '켯': 1, '켤': 1, '켠': 1,
                 '옛': 1, '온': 1, '옥': 1, '오': 3, '닐': 1, '옫': 1, '올': 1, '옭': 1, '옰': 1, '옮': 1, '옴': 1, '옳': 1, '믜': 1,
                 '옵': 1, '갉': 1, '옷': 1, '엿': 1, '와': 1, '옹': 1, '콛': 1, '코': 1, '둑': 1, '콘': 1, '콜': 1, '뵐': 1, '콩': 1,
                 '콕': 1, '콤': 1, '뵘': 1, '완': 1, '됭': 1, '왓': 1, '뵈': 1, '왕': 1, '왜': 1, '뵴': 1, '왠': 1, '둼': 1, '둥': 1,
                 '둣': 1, '둡': 1, '부': 3, '북': 1, '붇': 1, '불': 2, '콴': 1, '붉': 1, '분': 2, '붐': 1, '뒈': 1, '왱': 1, '켈': 1,
                 '왹': 1, '외': 2, '염': 1, '쾅': 1, '왼': 1, '왈': 1, '욀': 1, '욋': 1, '붑': 1, '뒝': 1, '붝': 1, '쾡': 1, '쾟': 1,
                 '요': 1, '붕': 1, '쾨': 1, '붙': 1, '붗': 1, '붚': 1, '욷': 1, '욿': 1, '우': 2, '욱': 1, '쾌': 1, '울': 1, '뒨': 1,
                 '운': 1, '듁': 1, '뒷': 1, '뷜': 1, '뷔': 1, '웁': 1, '드': 1, '둠': 1, '뷘': 1, '쿤': 1, '월': 1, '득': 1, '콰': 1,
                 '원': 2, '쿡': 1, '들': 1, '웻': 1, '쿨': 1, '듣': 1, '듧': 1, '듭': 1, '듬': 1, '웹': 1, '윈': 1, '윌': 1, '븍': 1,
                 '퀀': 1, '둘': 1, '브': 1, '쿵': 1, '윔': 1, '쿼': 1, '콥': 1, '븕': 1, '븘': 1, '윙': 1, '콧': 1, '딕': 1, '윗': 1,
                 '븓': 1, '블': 1, '퀘': 1, '유': 3, '육': 1, '윕': 1, '딘': 1, '윤': 1, '디': 1, '븨': 1, '콱': 1, '븟': 1, '딛': 1,
                 '율': 1, '딥': 1, '딜': 1, '딧': 1, '딩': 1, '윷': 1, '딤': 1, '으': 1, '융': 1, '윽': 1, '딮': 1, '퀴': 1, '퀸': 1,
                 '따': 1, '딲': 1, '갬': 1, '갭': 1, '을': 1, '은': 1, '욜': 1, '퀼': 1, '딸': 1, '퀵': 1, '딴': 1, '갱': 1, '큐': 1,
                 '딱': 1, '갯': 1, '갹': 1, '읏': 1, '읍': 1, '음': 1, '땃': 1, '빈': 1, '갸': 1, '땅': 1, '비': 3, '빌': 1, '빅': 1,
                 '응': 1, '빋': 1, '걍': 1, '의': 1, '딍': 1, '땍': 1, '때': 1, '빔': 1, '빗': 1, '빙': 1, '빚': 1, '땀': 1, '땔': 1,
                 '큘': 1, '빛': 1, '빠': 1, '빡': 1, '크': 1, '땜': 1, '클': 1, '인': 2, '이': 4, '킈': 1, '큼': 1, '잇': 1, '있': 1,
                 '잉': 1, '빨': 1, '잎': 1, '땡': 1, '땟': 1, '빰': 1, '겍': 1, '겇': 1, '겝': 1, '겥': 1, '빵': 1, '걱': 1, '건': 1,
                 '빽': 1, '빼': 1, '뺀': 1, '거': 2, '겅': 1, '겐': 1, '겜': 1, '겔': 1, '두': 2, '둔': 1, '겡': 1, '둗': 1, '겟': 1,
                 '훳': 1, '달': 1, '왯': 1, '왁': 1, '격': 1, '옻': 1}

    jobs = []
    for letter, max_i in page_nums.items():
        for i in range(1, max_i + 1):
            jobs.append(request(semaphore, target_dir, i, letter))

    await asyncio.gather(*jobs)


def merge_json():
    target_dir = 'tmp'
    data = []

    for filename in os.listdir(target_dir):
        file_path = os.path.join(target_dir, filename)
        with open(file_path, 'r') as f:
            data.extend(json.load(f))

    print(len(data))
    with open('async_output.json', 'w') as f:
        json.dump(data, f)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
    merge_json()
