# !/use/bin/python3
# _*_ coding:utf-8 _*_
# __author__ : __ajiang__
# 2020/4/30
import re
import requests
from urllib import parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from scrapy import Selector
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from biquge_spider.models import *

# webdriver 无头模式 启动的时候不显示浏览器界面
chrome_options = Options()
chrome_options.add_argument("--headless")

#  谷歌文档提示要加上这个属性来规避一些bug
chrome_options.add_argument("--disable-gpu")

# webdriver 不加载图片模式
chrome_options.add_argument("blink-settings=imagesEnabled=false")

# 笔趣阁的主路径
domain = ''

executor = ThreadPoolExecutor(max_workers=10)


def get_chapter_id(url):
    """
    :param url: 章节url
    :return: 章节ID
    """
    res = re.match('([0-9]+)', url)
    if res:
        return int(res.group(1))
    return None


def get_categories():
    """
    获取保存小说类别，并抽取分类的路径，以获取所有的路径
    :return: categories_list
    """
    categories_list = []
    text = requests.get(domain).text
    sel = Selector(text=text)
    all_categories = sel.xpath('//div[@class="nav"]//li')
    category = NovelCategories()
    for _category in all_categories:
        url = _category.xpath('.//a/@href').extract()[0]
        _url = re.match('/xiaoshuo([0-9]+)', url)
        if _url:
            categories_list.append(parse.urljoin(domain, url))
            category_name = _category.xpath('.//a/text()').extract()[0]
            novel_id = _url.group(1)
            if NovelCategories.select().where(NovelCategories.name == category_name):
                category.id = novel_id
                category.name = category_name
                category.save()
            else:
                category.id = novel_id
                category.name = category_name
                category.save(force_insert=True)
    return categories_list


def get_novel_url(url):
    """
    :param url: 小说列表的链接
    :return: None
    """
    category_url = requests.get(parse.urljoin(domain, url)).text
    sel = Selector(text=category_url)
    novel_urls = sel.xpath('//div[@class="ll"]//div[@class="item"]')
    for novel_url in novel_urls:
        _url = novel_url.xpath('.//div[@class="image"]/a/@href').extract()[0]
        executor.submit(parse_novel_detail, parse.urljoin(domain, _url))

    """
    在倒数第二页的时候，就没有下一页的按钮了，
    我们就可以直接判断当前的url 和最后一个URl是不是一样 如果不一样还有最后一页需要获取
    """
    next_page = sel.xpath('//div[@id="pagelink"]/a[@class="next"]/text()').extract()
    last_link = sel.xpath('//div[@id="pagelink"]/a[@class="last"]/@href').extract()[0]
    if next_page:
        next_link = sel.xpath('//div[@id="pagelink"]/a[@class="next"]/@href').extract()[0]
        get_novel_url(parse.urljoin(domain, next_link))
    elif url != last_link:
        get_novel_url(parse.urljoin(domain, last_link))


def parse_novel_detail(novel_url):
    """
    :param novel_url: 小说详情页链接
    :return: None
    """
    novel_detail_text = requests.get(novel_url).text
    sel = Selector(text=novel_detail_text)
    novel = NovelContent()

    novel_id = novel_url.split('/')[-2]
    novel.id = novel_id

    novel_category = sel.xpath('//meta[@property="og:novel:category"]/@content').extract()
    if novel_category:
        novel_category_name = novel_category[0]
        _novel_category = NovelCategories.select().where(NovelCategories.name == novel_category_name)
        novel.category = _novel_category

    novel_status = sel.xpath('//meta[@property="og:novel:status"]/@content').extract()
    if novel_status:
        novel.status = novel_status[0]

    novel_image = sel.xpath('//meta[@property="og:image"]/@content').extract()
    if novel_image:
        novel.image = novel_image[0]

    novel_name = sel.xpath('//meta[@property="og:novel:book_name"]/@content').extract()
    if novel_name:
        novel.name = novel_name[0]
        print('开始爬取小说:{}'.format(novel_name[0]))

    novel_author = sel.xpath('//meta[@property="og:novel:author"]/@content').extract()
    if novel_author:
        novel.author = novel_name[0]

    novel_update_time = sel.xpath('//meta[@property="og:novel:update_time"]/@content').extract()
    if novel_update_time:
        novel.last_update = datetime.strptime(novel_update_time[0], '%Y-%m-%d %H:%M:%S')

    novel_description = sel.xpath('//meta[@property="og:description"]/@content').extract()
    if novel_description:
        novel.description = novel_description[0]

    # 判断这本书在不在数据库里面
    _novel = NovelContent.select().where(NovelContent.id == novel_id)
    if _novel:
        novel.save()
    else:
        novel.save(force_insert=True)
    print('小说{}爬取完成'.format(novel_name[0]))
    # 判断是否需要重新抓取新的章节 或者说这里不管，就把剩下的操作全部丢给解析章节的函数
    novel_chapter_urls = sel.xpath('//div[@id="list"]//dd')
    for novel_chapter_url in novel_chapter_urls:
        if novel_chapter_url.xpath('.//a/@href').extract():
            chapter_url = novel_chapter_url.xpath('.//a/@href').extract()[0]
            executor.submit(parse_novel_chapter, parse.urljoin(novel_url, chapter_url))


def parse_novel_chapter(chapter_url):
    """

    :param chapter_url: 小说详情页链接
    :return: None
    pass
    """
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en,zh;q=0.9,ar;q=0.8,zh-CN;q=0.7,zh-TW;q=0.6,zh-HK;q=0.5",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Host": "www.biquku.la",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36",

    }
    html = requests.get(chapter_url, headers=headers)
    # 使用utf-8编码解码
    html.encoding = 'UTF-8'
    page_text = html.text
    sel = Selector(text=page_text)
    chapter = NovelChapter()
    # 我们从章节的URL里面获取章节ID
    result_chapter = re.match('.*\/([0-9]+)\.html', chapter_url)
    chapter_id = 0
    if result_chapter:
        chapter_id = int(result_chapter.group(1))
    result_chapter = NovelChapter.select().where(NovelChapter.id == chapter_id)

    result_novel = re.match('.*\/([0-9]+)\/[0-9]+.html', chapter_url)
    novel_id = 0
    if result_novel:
        novel_id = int(result_novel.group(1))
    res_novel = NovelContent.select().where(NovelContent.id == novel_id)

    chapter_next_btn = sel.xpath('//div[@class="bottem1"]//a[contains(text(), "下一章")]/@href').extract()
    chapter_pre_btn = sel.xpath('//div[@class="bottem1"]//a[contains(text(), "上一章")]/@href').extract()
    chapter_domain = sel.xpath('//div[@class="bottem1"]//a[contains(text(), "章节列表")]/@href').extract()[0]
    if not result_chapter:
        chapter.id = chapter_id
        try:
            if result_novel:
                chapter.novel = res_novel
        except Exception as e:
            chapter.novel = novel_id
        chapter_title = sel.xpath('//div[@class="bookname"]/h1/text()').extract()
        if chapter_title:
            chapter.title = chapter_title[0]
            print('开始爬取章节:{}'.format(chapter_title[0]))
        chapter_content = sel.xpath('//div[@id="content"]').extract()
        if chapter_content:
            chapter.content = chapter_content[0]

        if '.html' in chapter_next_btn[0]:
            chapter.next_chapter = get_chapter_id(chapter_next_btn[0])

        if '.html' in chapter_pre_btn[0]:
            chapter.pre_chapter = get_chapter_id(chapter_pre_btn[0])

        chapter.save(force_insert=True)
        print('爬取章节{}结束'.format(chapter_title[0]))
    # 解析下一章的信息
    if '.html' in chapter_next_btn[0]:
        executor.submit(parse_novel_chapter, parse.urljoin(domain, chapter_domain + chapter_next_btn[0]))


if __name__ == '__main__':
    # 任务列表，往线程池里面提交任务
    categories_urls = get_categories()
    task_list = []
    for url in categories_urls:
        task_list.append(executor.submit(get_novel_url, url))

    wait(task_list, return_when=ALL_COMPLETED)
