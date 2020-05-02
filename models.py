# !/use/bin/python3
# _*_ coding:utf-8 _*_
# __author__ : __ajiang__
# 2020/4/30

from datetime import datetime

from peewee import *

db = MySQLDatabase('biquge', host='127.0.0.1', port=3306, user='root', password='admin123')


class BaseModel(Model):
    class Meta:
        database = db


class NovelCategories(BaseModel):
    id = PrimaryKeyField(verbose_name='章节ID')
    name = CharField(max_length=10, default='', verbose_name='分类名称')
    create_time = DateTimeField(default=datetime.now, verbose_name='创建时间')


class NovelContent(BaseModel):
    id = IntegerField(primary_key=True, verbose_name='小说ID')
    category = ForeignKeyField(NovelCategories, verbose_name='小说类别', null=True, related_name='category',
                               on_delete='SET NULL')
    name = CharField(max_length=50, default='', verbose_name='小说名称')
    description = TextField(default='', verbose_name='小说简介')
    image = CharField(max_length=200, default='', verbose_name='小说图片')
    author = CharField(max_length=50, default='', verbose_name='小说作者')
    last_update = DateTimeField(default=datetime.now, verbose_name='最后更新时间')
    status = CharField(default='', max_length=10, verbose_name='小说状态')
    create_time = DateTimeField(default=datetime.now, verbose_name='创建时间')


class NovelChapter(BaseModel):
    id = IntegerField(primary_key=True, verbose_name='章节ID')
    novel = ForeignKeyField(NovelContent, verbose_name='小说名称', null=True, related_name='novel', on_delete='SET NULL')
    title = CharField(max_length=100, default='', verbose_name='章节名称')
    content = TextField(default='', verbose_name='章节内容')
    pre_chapter = IntegerField(null=True, verbose_name='上一章ID')
    next_chapter = IntegerField(null=True, verbose_name='下一章ID')
    create_time = DateTimeField(default=datetime.now, verbose_name='创建时间')

    
if __name__ == '__main__':
    db.create_tables([NovelCategories, NovelContent, NovelChapter])
