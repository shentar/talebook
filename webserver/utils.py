#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


import datetime
import logging
import os
import re
from gettext import gettext as _

import PyPDF2
from PyPDF2 import generic

from webserver import constants
from webserver.main import CONF
from webserver.models import Item
from webserver.plugins.meta import douban, baike


class SimpleBookFormatter:
    """格式化calibre book的字段"""

    def __init__(self, calibre_book_item, cdn_url):
        self.cdn_url = cdn_url
        self.book = calibre_book_item

    def get_collector(self):
        collector = self.book.get("collector", None)
        if isinstance(collector, dict):
            collector = collector.get("username", None)
        elif collector:
            collector = collector.username
        return collector

    def val(self, k, default_value=_("Unknown")):
        v = self.book.get(k, None)
        if not v:
            v = default_value
        if isinstance(v, datetime.datetime):
            return v.strftime("%Y-%m-%d").zfill(10)
        return v

    def format(self):
        b = self.book
        b["ts"] = b["last_modified"].strftime("%s")
        return {
            "id": b["id"],
            "title": b["title"],
            "rating": b["rating"],
            "timestamp": self.val("timestamp"),
            "pubdate": self.val("pubdate"),
            "author": ", ".join(b["authors"]),
            "authors": b["authors"],
            "author_sort": self.val("author_sort"),
            "tag": " / ".join(b["tags"]),
            "tags": b["tags"],
            "publisher": self.val("publisher"),
            "comments": self.val("comments", _(u"暂无简介")),
            "series": self.val("series", None),
            "language": self.val("language", None),
            "isbn": self.val("isbn", None),
            "img": self.cdn_url + "/get/cover/%(id)s.jpg?t=%(ts)s" % b,
            "thumb": self.cdn_url + "/get/thumb_60x80/%(id)s.jpg?t=%(ts)s" % b,
            # 额外填充的字段
            "collector": self.get_collector(),
            "count_visit": self.val("count_visit", 0),
            "count_download": self.val("count_download", 0),
            "douban_id": self.val("website"),
        }


class BrefInfoFormatter(SimpleBookFormatter):
    """格式化摘要信息"""

    def format(self):
        b = self.book
        b["ts"] = b["last_modified"].strftime("%s")
        return {
            "id": b["id"],
            "title": b["title"],
            "comments": self.val("comments", _(u"暂无简介")),
            "img": self.cdn_url + "/get/cover/%(id)s.jpg?t=%(ts)s" % b,
        }


class BookFormatter:
    def __init__(self, tornado_handler, calibre_book_item):
        self.db = tornado_handler.db
        self.book = calibre_book_item
        self.cdn_url = tornado_handler.cdn_url
        self.api_url = tornado_handler.api_url
        self.handler = tornado_handler

    def get_files(self):
        files = []
        book_id = self.book["id"]
        for fmt in self.book.get("available_formats", ""):
            try:
                filesize = self.db.sizeof_format(book_id, fmt, index_is_id=True)
            except:
                continue
            item = {
                "format": fmt,
                "size": filesize,
                "href": self.cdn_url + "/api/book/%s.%s" % (book_id, fmt),
            }
            files.append(item)
        return files

    def get_permissions(self):
        h = self.handler
        return {
            # 图书权限数据
            "is_public": True,
            "is_owner": h.is_admin() or h.is_book_owner(self.book["id"], h.user_id()),
        }

    def format(self, with_files=False, with_perms=False, for_list_card=False):
        if for_list_card:
            f = BrefInfoFormatter(self.book, self.cdn_url)
        else:
            f = SimpleBookFormatter(self.book, self.cdn_url)

        data = f.format()
        if not for_list_card:
            data.update(
                {
                    "author_url": self.api_url + "/author/" + f.val("author_sort"),
                    "publisher_url": self.api_url + "/publisher/" + f.val("publisher"),
                }
            )
            if with_files:
                data["files"] = self.get_files()
            if with_perms:
                data.update(self.get_permissions())
        return data


def compare_books_by_rating_or_id(x, y):
    a = x.get("rating", 0) or 0
    b = y.get("rating", 0) or 0

    if a > b:
        return 1
    elif a < b:
        return -1
    elif x["id"] > y["id"]:
        return 1
    else:
        return -1


def compare_books_by_visit_download(x, y):
    x_ = (x.get("count_visit", 0) * 2 or 0) + (x.get("count_download", 0) or 0)
    y_ = (y.get("count_visit", 0) * 2 or 0) + (y.get("count_download", 0) or 0)

    if x_ > y_:
        return 1
    elif x_ < y_:
        return -1
    elif x["id"] > y["id"]:
        return 1
    else:
        return -1


def adjust_book_info(full_path, file_name, mi):
    try:
        filter_tags(mi)

        # 对于PDF文件，大于6MB，多半是扫描版，扫描版一般PDF内部的title填写错误，直接使用文件名。
        fmt = file_name.split(".")[-1].lower()
        if fmt == "pdf":
            f = os.stat(full_path)
            if f.st_size > 6 * 1024 * 1024:
                mi.title = re.sub(u"[-\s[{【(（+=<_].*", "", file_name)
    except Exception as e:
        logging.warning("some err: path: %s, mi: %s, err: %r" % (full_path, mi, e))


INVALID_TAG_CHA = ".-:：（【{[("
INVALID_TAG_STR = ["sanqiu", "novel"]


def filter_tags(mi):
    try:
        # 去除无效tag
        for t in mi.tags:
            tag = t.lower()
            for i in INVALID_TAG_STR:
                if i in tag:
                    mi.tags.remove(t)
            for i in INVALID_TAG_CHA:
                if i in tag:
                    mi.tags.remove(t)
    except Exception as e:
        logging.warning("some err: mi: %s, err: %r" % (mi, e))


def save_user_his(session, action, user, book_id):
    extra = user.extra
    history = extra.get(action, [])
    if len(history) > 0:
        for i in range(0, len(history)):
            if history[i] == book_id:
                history.pop(i)
                break

    history.insert(0, book_id)
    extra[action] = history
    user.extra.update(extra)
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logging.warning("some err: %r" % e)


def save_website(session, book_id, provider_key, provider_value):
    if provider_key != douban.KEY:
        return

    douban_id = provider_value
    try:
        item = session.query(Item).filter(Item.book_id == book_id).one()
    except:
        item = Item()
        item.book_id = book_id
        item.save()

    if item.website != douban_id:
        item.website = douban_id
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            logging.warning("some err: %r" % e)


def update_book_meta(mi, refer_mi):
    if len(refer_mi.tags) == 0:
        ts = []
        for nn, tags in constants.BOOK_NAV:
            for tag in tags:
                if (tag in refer_mi.title or tag in refer_mi.comments or tag in refer_mi.authors) and \
                        tag not in constants.ESCAPED_TAGS:
                    ts.append(tag)
        if len(ts) > 0:
            refer_mi.tags += ts[:8]
            logging.info("tags are %s" % ','.join(refer_mi.tags))
    filter_tags(mi)
    mi.smart_update(refer_mi, replace_metadata=True)


def get_proper_book(api, books, mi):
    if len(books) == 0:
        return books

    has_isbn = True
    if not mi.isbn \
            or mi.isbn == baike.BAIKE_ISBN \
            or str(mi.isbn).startswith('000000000'):
        has_isbn = False

    isbn_id = -1
    ids = []
    for i, b in enumerate(books):
        if has_isbn and mi.isbn == b.get("isbn13", "xxx"):
            isbn_id = i
        if mi.title == b.get("title") and mi.publisher == b.get("publisher"):
            ids.append(i)

    for i in ids:
        b = books[i]
        books = books[:i] + books[i + 1:]
        books.insert(0, b)

    if isbn_id == -1:
        # 若有ISBN号，但是却没搜索出来，则精准查询一次ISBN
        # 总是把最佳书籍放在第一位
        if has_isbn:
            book = api.get_book_by_isbn(mi.isbn)
            logging.info("get book by isbn: %s" % book)
            if book:
                books = list(books)
                books.insert(0, book)
    else:
        b = books[isbn_id]
        books = books[:isbn_id] + books[isbn_id + 1:]
        books.insert(0, b)

    return books


def plugin_search_books(mi):
    title = re.sub(u"[-\s[{【(（+=<_].*", "", mi.title)
    api = douban.DoubanBookApi(
        CONF["douban_apikey"],
        CONF["douban_baseurl"],
        copy_image=False,
        manual_select=False,
        maxCount=CONF["douban_max_count"],
    )
    # first, search title
    books = []
    try:
        books = api.search_books(title) or []
    except:
        logging.error(_(u"豆瓣接口查询 %s 失败" % title))

    books = get_proper_book(api, books, mi)
    books = [api._metadata(b) for b in books]

    # append baidu book
    # api = baike.BaiduBaikeApi(copy_image=False)
    # try:
    #     book = api.get_book(title)
    # except:
    #     return {"err": "httprequest.baidubaike.failed", "msg": _(u"百度百科查询失败")}
    # if book:
    #     books.append(book)
    return books


def plugin_get_book_meta(provider_key, provider_value, mi):
    if provider_key == baike.KEY:
        title = re.sub(u"[(（].*", "", mi.title)
        api = baike.BaiduBaikeApi(copy_image=True)
        try:
            return api.get_book(title)
        except:
            logging.info("百度百科查询失败。")

    if provider_key == douban.KEY:
        mi.douban_id = provider_value
        api = douban.DoubanBookApi(
            CONF["douban_apikey"],
            CONF["douban_baseurl"],
            copy_image=True,
            maxCount=CONF["douban_max_count"],
        )
        try:
            return api.get_book(mi)
        except:
            logging.info("豆瓣接口查询失败")

    return None


def check_email(addr):
    if not addr:
        return False
    if re.match(r"[^@]+@[^@]+\.[^@]+", addr):
        return True
    return False


class PdfCopyer:
    def __init__(self):
        self.page_marks = {}
        self.page_labels = {}

    def get_bookmark_info(self, str_line, level_id):
        dtn = str_line
        idobj = dtn.page
        if idobj and not isinstance(idobj, generic.NullObject):
            return level_id, self.page_labels[idobj.idnum], dtn.title, dtn.typ
        else:
            return None

    def get_fist_grade(self, str_line, level_id=0):
        num = level_id
        parent_id = level_id
        for sub_line in str_line:
            if isinstance(sub_line, list):
                num, parent_id = self.get_fist_grade(sub_line, num)
            else:
                num = num + 1
                self.page_marks[num] = self.get_bookmark_info(sub_line, level_id)
        return num, parent_id

    def __call__(self, pdf_file, title):
        pdf_reader = PyPDF2.PdfFileReader(pdf_file)
        pdf_writer = PyPDF2.PdfFileWriter()
        count = pdf_reader.numPages
        for i in range(count):
            page = pdf_reader.getPage(i)
            self.page_labels[page.indirect_ref.idnum] = i
            pdf_writer.addPage(page)

        outlines = pdf_reader.getOutlines()
        self.get_fist_grade(outlines)
        pg_marks = {}
        for i in range(1, len(self.page_marks) + 1):
            if not self.page_marks[i]:
                continue
            (pt_index, pgnum, pgtitle, bktyp) = self.page_marks[i]
            if pt_index == 0:
                pg_marks[i] = pdf_writer.addBookmark(pgtitle, pgnum)
            else:
                pts = pg_marks[pt_index]
                pg_marks[i] = pdf_writer.addBookmark(pgtitle, pgnum, parent=pts)

        pdf_writer.addMetadata(pdf_reader.getDocumentInfo())
        pdf_writer.addMetadata({'/Title': '%s' % title})

        return pdf_writer
