#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import datetime
import hashlib
import logging
import re
import time
from gettext import gettext as _

import tornado.escape
from tornado import web

from webserver import loader
from webserver.handlers.base import BaseHandler, auth, js
from webserver.models import Message, Reader, KeyValueStore
from webserver.utils import check_email
from webserver.version import VERSION

CONF = loader.get_settings()
COOKIE_REDIRECT = "login_redirect"


class Done(BaseHandler):
    def update_userinfo(self):
        if int(CONF.get("auto_login", 0)):
            return

        user_id = self.get_secure_cookie("user_id")
        user = self.session.query(Reader).get(int(user_id)) if user_id else None
        if not user:
            return
        socials = user.social_auth.all()
        if not socials:
            logging.warning("the socials is None: %d" % user.id)
            self.session.query(Reader).filter(Reader.id == user.id).delete()
            return

        si = socials[0]
        if not user.create_time:
            logging.info("init new user %s, info=%s" % (user.username, si))
            user.init(si)
            user.permission = "U"

        if not user.create_time:
            self.session.query(Reader).filter(Reader.id == user.id).delete()
            user = None
        else:
            user.check_and_update(si)
        return user

    def get(self):
        user = self.update_userinfo()
        if not user:
            self.log_out()
            raise web.HTTPError(403, log_message=_(u"注册异常"))

        if not user.can_login():
            raise web.HTTPError(403, log_message=_(u"无权登录"))
        self.login_user(user)
        url = self.get_secure_cookie(COOKIE_REDIRECT)
        self.clear_cookie(COOKIE_REDIRECT)
        if not url:
            url = "/"
        self.redirect(url)

    def log_out(self):
        self.set_secure_cookie("user_id", "")
        self.set_secure_cookie("admin_id", "")


class UserUpdate(BaseHandler):
    @js
    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        user = self.current_user
        nickname = data.get("nickname", "")
        if nickname:
            nickname = nickname.strip()
            if len(nickname) > 0:
                if len(nickname) < 3:
                    return {"err": "params.nickname.invald", "msg": _(u"昵称无效")}
                user.name = nickname

        p0 = data.get("password0", "").strip()
        p1 = data.get("password1", "").strip()
        p2 = data.get("password2", "").strip()
        if len(p0) > 0:
            if user.get_secure_password(p0) != user.password:
                return {"err": "params.password.error", "msg": _(u"密码错误")}
            if p1 != p2 or len(p1) < 8 or len(p1) > 20 or not re.match(Reader.RE_PASSWORD, p1):
                return {"err": "params.password.invalid", "msg": _(u"密码无效")}
            user.set_secure_password(p1)

        ke = data.get("kindle_email", "").strip()
        if len(ke) > 0:
            if not check_email(ke):
                return {"err": "params.email.invalid", "msg": _(u"Kindle地址无效")}
            user.extra["kindle_email"] = ke

        try:
            user.save()
            self.add_msg("success", _("Settings saved."))
            return {"err": "ok"}
        except:
            self.session.rollback()
            return {"err": "db.error", "msg": _(u"数据库操作异常，请重试")}


class SignUp(BaseHandler):
    def check_active_code(self, username, code):
        user = self.session.query(Reader).filter(Reader.username == username).first()
        if not user or code != user.get_active_code():
            raise web.HTTPError(403, log_message=_(u"激活码无效"))
        user.active = True
        try:
            user.save()
        except Exception as e:
            self.session.rollback()
            logging.warning("some err: %r" % e)
        return self.redirect("/active/success")

    def send_active_email(self, user):
        code = user.get_active_code()
        link = "%s/api/active/%s/%s" % (self.site_url, user.username, code)
        args = {
            "site_title": CONF["site_title"],
            "username": user.username,
            "active_link": link,
        }
        mail_subject = CONF["SIGNUP_MAIL_TITLE"] % args
        mail_to = user.email
        mail_from = CONF["smtp_username"]
        mail_body = CONF["SIGNUP_MAIL_CONTENT"] % args
        self.mail(mail_from, mail_to, mail_subject, mail_body)

    @js
    def post(self):
        if not CONF["ALLOW_REGISTER"]:
            return {"err": "params.invalid", "msg": _(u"当前系统设置为不允许注册新用户，请联系管理员。")}

        email = self.get_argument("email", "").strip()
        nickname = self.get_argument("nickname", "").strip()
        username = self.get_argument("username", "").strip().lower()
        password = self.get_argument("password", "").strip()
        if not nickname or not username or not password:
            return {"err": "params.invalid", "msg": _(u"用户名或密码无效")}

        if not check_email(email):
            return {"err": "params.email.invalid", "msg": _(u"Email无效")}
        if len(username) < 5 or len(username) > 20 or not re.match(Reader.RE_USERNAME, username):
            return {"err": "params.username.invalid", "msg": _(u"用户名无效")}
        if len(password) < 8 or len(password) > 20 or not re.match(Reader.RE_PASSWORD, password):
            return {"err": "params.password.invalid", "msg": _(u"密码无效")}

        user = self.session.query(Reader).filter(Reader.username == username).first()
        if user:
            return {"err": "params.username.exist", "msg": _(u"用户名已被使用")}
        user = self.session.query(Reader).filter(Reader.email == email).first()
        if user:
            return {"err": "params.email.exist", "msg": _(u"邮箱地址已被使用")}
        user = Reader()
        user.username = username
        user.name = nickname
        user.email = email
        user.avatar = CONF["avatar_service"] + "/avatar/" + hashlib.md5(email.encode("UTF-8")).hexdigest()
        user.create_time = datetime.datetime.now()
        user.update_time = datetime.datetime.now()
        user.access_time = datetime.datetime.now()
        user.active = False
        user.extra = {"kindle_email": ""}
        user.set_secure_password(password)
        logging.info("create a new user: %s, %s, %s" % (user.name, user.username, str(user.create_time)))
        # 默认不允许上传。
        user.permission = "U"
        try:
            user.save()
        except:
            import traceback
            self.session.rollback()
            logging.error(traceback.format_exc())
            return {"err": "db.error", "msg": _(u"系统异常，请重试或更换注册信息")}
        self.send_active_email(user)
        return {"err": "ok"}


class UserSendActive(SignUp):
    @js
    @auth
    def get(self):
        self.send_active_email(self.current_user)
        return {"err": "ok"}

    def post(self):
        return self.get()


class UserActive(SignUp):
    def get(self, username, code):
        return self.check_active_code(username, code)

    def post(self, username, code):
        return self.check_active_code(username, code)


class SignIn(BaseHandler):
    @js
    def post(self):
        username = self.get_argument("username", "").strip().lower()
        password = self.get_argument("password", "").strip()
        if not username:
            return {"err": "params.invalid", "msg": _(u"用户名为空")}
        if not password:
            return {"err": "params.invalid", "msg": _(u"不允许空密码")}

        user = self.session.query(Reader).filter(Reader.username == username).first()
        if not user:
            return {"err": "params.invalid", "msg": _(u"用户%s未注册" % username)}

        if not user.salt:
            return {"err": "params.invalid", "msg": _(u"%s用户不是本地注册用户，请使用正确的登录平台登录。" % username)}

        if not user:
            return {"err": "params.no_user", "msg": _(u"无此用户")}

        if user.get_secure_password(password) != user.password:
            return {"err": "params.invalid", "msg": _(u"用户名或密码错误")}

        if not user.can_login():
            return {"err": "permission", "msg": _(u"无权登录")}

        logging.debug("PERM = %s", user.permission)

        self.login_user(user)

        return {"err": "ok", "msg": "ok"}


class UserReset(BaseHandler):
    @js
    def post(self):
        email = self.get_argument("email", "").strip().lower()
        username = self.get_argument("username", "").strip().lower()
        if not username or not email:
            return {"err": "params.invalid", "msg": _(u"用户名或邮箱错误")}
        user = self.session.query(Reader).filter(Reader.username == username, Reader.email == email).first()
        if not user:
            return {"err": "params.no_user", "msg": _(u"无此用户")}
        p = user.reset_password()

        # send notice email
        args = {
            "site_title": CONF["site_title"],
            "username": user.username,
            "password": p,
        }
        mail_subject = CONF["RESET_MAIL_TITLE"] % args
        mail_to = user.email
        mail_from = CONF["smtp_username"]
        mail_body = CONF["RESET_MAIL_CONTENT"] % args
        self.mail(mail_from, mail_to, mail_subject, mail_body)

        # do save into db
        try:
            user.save()
            self.add_msg("success", _("你刚刚重置了密码"))
            return {"err": "ok"}
        except:
            self.session.rollback()
            return {"err": "db.error", "msg": _(u"系统繁忙")}


class SignOut(BaseHandler):
    @js
    @auth
    def get(self):
        logging.info("user logout: %s" % str(self.get_secure_cookie("user_id")))
        self.set_secure_cookie("user_id", "")
        self.set_secure_cookie("admin_id", "")
        return {"err": "ok", "msg": _(u"你已成功退出登录。")}


class UserMessages(BaseHandler):
    @js
    def get(self):
        user = self.current_user
        rsp = {
            "err": "ok",
            "messages": [],
        }

        if user:
            for msg in user.messages:
                if not msg.unread:
                    continue
                m = {
                    "id": msg.id,
                    "title": msg.title,
                    "status": msg.status,
                    "create_time": msg.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "data": msg.data,
                }
                rsp["messages"].append(m)
        return rsp

    @js
    @auth
    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        if "id" not in data:
            return {"err": "params.invalid", "msg": _(u"ID错误")}
        msg = self.session.query(Message).filter(Message.id == data["id"]).first()
        if not msg:
            return {"err": "params.not_found", "msg": _(u"查无此ID")}

        msg.unread = False
        msg.update_time = datetime.datetime.now()
        try:
            msg.save()
        except Exception as e:
            self.session.rollback()
            logging.warning("some err: %r" % e)
        return {"err": "ok"}


class UserInfo(BaseHandler):
    def get_sys_info(self):
        from sqlalchemy import func

        db = self.db
        last_week = datetime.datetime.now() - datetime.timedelta(days=7)
        count_all_users = self.session.query(func.count(Reader.id)).scalar()
        count_hot_users = self.session.query(func.count(Reader.id)).filter(Reader.access_time > last_week).scalar()
        v = "0"
        visits = self.session.query(KeyValueStore.value).filter(KeyValueStore.key == "visit")
        if visits.count() > 0:
            v = visits[0].value
        d = "0"
        downloads = self.session.query(KeyValueStore.value).filter(KeyValueStore.key == "download")
        if downloads.count() > 0:
            d = downloads[0].value
        return {
            "books": db.count(),
            "readcount": int(v),
            "downloadcount": int(d),
            "tags": len(db.all_tags()),
            "authors": len(db.all_authors()),
            "publishers": len(db.all_publishers()),
            "series": len(db.all_series()),
            "mtime": db.last_modified().strftime("%Y-%m-%d"),
            "users": count_all_users,
            "active": count_hot_users,
            "version": VERSION,
            "title": CONF["site_title"],
            "socials": CONF["SOCIALS"],
            "friends": CONF["FRIENDS"],
            "footer": CONF["FOOTER"],
            "allow": {
                "register": CONF["ALLOW_REGISTER"],
                "download": CONF["ALLOW_GUEST_DOWNLOAD"],
                "push": CONF["ALLOW_GUEST_PUSH"],
                "read": CONF["ALLOW_GUEST_READ"],
            },
        }

    def get_user_info(self, detail):
        user = self.current_user
        d = {
            "avatar": "https://tva1.sinaimg.cn/default/images/default_avatar_male_50.gif",
            "is_login": False,
            "is_admin": False,
            "nickname": "",
            "email": "",
            "kindle_email": "",
            "extra": {},
            "pems": "",
        }

        if not user or user.create_time is None:
            return d

        d.update(
            {
                "is_login": True,
                "is_admin": user.is_admin(),
                "is_active": user.is_active(),
                "nickname": user.name or "",
                "username": user.username,
                "email": user.email,
                "extra": {},
                "create_time": user.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "pems": user.permission,
            }
        )
        if user.avatar:
            gravatar_url = "https://www.gravatar.com"
            d["avatar"] = user.avatar.replace("http://", "https://").replace(gravatar_url, CONF["avatar_service"])
        if user.extra:
            d["kindle_email"] = user.extra.get("kindle_email", "")
            if detail:
                for k, v in user.extra.items():
                    if not k.endswith("_history") or not v:
                        continue

                    hbs = {}
                    hb_list = []
                    # 只取前60本。
                    books = self.db.get_data_as_dict(ids=v[:100])
                    for b in books:
                        hb = {
                            "id": b["id"],
                            "lm": b["last_modified"].strftime("%s"),
                            "title": b["title"]
                        }
                        hbs[hb["id"]] = hb
                    for idx in v:
                        if idx in hbs:
                            hb_list.append(hbs[idx])
                    d["extra"][k] = hb_list[:60]
        return d

    @js
    def get(self):
        if CONF.get("installed", None) is False:
            return {"err": "not_installed"}
        user = self.current_user
        # 超过30s，则刷新一次用户最新访问时间。
        if user and user.access_time and user.access_time.timestamp() < time.time() - 30:
            user.access_time = datetime.datetime.now()
            try:
                user.save()
            except Exception as e:
                self.session.rollback()
                logging.warning("some err: %r" % e)

        detail = self.get_argument("detail", "")
        rsp = {
            "err": "ok",
            "cdn": self.cdn_url,
            "sys": self.get_sys_info() if not detail else {},
            "user": self.get_user_info(detail),
        }
        return rsp


class ClearUserHis(BaseHandler):
    @js
    def delete(self):
        if not self.current_user:
            return {
                "err": "error",
                "msg": _(u"请登录后操作"),
                "to": "/login?from=/user/history"
            }
        if not self.current_user.is_active():
            return {
                "err": "error",
                "msg": _(u"请先激活账号后操作"),
            }

        user = self.current_user
        action = self.get_argument("action", None)
        if action:
            action += "_history"
        else:
            return {
                "err": "error",
                "msg": _(u"清理目标为空")
            }

        if user.extra and action and action in user.extra:
            del user.extra[action]
            try:
                user.save()
            except Exception as e:
                self.session.rollback()
                logging.warning("some err: %r" % e)

        return {
            "err": "ok",
            "msg": _(u"清理历史记录成功")
        }


class Welcome(BaseHandler):
    def should_be_invited(self):
        pass

    @js
    def get(self):
        if not self.need_invited():
            return {"err": "free", "msg": _(u"无需访问码")}
        if self.invited_code_is_ok():
            return {"err": "free", "msg": _(u"已输入访问码")}
        return {"err": "ok", "msg": CONF["INVITE_MESSAGE"]}

    @js
    def post(self):
        code = self.get_argument("invite_code", None)
        if not code or code != CONF["INVITE_CODE"]:
            return {"err": "params.invalid", "msg": _(u"访问码无效")}
        self.mark_invited()
        return {"err": "ok", "msg": "ok"}


def routes():
    return [
        (r"/api/welcome", Welcome),
        (r"/api/user/info", UserInfo),
        (r"/api/user/messages", UserMessages),
        (r"/api/user/sign_in", SignIn),
        (r"/api/user/sign_up", SignUp),
        (r"/api/user/sign_out", SignOut),
        (r"/api/user/update", UserUpdate),
        (r"/api/user/reset", UserReset),
        (r"/api/user/clearhis", ClearUserHis),
        (r"/api/user/active/send", UserSendActive),
        (r"/api/active/(.*)/(.*)", UserActive),
        (r"/api/done/", Done),
    ]
