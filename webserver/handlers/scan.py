#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import hashlib
import logging
import os
import threading
import time
import traceback
from gettext import gettext as _

import sqlalchemy
import tornado

from webserver import loader
from webserver.handlers.base import BaseHandler, auth, js, is_admin
from webserver.models import Item, ScanFile

CONF = loader.get_settings()
SCAN_EXT = ["azw", "azw3", "epub", "mobi", "pdf", "txt"]
SCAN_DIR_PREFIX = "/data/"  # 限定扫描必须在/data/目录下，以防黑客扫描到其他系统目录


class Scanner:
    def __init__(self, calibre_db, ScopedSession, user_id=None, base_handler=None):
        self.base_handler = base_handler
        self.db = calibre_db
        self.user_id = user_id
        self.func_new_session = ScopedSession
        self.curret_thread = threading.get_ident()
        self.bind_new_session()

    def bind_new_session(self):
        # NOTE 起线程后台运行后，如果不开新的session，会出现session对象的绑定错误
        self.session = self.func_new_session()

    def allow_backgrounds(self):
        """for unittest control"""
        return True

    def save_or_rollback(self, row):
        try:
            row.save()
            self.session.commit()
            bid = "[ book-id=%s ]" % row.book_id
            logging.info("update: status=%-5s, path=%s %s", row.status, row.path, bid if row.book_id > 0 else "")
            return True
        except Exception as err:
            logging.error(traceback.format_exc())
            self.session.rollback()
            logging.warning("save error: %s", err)
            return False

    def run_scan(self, path_dir):
        sem = threading.Semaphore(value=1)
        if not self.allow_backgrounds():
            self.do_scan(path_dir, sem)
        else:
            logging.info("run into background thread")

            t = threading.Thread(name="do_scan", target=self.do_scan, args=(path_dir,sem,))
            t.setDaemon(True)
            t.start()
        sem.acquire(timeout=30)
        return 1

    def do_scan(self, path_dir, sem):
        from calibre.ebooks.metadata.meta import get_metadata

        if threading.get_ident() != self.curret_thread:
            self.bind_new_session()

        # 生成任务（粗略扫描），前端可以调用API查询进展
        tasks = []
        for dirpath, __, filenames in os.walk(path_dir):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                if not os.path.isfile(fpath):
                    continue

                fmt = fpath.split(".")[-1].lower()
                if fmt not in SCAN_EXT:
                    # logging.debug("bad format: [%s] %s", fmt, fpath)
                    continue
                tasks.append((fname, fpath, fmt))

        # 生成任务ID
        scan_id = int(time.time())
        logging.info("========== start to check files size & name ============")

        rows = []
        first_time = True
        for fname, fpath, fmt in tasks:
            # logging.info("Scan: %s", fpath)
            if self.session.query(ScanFile).filter(ScanFile.path == fpath).count() > 0:
                # 如果已经有相同的文件记录，则跳过
                continue

            # 先用fpath作为hash填入，后面会修改为正式的值。
            row = ScanFile(fpath, fpath, scan_id)
            if not self.save_or_rollback(row):
                continue
            if first_time:
                first_time = False
                sem.release()
            rows.append(row)

        if first_time:
            sem.release()

        logging.info("========== start to check files hash & meta ============")
        # 检查文件哈希值，检查DB重复情况
        inserted_hash = set()
        for row in rows:
            fpath = row.path
            # 尝试解析metadata
            fmt = fpath.split(".")[-1].lower()
            with open(fpath, "rb") as stream:
                mi = get_metadata(stream, stream_type=fmt, use_libprs_metadata=True)

            row.title = mi.title
            row.author = mi.author_sort
            row.publisher = mi.publisher
            row.tags = ", ".join(mi.tags)
            row.status = ScanFile.READY  # 设置为可处理

            # TODO calibre提供的书籍重复接口只有对比title；应当提前对整个书库的文件做哈希，才能准确去重
            books = self.db.books_with_same_title(mi)
            if books:
                row.book_id = books.pop()
                row.status = ScanFile.EXIST

            # 使用文件元数据计算Hash值。避免全文读取数据耗时过长。
            sha256 = hashlib.sha256()
            sha256.update((row.title if row.title else "").encode("UTF-8"))
            sha256.update((row.author if row.author else "").encode("UTF-8"))
            sha256.update((row.publisher if row.publisher else "").encode("UTF-8"))
            sha256.update((row.tags if row.tags else "").encode("UTF-8"))
            sha256.update(hex(os.path.getsize(fpath if fpath else "")).encode("UTF-8"))
            hash_str = "sha256:" + sha256.hexdigest()

            if hash_str in inserted_hash or self.session.query(ScanFile).filter(ScanFile.hash == hash_str).count() > 0:
                # 如果已经有相同的哈希值，则删掉本任务
                row.status = ScanFile.DROP
            row.hash = hash_str
            inserted_hash.add(hash_str)
            if not self.save_or_rollback(row):
                continue
        return True

    def delete(self, hashlist):
        query = self.session.query(ScanFile)
        if isinstance(hashlist, (list, tuple)):
            query = query.filter(ScanFile.hash.in_(hashlist))
        elif isinstance(hashlist, str):
            query = query.filter(ScanFile.hash == hashlist)
        count = query.delete()
        self.session.commit()
        return count

    def resume_last_import(self):
        # TODO
        return False

    def build_query(self, hashlist):
        query = self.session.query(ScanFile).filter(
            ScanFile.status == ScanFile.READY
        )  # .filter(ScanFile.import_id == 0)
        if isinstance(hashlist, (list, tuple)):
            query = query.filter(ScanFile.hash.in_(hashlist))
        elif isinstance(hashlist, str):
            query = query.filter(ScanFile.hash == hashlist)
        return query

    def run_import(self, hashlist):
        if self.resume_last_import():
            return 1

        total = self.build_query(hashlist).count()

        if not self.allow_backgrounds():
            self.do_import(hashlist)
        else:
            t = threading.Thread(name="do_import", target=self.do_import, args=(hashlist,))
            t.setDaemon(True)
            t.start()
        return total

    def do_import(self, hashlist):
        from calibre.ebooks.metadata.meta import get_metadata

        if threading.get_ident() != self.curret_thread:
            self.bind_new_session()

        # 生成任务ID
        import_id = int(time.time())

        query = self.build_query(hashlist)
        query.update({ScanFile.import_id: import_id}, synchronize_session=False)
        self.session.commit()

        # 逐个处理
        for row in query.all():
            fpath = row.path
            fmt = fpath.split(".")[-1].lower()
            with open(fpath, "rb") as stream:
                mi = get_metadata(stream, stream_type=fmt, use_libprs_metadata=True)

            # 再次检查是否有重复书籍
            books = self.db.books_with_same_title(mi)
            if books:
                row.status = ScanFile.EXIST
                row.book_id = books.pop()
                self.save_or_rollback(row)
                continue

            logging.info("import [%s] from %s", mi.title, fpath)
            row.book_id = self.db.import_book(mi, [fpath])
            row.status = ScanFile.IMPORTED
            self.save_or_rollback(row)
            self.base_handler.user_history("upload_history", row.book_id)
            # 添加关联表
            item = Item()
            item.book_id = row.book_id
            item.collector_id = self.user_id
            try:
                item.save()
            except Exception as err:
                self.session.rollback()
                logging.error("save link error: %s", err)
        return True

    def import_status(self):
        import_id = self.session.query(sqlalchemy.func.max(ScanFile.import_id)).scalar()
        if import_id is None:
            return (0, {ScanFile.READY: 0})
        query = self.session.query(ScanFile.status).filter(ScanFile.import_id == import_id)
        return (import_id, self.count(query))

    def scan_status(self):
        scan_id = self.session.query(sqlalchemy.func.max(ScanFile.scan_id)).scalar()
        if scan_id is None:
            return (0, {ScanFile.NEW: 0})
        query = self.session.query(ScanFile.status).filter(ScanFile.scan_id == scan_id)
        return (scan_id, self.count(query))

    def count(self, query):
        rows = query.all()
        count = {
            "total": len(rows),
            ScanFile.NEW: 0,
            ScanFile.DROP: 0,
            ScanFile.EXIST: 0,
            ScanFile.READY: 0,
            ScanFile.IMPORTED: 0,
        }
        for row in rows:
            if row.status not in count:
                count[row.status] = 0
            count[row.status] += 1
        return count


class ScanList(BaseHandler):
    @js
    @auth
    def get(self):
        if not self.admin_user:
            return {"err": "permission.not_admin", "msg": _(u"当前用户非管理员")}

        num = max(10, int(self.get_argument("num", "20")))
        page = max(0, int(self.get_argument("page", "1")) - 1)
        sort = self.get_argument("sort", "access_time")
        desc = self.get_argument("desc", "desc")
        logging.debug("num=%d, page=%d, sort=%s, desc=%s" % (num, page, sort, desc))

        # get order by query args
        order = {
            "id": ScanFile.id,
            "path": ScanFile.path,
            "name": ScanFile.name,
            "create_time": ScanFile.create_time,
            "update_time": ScanFile.update_time,
        }.get(sort, ScanFile.create_time)
        order = order.asc() if desc == "false" else order.desc()
        query = self.session.query(ScanFile).order_by(order)
        total = query.count()
        start = page * num

        response = []
        for s in query.limit(num).offset(start).all():
            d = {
                "id": s.id,
                "path": s.path,
                "hash": s.hash,
                "title": s.title,
                "author": s.author,
                "publisher": s.publisher,
                "tags": s.tags,
                "status": s.status,
                "book_id": s.book_id,
                "create_time": s.create_time.strftime("%Y-%m-%d %H:%M:%S") if s.create_time else "N/A",
                "update_time": s.update_time.strftime("%Y-%m-%d %H:%M:%S") if s.update_time else "N/A",
            }
            response.append(d)
        return {"err": "ok", "items": response, "total": total, "scan_dir": CONF["scan_upload_path"]}


class ScanMark(BaseHandler):
    @js
    @is_admin
    def post(self):
        return {"err": "ok", "msg": _(u"发送成功")}


class ScanRun(BaseHandler):
    @js
    @is_admin
    def post(self):
        path = CONF["scan_upload_path"]
        if not path.startswith(SCAN_DIR_PREFIX):
            return {"err": "params.error", "msg": _(u"参数错误")}
        m = Scanner(self.db, self.settings["ScopedSession"])
        total = m.run_scan(path)
        if total == 0:
            return {"err": "empty", "msg": _("目录中没有找到符合要求的书籍文件！")}
        return {"err": "ok", "msg": _(u"开始扫描了"), "total": total}


class ScanDelete(BaseHandler):
    @js
    @is_admin
    def post(self):
        req = tornado.escape.json_decode(self.request.body)
        hashlist = req["hashlist"]
        if not hashlist:
            return {"err": "params.error", "msg": _(u"参数错误")}
        if hashlist == "all":
            hashlist = None
        delete_success = req["delete_success"]
        delete_failed = req["delete_failed"]
        logging.info("delete_success: %s, delete_failed: %s" % (delete_success, delete_failed))

        delete_files = []
        records = self.session.query(ScanFile).filter(ScanFile.hash.in_(hashlist))
        for record in records:
            if (ScanFile.IMPORTED == record.status) and delete_success:
                delete_files.append(record.path)
                logging.info("try to delete one imported successfully file: %s" % record.path)
            if (ScanFile.IMPORTED != record.status) and delete_failed:
                delete_files.append(record.path)
                logging.info("try to delete one imported failed file: %s" % record.path)

        m = Scanner(self.db, self.settings["ScopedSession"])

        count = m.delete(hashlist)

        for file in delete_files:
            if os.path.isfile(file):
                os.remove(file)

        return {"err": "ok", "msg": _(u"删除成功"), "count": count}


class ScanStatus(BaseHandler):
    @js
    @is_admin
    def get(self):
        m = Scanner(self.db, self.settings["ScopedSession"])
        status = m.scan_status()[1]
        return {"err": "ok", "msg": _(u"成功"), "status": status}


class ImportRun(BaseHandler):
    @js
    @is_admin
    def post(self):
        req = tornado.escape.json_decode(self.request.body)
        hashlist = req["hashlist"]
        if not hashlist:
            return {"err": "params.error", "msg": _(u"参数错误")}
        if hashlist == "all":
            hashlist = None

        m = Scanner(self.db, self.settings["ScopedSession"],
                    user_id=self.user_id(), base_handler=self)
        total = m.run_import(hashlist)
        if total == 0:
            return {"err": "empty", "msg": _("没有等待导入书库的书籍！")}
        return {"err": "ok", "msg": _(u"扫描成功")}


class ImportStatus(BaseHandler):
    @js
    @is_admin
    def get(self):
        m = Scanner(self.db, self.settings["ScopedSession"])
        status = m.import_status()[1]
        return {"err": "ok", "msg": _(u"成功"), "status": status}


def routes():
    return [
        (r"/api/admin/scan/list", ScanList),
        (r"/api/admin/scan/run", ScanRun),
        (r"/api/admin/scan/status", ScanStatus),
        (r"/api/admin/scan/delete", ScanDelete),
        (r"/api/admin/scan/mark", ScanMark),
        (r"/api/admin/import/run", ImportRun),
        (r"/api/admin/import/status", ImportStatus),
    ]
