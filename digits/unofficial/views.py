# -*- coding: utf-8 -*-
from __future__ import absolute_import
from operator import and_


import os
import flask
from flask import request, flash, session, redirect, render_template, url_for
import hashlib
import datetime

from digits.config import config_value
from digits.webapp import app, socketio, scheduler, db
import digits
from digits import dataset, extensions, model, utils, pretrained_model
from digits.log import logger
from digits.utils.routing import request_wants_json
from digits.models import valid_login, valid_regist, User, verify_pwd

blueprint = flask.Blueprint(__name__, __name__)


@blueprint.route('/task_manager', methods=['GET'])
@utils.auth.requires_login
def task_manager():
    running_datasets = get_job_list(dataset.DatasetJob, True)
    completed_datasets = get_job_list(dataset.DatasetJob, False)
    running_models = get_job_list(model.ModelJob, True)
    completed_models = get_job_list(model.ModelJob, False)

    job_data = {
        'datasets': [j.json_dict(True)
                     for j in running_datasets + completed_datasets],
        'models': [j.json_dict(True)
                   for j in running_models + completed_models],
    }

    return render_template('unofficial/task_manager.html', job_data=job_data, scheduler=scheduler, enumerate=enumerate)


def get_job_list(cls, running):
    return sorted(
        [j for j in scheduler.jobs.values() if isinstance(j, cls) and j.status.is_running() == running],
        key=lambda j: j.status_history[0][1],
        reverse=True,
    )


@blueprint.route('/system_manager', methods=['GET'])
@utils.auth.requires_login
def system_manager():
    users = User.get_all_users()
    running_datasets = get_job_list(dataset.DatasetJob, True)
    completed_datasets = get_job_list(dataset.DatasetJob, False)
    running_models = get_job_list(model.ModelJob, True)
    completed_models = get_job_list(model.ModelJob, False)

    job_data = {
        'datasets': [j.json_dict(True)
                     for j in running_datasets + completed_datasets],
        'models': [j.json_dict(True)
                   for j in running_models + completed_models],
    }
    return render_template('unofficial/user_manager.html',
                           users=users,
                           job_data=job_data,
                           scheduler=scheduler,
                           enumerate=enumerate,
                           int=int)


@blueprint.route('/digits.log', methods=['GET'])
def system_log():
    path = config_value('log_file')['filename'].split('/')
    return flask.send_from_directory(directory='/'.join(path[:-1]), filename=path[-1])


@blueprint.route('/index_manager', methods=['GET'])
@utils.auth.requires_login
def index_manager():
    completed_datasets = get_job_list(dataset.DatasetJob, False)
    datasets = [j.json_dict(True) for j in completed_datasets]
    dataset_job_ids = [data_set['id'] for data_set in datasets]
    return render_template('unofficial/index_manager.html',
                           ids=dataset_job_ids,
                           scheduler=scheduler,
                           datasets=datasets,
                           hasattr=hasattr)


@blueprint.route('/data_manager', methods=['GET', 'POST'])
@utils.auth.requires_login
def data_manager():
    if request.method == 'POST':
        # print(request.form.get('image_folder'))
        # image_file = request.files['image_file']
        # image_folder = request.files
        # file_path = request.form.get('file_path')
        # if not file_path:
        #     file_path = '/data/upload_file/'
        # if not os.path.exists(file_path):
        #     os.makedirs(file_path)
        # if image_file:
        #     image_file.save(file_path, image_file.filename)
        # print(image_folder)
        # if image_folder:
        # for file in image_folder:
        #     print(file)

        # print(request.form.get('upload_file_path'))
        return redirect(url_for('digits.unofficial.views.data_manager'))
    return render_template('unofficial/data_manager.html')


@blueprint.route('/mark_manager/<index>', methods=['GET'])
@utils.auth.requires_login
def mark_manager(index):
    if index == 'image':
        return render_template('unofficial/gds-image.html')
    elif index == 'voice':
        return render_template('unofficial/gds-voice.html')
    elif index == 'video':
        return render_template('unofficial/gds-video.html')
    return render_template('unofficial/mark_manager.html')


@blueprint.route('/visualization_manager', methods=['GET'])
@utils.auth.requires_login
def visualization_manager():
    completed_models = get_job_list(model.ModelJob, False)
    models = [j.json_dict(True) for j in completed_models]
    return render_template('unofficial/visualization_manager.html',
                           models=models,
                           scheduler=scheduler,
                           enumerate=enumerate)


@blueprint.route('/add_user', methods=['POST'])
@utils.auth.requires_login
def add_user():
    username = request.form.get('username')
    if User.inspect_username(username):
        permissions = request.form.get('permissions')
        password = hashlib.md5(request.form.get('upassword').encode()).hexdigest()
        create_time = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        user = User(username=username, password_hash=password, permissions=permissions, status="T",create_time = create_time)
        db.session.add(user)
        db.session.commit()
    else:
        flash("用户名已存在！请重新输入用户名。")
    return redirect(url_for('digits.unofficial.views.system_manager'))


@blueprint.route('/modify_user', methods=['POST'])
def modify_user():
    username = request.form.get('modUser_name')
    old_user = User.query.filter(User.username == username).first()
    permissions = request.form.get('modUser_perm')
    status = request.form.get('is_jinyong')
    modify_time = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    old_user.permissions = permissions
    old_user.status = status
    old_user.modify_time = modify_time
    db.session.commit()
    return redirect(url_for('digits.unofficial.views.system_manager'))


@blueprint.route("/del_user",methods = ['POST'])
def del_user():
    username = request.form.get('delname')
    old_user = User.query.filter(User.username == username).first()
    db.session.delete(old_user)
    db.session.commit()
    return redirect(url_for('digits.unofficial.views.system_manager'))


@blueprint.route("/select_user",methods = ['POST'])
def select_user():
    running_datasets = get_job_list(dataset.DatasetJob, True)
    completed_datasets = get_job_list(dataset.DatasetJob, False)
    running_models = get_job_list(model.ModelJob, True)
    completed_models = get_job_list(model.ModelJob, False)
    job_data = {
        'datasets': [j.json_dict(True)
                     for j in running_datasets + completed_datasets],
        'models': [j.json_dict(True)
                   for j in running_models + completed_models],
    }
    ##多个过滤
    condition = (User.id > 0)
    user_name = request.form.get("seluser_name")
    if user_name:
        condition = and_(condition, User.username.like(str(user_name)+'%'))
    user_perm = request.form.get("seluser_perm")
    if user_perm in ["0","1","2","3"]:
        condition = and_(condition, User.permissions == user_perm)
    user_status = request.form.get("seluser_status")
    if user_status in ["T","F"]:
        condition = and_(condition, User.status == user_status)
    users = User.get_filter_users(condition)
    return render_template('unofficial/user_manager.html',
                               users=users,
                               job_data=job_data,
                               scheduler=scheduler,
                               enumerate=enumerate,
                               int=int)




