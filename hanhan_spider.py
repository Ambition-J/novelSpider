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

from biquge_spider.models import *

# 笔趣阁的主路径
domain = 'http://www.biquku.la/'

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
    # requests 获取的中文返回乱码所以使用 selenum 来获取，这种方式应该会慢但是我们可以用多线程爬取
    html = requests.get(chapter_url)
    html.encoding = 'gbk'
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
            chapter.pre_chapter = get_chapter_id(chapter_next_btn[0])

        chapter.save(force_insert=True)
        print('爬取章节{}结束'.format(chapter_title[0]))
    # 解析下一章的信息
    if '.html' in chapter_next_btn[0]:
        executor.submit(parse_novel_chapter, parse.urljoin(domain, chapter_domain + chapter_next_btn[0]))


if __name__ == '__main__':
    # 任务列表，往线程池里面提交任务
    task_list = [executor.submit(parse_novel_detail, '')]
    wait(task_list, return_when=ALL_COMPLETED)
