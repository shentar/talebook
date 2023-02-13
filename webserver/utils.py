#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


import datetime
import re
from gettext import gettext as _

import PyPDF2
from PyPDF2 import generic


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
            return v.strftime("%Y-%m-%d")
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
