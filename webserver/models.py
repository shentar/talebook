#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import datetime
import hashlib
import json
import logging
import os
import time
from gettext import gettext as _

from social_sqlalchemy.storage import JSONType, SQLAlchemyMixin
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import relationship
from tornado import web


def mksalt():
    import random
    import string

    # for python3, just use: crypt.mksalt(crypt.METHOD_SHA512)
    saltchars = string.ascii_letters + string.digits + "./"
    salt = []
    for c in range(32):
        idx = int(random.random() * 10000) % len(saltchars)
        salt.append(saltchars[idx])
    return "".join(salt)


Base = declarative_base()


def bind_session(session):
    def _session(self):
        return session

    Base._session = classmethod(_session)
    SQLAlchemyMixin._session = classmethod(_session)
    logging.info("Bind modles._session()")


def to_dict(self):
    return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}


Base.to_dict = to_dict


class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."
        if isinstance(value, MutableDict):
            return value
        if isinstance(value, dict):
            return MutableDict(value)
        return Mutable.coerce(key, value)

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."
        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."
        dict.__delitem__(self, key)
        self.changed()

    def __getitem__(self, key):
        if not dict.__contains__(self, key):
            return ""
        return dict.__getitem__(self, key)


class Reader(Base, SQLAlchemyMixin):
    OVERSIZE_SHRINK_RATE = 0.8
    SQLITE_MAX_LENGTH = 32 * 1024.0

    RE_USERNAME = r"[a-z][a-z0-9_]*"
    RE_PASSWORD = r'[a-zA-Z0-9!@#$%^&*()_+\-=[\]{};\':",./<>?\|]*'

    __tablename__ = "readers"
    id = Column(Integer, primary_key=True)
    username = Column(String(200))
    password = Column(String(200), default="")
    salt = Column(String(200))
    name = Column(String(100))
    email = Column(String(200))
    avatar = Column(String(200))
    admin = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    permission = Column(String(100), default="")
    create_time = Column(DateTime)
    update_time = Column(DateTime)
    access_time = Column(DateTime)
    extra = Column(MutableDict.as_mutable(JSONType), default={})

    def __str__(self):
        return "<id=%d, username=%s, email=%s>" % (self.id, self.username, self.email)

    def shrink_column_extra(self):
        # check whether the length of `extra` column is out of limit 32KB
        text = json.dumps(self.extra)
        shrink = min(self.OVERSIZE_SHRINK_RATE, self.SQLITE_MAX_LENGTH / len(text))
        if len(text) > self.SQLITE_MAX_LENGTH:
            for k, v in self.extra.items():
                if k.endswith("_history") and isinstance(v, list):
                    new_length = int(len(v) * shrink)
                    self.extra[k] = v[:new_length]

    def save(self):
        self.shrink_column_extra()
        return super().save()

    def init_default_user(self):
        class DefaultUserInfo:
            extra_data = {"username": _(u"默认用户")}
            provider = "qq"
            uid = 123456789

        self.init(DefaultUserInfo())

    def init(self, social_user):
        self.username = self.get_social_username(social_user)
        self.create_time = datetime.datetime.now()
        self.update_time = datetime.datetime.now()
        self.access_time = datetime.datetime.now()
        self.extra = {"kindle_email": ""}
        self.init_avatar(social_user)

    def reset_password(self):
        s = "%s%s%s" % (self.username, self.create_time.strftime("%s"), time.time())
        p = hashlib.md5(s.encode("UTF-8")).hexdigest()[:16]
        self.set_secure_password(p)
        return p

    def get_secure_password(self, raw_password):
        p1 = hashlib.sha256(raw_password.encode("UTF-8")).hexdigest()
        p2 = hashlib.sha256((self.salt + p1).encode("UTF-8")).hexdigest()
        return p2

    def set_secure_password(self, raw_password):
        self.salt = mksalt()
        self.password = self.get_secure_password(raw_password)

    def init_avatar(self, social_user):
        anyone = "http://tva1.sinaimg.cn/default/images/default_avatar_male_50.gif"
        url = social_user.extra_data.get("profile_image_url", anyone)
        self.avatar = url.replace("http://q.qlogo.cn", "//q.qlogo.cn")

        if social_user.provider == "github":
            self.avatar = "https://avatars.githubusercontent.com/u/%s" % social_user.extra_data["id"]

    def get_active_code(self):
        return self.get_secure_password(self.create_time.strftime("%Y-%m-%d %H:%M:%S"))

    def get_social_username(self, si):
        for k in ["username", "login"]:
            if k in si.extra_data:
                return si.extra_data[k]
        return "%s_%s" % (si.provider, si.uid)

    def check_and_update(self, social_user):
        name = self.get_social_username(social_user)
        if self.username != name:
            logging.info("userid[%s] username needs update to [%s]" % (self.id, name))
            self.username = name

    def set_permission(self, operations):
        ALL = "delprsuv"
        if not isinstance(operations, str):
            raise "bug"
        v = list(self.permission)
        for p in operations:
            if p.lower() not in ALL:
                continue
            r = p.upper() if p.islower() else p.lower()
            try:
                v.remove(r)
            except:
                pass
            v.append(p)
        self.permission = "".join(sorted(v))

    def has_permission(self, operation, default=True):
        if operation.upper() in self.permission:
            return False
        if operation.lower() in self.permission:
            return True
        return default

    def can_login(self):
        return self.has_permission("l")

    def can_delete(self, check=False):
        if check and not self.is_active():
            raise web.HTTPError(403, reason=_(u"未激活账号无权删除书籍，请先登录注册邮箱激活账号。"))
        return self.has_permission("d")

    def can_edit(self, check=False):
        if check and not self.is_active():
            raise web.HTTPError(403, reason=_(u"未激活账号无权编辑书籍，请先登录注册邮箱激活账号。"))
        return self.has_permission("e")

    def can_push(self, check=False):
        if check and not self.is_active():
            raise web.HTTPError(403, reason=_(u"未激活账号无权推送书籍，请先登录注册邮箱激活账号。"))
        return self.has_permission("p")

    def can_read(self, check=False):
        if check and not self.is_active():
            raise web.HTTPError(403, reason=_(u"未激活账号无权在线阅读书籍，请先登录注册邮箱激活账号。"))
        return self.has_permission("r")

    def can_save(self, check=False):
        if check and not self.is_active():
            raise web.HTTPError(403, reason=_(u"未激活账号无权下载书籍，请先登录注册邮箱激活账号。"))
        return self.has_permission("s")

    def can_upload(self, check=False):
        if check and not self.is_active():
            raise web.HTTPError(403, reason=_(u"未激活账号无权上传书籍，请先登录注册邮箱激活账号。"))
        return self.has_permission("u")

    def can_view(self):
        return self.has_permission("v")

    def is_active(self):
        return self.active

    def is_admin(self):
        return self.admin


class Message(Base, SQLAlchemyMixin):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    status = Column(String(100))
    unread = Column(Boolean, default=True)
    create_time = Column(DateTime)
    update_time = Column(DateTime)
    data = Column(MutableDict.as_mutable(JSONType), default={})

    reader_id = Column(Integer, ForeignKey("readers.id"))
    reader = relationship(Reader, backref="messages")

    def __init__(self, user_id, status, msg):
        super(Message, self).__init__()
        self.reader_id = user_id
        self.status = status
        self.create_time = datetime.datetime.now()
        self.update_time = datetime.datetime.now()
        self.data = {"message": msg}


class Item(Base, SQLAlchemyMixin):
    __tablename__ = "items"

    book_id = Column(Integer, default=0, primary_key=True)
    count_guest = Column(Integer, default=0, nullable=False)
    count_visit = Column(Integer, default=0, nullable=False)
    count_download = Column(Integer, default=0, nullable=False)
    website = Column(String(255), default="", nullable=False)

    collector_id = Column(Integer, ForeignKey("readers.id"))
    collector = relationship(Reader, backref="items")

    def __init__(self):
        super(Item, self).__init__()
        self.count_guest = 0
        self.count_visit = 0
        self.count_download = 0
        self.collector_id = 1


class IpDownloads(Base, SQLAlchemyMixin):
    __tablename__ = "ipdownloads"
    ip = Column(String(32), default="", nullable=False, primary_key=True)
    starttime = Column(DateTime)
    dcount = Column(Integer, default=0, nullable=False)

    def __init__(self):
        super(IpDownloads, self).__init__()


class KeyValueStore(Base, SQLAlchemyMixin):
    __tablename__ = "access_statis"
    key = Column(String(128), default="", nullable=False, primary_key=True)
    value = Column(String(128), default="", nullable=False)

    def __init__(self):
        super(KeyValueStore, self).__init__()


class ScanFile(Base, SQLAlchemyMixin):
    __tablename__ = "scanfiles"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, default=0)
    import_id = Column(Integer, default=0)

    name = Column(String(512))
    path = Column(String(1024))
    hash = Column(String(512), unique=True)
    status = Column(String(24))

    title = Column(String(100))
    author = Column(String(100))
    publisher = Column(String(100))
    tags = Column(String(100))

    create_time = Column(DateTime)
    update_time = Column(DateTime)
    book_id = Column(Integer, default=0)
    data = Column(MutableDict.as_mutable(JSONType), default={})

    # STATUS
    NEW = "new"
    DROP = "drop"
    READY = "ready"
    EXIST = "exist"
    IMPORTED = "imported"

    def __init__(self, path, hash_value, scan_id):
        super(ScanFile, self).__init__()
        self.name = os.path.basename(path)
        self.path = path
        self.hash = hash_value
        self.scan_id = scan_id
        self.status = self.NEW
        self.create_time = datetime.datetime.now()
        self.update_time = datetime.datetime.now()


def user_syncdb(engine):
    Base.metadata.create_all(engine)
