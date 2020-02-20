# -*- coding: utf-8 -*-
from .webapp import db, app
from sqlalchemy import and_
import hashlib


class User(db.Model):
    DEFAULT_PERMISSIONS = '0'
    DEFAULT_STATUS = 'T'
    DEFAULT_LAST_LOGIN= "无"
    DEFAULT_MODIFY_TIME = "无"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(320), unique=True)
    password_hash = db.Column(db.String(128), nullable=True)
    permissions = db.Column(db.String(128), default=DEFAULT_PERMISSIONS)
    status = db.Column(db.String(128), default=DEFAULT_STATUS)
    last_login = db.Column(db.String(128), default = DEFAULT_LAST_LOGIN)
    create_time = db.Column(db.String(128),nullable=False)
    modify_time = db.Column(db.String(128),default= DEFAULT_MODIFY_TIME)
    __tablename__ = 'users'

    def __repr__(self):
        return '<User %r>' % self.username

    @staticmethod
    def get_all_users():
        return User.query.filter().order_by(User.id).all()


    @staticmethod
    def get_filter_users(condition):
        return User.query.filter(
                                condition
                                ).order_by(User.id).all()

    @staticmethod
    def inspect_username(username):
        if User.query.filter(User.username == username).first():
            return False
        else:
            return True
    @staticmethod
    def have_user():
        u = User.query.filter().all()
        return False if u else True


# 登录检验
def valid_login(username, password):
    pwb_hash = hashlib.md5(password.encode()).hexdigest()
    user = User.query.filter(and_(User.username == username, User.password_hash == pwb_hash)).first()
    if user:
        return True
    else:
        return False


# 注册检验
def valid_regist(username):
    user = User.query.filter(User.username == username).first()
    if user:
        return False
    else:
        return True


# 两次密码验证
def verify_pwd(pwd, repeat_pwd):
    first_pwd = hashlib.md5(pwd.encode()).hexdigest()
    repeat_pwd = hashlib.md5(repeat_pwd.encode()).hexdigest()
    if first_pwd == repeat_pwd:
        return False
    return True


@app.before_first_request
def create_db():
    db.create_all()
