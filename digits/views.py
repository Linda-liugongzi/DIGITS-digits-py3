# Copyright (c) 2014-2017, NVIDIA CORPORATION.  All rights reserved.
# -*- coding: utf-8 -*-
import datetime
import glob
import hashlib
import json
import platform
import traceback
import os
import time


import flask
from flask import request, flash, session, redirect, render_template, url_for
from flask_socketio import join_room, leave_room
from werkzeug import HTTP_STATUS_CODES
import werkzeug.exceptions

from .config import config_value
from .webapp import app, socketio, scheduler, db
import digits
from digits import dataset, extensions, model, utils, pretrained_model
from digits.log import logger
from digits.utils.routing import request_wants_json
from flask_babel import lazy_gettext as _
from .models import valid_login, valid_regist, User, verify_pwd

blueprint = flask.Blueprint(__name__, __name__)


@blueprint.route('/model.json', methods=['GET'])
def model_json():
    """
    Returns JSON when requested:
        {
            datasets: [{id, name, status},...],
            models: [{id, name, status},...]
        }
    """
    running_models = get_job_list(model.ModelJob, True)
    completed_models = get_job_list(model.ModelJob, False)

    data = {
        'models': [j.json_dict()
                   for j in running_models + completed_models],
    }
    return flask.jsonify(data)


@blueprint.route('/index.json', methods=['GET'])
@blueprint.route('/home', methods=['GET'])
@utils.auth.requires_login
def home(tab=2):
    """
    DIGITS home page
    Returns information about each job on the server

    Returns JSON when requested:
        {
            datasets: [{id, name, status},...],
            models: [{id, name, status},...]
        }
    """
    running_datasets = get_job_list(dataset.DatasetJob, True)
    completed_datasets = get_job_list(dataset.DatasetJob, False)
    running_models = get_job_list(model.ModelJob, True)
    completed_models = get_job_list(model.ModelJob, False)

    if request_wants_json():
        data = {
            'version': digits.__version__,
            'jobs_dir': config_value('jobs_dir'),
            'datasets': [j.json_dict()
                         for j in running_datasets + completed_datasets],
            'models': [j.json_dict()
                       for j in running_models + completed_models],
        }
        if config_value('server_name'):
            data['server_name'] = config_value('server_name')
        return flask.jsonify(data)
    else:
        new_dataset_options = {
            'Images': {
                'image-classification': {
                    'title': _('Classification'),
                    'url': flask.url_for(
                        'digits.dataset.images.classification.views.new'),
                },
                'image-other': {
                    'title': _('Other'),
                    'url': flask.url_for(
                        'digits.dataset.images.generic.views.new'),
                },
            },
            'Sounds': {
                'image-classification': {
                    'title': _('Classification'),
                    'url': flask.url_for(
                        'digits.dataset.images.classification.views.sound_new'),
                }
            }
        }

        new_model_options = {
            'Images': {
                'image-classification': {
                    'title': _('Classification'),
                    'url': flask.url_for(
                        'digits.model.images.classification.views.new'),
                },
                'image-other': {
                    'title': _('Other'),
                    'url': flask.url_for(
                        'digits.model.images.generic.views.new'),
                },
            },
        }

        load_model_options = {
            'Images': {
                'pretrained-model': {
                    'title': _('Upload Pretrained Model'),
                    'id': 'uploadPretrainedModel',
                    'url': flask.url_for(
                        'digits.pretrained_model.views.new'),
                },
                # 'access-model-store': {
                #     'title': _('Retrieve from Model Store'),
                #     'id': 'retrieveModelStore',
                #     'url': flask.url_for('digits.store.views.store'),
                # }
            },
        }

        # add dataset options for known dataset extensions
        data_extensions = extensions.data.get_extensions()
        for extension in data_extensions:
            ext_category = extension.get_category()
            ext_title = extension.get_title()
            ext_id = extension.get_id()
            if ext_category not in new_dataset_options:
                new_dataset_options[ext_category] = {}
            new_dataset_options[ext_category][ext_id] = {
                'title': ext_title,
                'url': flask.url_for(
                    'digits.dataset.generic.views.new',
                    extension_id=ext_id),
            }
            if ext_category not in new_model_options:
                new_model_options[ext_category] = {}
            new_model_options[ext_category][ext_id] = {
                'title': ext_title,
                'url': flask.url_for(
                    'digits.model.images.generic.views.new',
                    extension_id=ext_id),
            }

        return flask.render_template(
            'home.html',
            tab=tab,
            new_dataset_options=new_dataset_options,
            running_datasets=running_datasets,
            completed_datasets=completed_datasets,
            new_model_options=new_model_options,
            running_models=running_models,
            completed_models=completed_models,
            load_model_options=load_model_options,
            total_gpu_count=len(scheduler.resources['gpus']),
            remaining_gpu_count=sum(r.remaining()
                                    for r in scheduler.resources['gpus']),
        )


def json_dict(job, model_output_fields):
    d = {
        'id': job.id(),
        'name': job.name(),
        'group': job.group,
        'status': job.status_of_tasks().name,
        'status_css': job.status_of_tasks().css,
        'submitted': job.status_history[0][1],
        'elapsed': job.runtime_of_tasks(),
    }

    if 'train_db_task' in dir(job):
        d.update({
            'backend': job.train_db_task().backend,
        })

    if 'train_task' in dir(job):
        d.update({
            'framework': job.train_task().get_framework_id(),
        })
        for prefix, outputs in (('train', job.train_task().train_outputs),
                                ('val', job.train_task().val_outputs)):
            for key in outputs.keys():
                data = outputs[key].data
                if len(data) > 0:
                    key = '%s (%s) ' % (key, prefix)
                    model_output_fields.add(key + 'last')
                    model_output_fields.add(key + 'min')
                    model_output_fields.add(key + 'max')
                    d.update({key + 'last': data[-1]})
                    d.update({key + 'min': min(data)})
                    d.update({key + 'max': max(data)})

        if (job.train_task().combined_graph_data() and
                'columns' in job.train_task().combined_graph_data()):
            d.update({
                'sparkline': job.train_task().combined_graph_data()['columns'][0][1:],
            })

    if 'get_progress' in dir(job):
        d.update({
            'progress': int(round(100 * job.get_progress())),
        })

    if hasattr(job, 'dataset_id'):
        d.update({
            'dataset_id': job.dataset_id,
        })

    if hasattr(job, 'extension_id'):
        d.update({
            'extension': job.extension_id,
        })
    else:
        if hasattr(job, 'dataset_id'):
            ds = scheduler.get_job(job.dataset_id)
            if ds and hasattr(ds, 'extension_id'):
                d.update({
                    'extension': ds.extension_id,
                })

    if isinstance(job, dataset.DatasetJob):
        d.update({'type': 'dataset'})

    if isinstance(job, model.ModelJob):
        d.update({'type': 'model'})

    if isinstance(job, pretrained_model.PretrainedModelJob):
        model_output_fields.add("has_labels")
        model_output_fields.add("username")
        d.update({
            'type': 'pretrained_model',
            'framework': job.framework,
            'username': job.username,
            'has_labels': job.has_labels_file()
        })
    return d


@blueprint.route('/completed_jobs.json', methods=['GET'])
def completed_jobs():
    """
    Returns JSON
        {
            datasets: [{id, name, group, status, status_css, submitted, elapsed, badge}],
            models:   [{id, name, group, status, status_css, submitted, elapsed, badge}],
        }
    """
    completed_datasets = get_job_list(dataset.DatasetJob, False)
    completed_models = get_job_list(model.ModelJob, False)
    running_datasets = get_job_list(dataset.DatasetJob, True)
    running_models = get_job_list(model.ModelJob, True)
    pretrained_models = get_job_list(pretrained_model.PretrainedModelJob, False)

    model_output_fields = set()
    data = {
        'running': [json_dict(j, model_output_fields) for j in running_datasets + running_models],
        'datasets': [json_dict(j, model_output_fields) for j in completed_datasets],
        'models': [json_dict(j, model_output_fields) for j in completed_models],
        'pretrained_models': [json_dict(j, model_output_fields) for j in pretrained_models],
        'model_output_fields': sorted(list(model_output_fields)),
    }

    return flask.jsonify(data)


@blueprint.route('/jobs/<job_id>/table_data.json', methods=['GET'])
def job_table_data(job_id):
    """
    Get the job data for the front page tables
    """
    job = scheduler.get_job(job_id)
    if job is None:
        raise werkzeug.exceptions.NotFound(_('Job not found'))

    model_output_fields = set()
    return flask.jsonify({'job': json_dict(job, model_output_fields)})


def get_job_list(cls, running):
    return sorted(
        [j for j in scheduler.jobs.values() if isinstance(j, cls) and j.status.is_running() == running],
        key=lambda j: j.status_history[0][1],
        reverse=True,
    )


@blueprint.route('/group', methods=['GET', 'POST'])
@utils.auth.requires_login
def group():
    """
    Assign the group for the listed jobs
    """
    not_found = 0
    forbidden = 0
    group_name = utils.routing.get_request_arg('group_name').strip()
    job_ids = flask.request.form.getlist('job_ids[]')
    error = []
    for job_id in job_ids:
        try:
            job = scheduler.get_job(job_id)
            if job is None:
                logger.warning('Job %s not found for group assignment.' % job_id)
                not_found += 1
                continue

            if not utils.auth.has_permission(job, 'edit'):
                logger.warning('Group assignment not permitted for job %s' % job_id)
                forbidden += 1
                continue

            job.group = group_name

            # update form data so updated name gets used when cloning job
            if hasattr(job, 'form_data'):
                job.form_data['form.group_name.data'] = job.group

            job.emit_attribute_changed('group', job.group)

        except Exception as e:
            error.append(e)
            pass

    for job_id in job_ids:
        job = scheduler.get_job(job_id)

    error = []
    if not_found:
        error.append('%d job%s not found.' % (not_found, '' if not_found == 1 else 's'))

    if forbidden:
        error.append('%d job%s not permitted to be regrouped.' % (forbidden, '' if forbidden == 1 else 's'))

    if len(error) > 0:
        error = ' '.join(error)
        raise werkzeug.exceptions.BadRequest(error)

    return 'Jobs regrouped.'


@blueprint.route('/login', methods=['GET', 'POST'])
@blueprint.route('/', methods=['GET', 'POST'])
def login():
    """
    user login
    """
    if session.get('username'):
        return redirect(url_for('digits.views.home'))
    error = None
    if request.method == 'POST':
        if valid_login(request.form['username'], request.form['password']):
            flash("成功登录！")
            session['username'] = request.form.get('username')
            old_user = User.query.filter(User.username == session['username']).first()
            old_user.last_login= str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            db.session.commit()
            return redirect(url_for('digits.views.home'))
        else:
            error = '错误的用户名或密码！'
    have_user = User.have_user()
    return render_template('login.html', error=error, have_user=have_user)


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    """
    user register
    """
    error = None
    if request.method == 'POST':
        if verify_pwd(request.form['password'], request.form['repeat_pwd']):
            error = '两次密码不相同！'
        elif valid_regist(request.form['username']):
            password = hashlib.md5(request.form['password'].encode()).hexdigest()
            last_login = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            user = User(username=request.form['username'], password_hash=password, status="T",last_login = last_login)
            db.session.add(user)
            db.session.commit()

            flash("成功注册！")
            session['username'] = request.form['username']
            return redirect(url_for('digits.views.home'))
        else:
            error = '该用户名已被注册！'

    return render_template('register.html', error=error)


@blueprint.route('/logout', methods=['GET', 'POST'])
def logout():
    """
    Unset the username cookie
    """
    response = flask.make_response(flask.redirect(url_for('digits.views.login')))
    session.pop('username', None)
    return response


# Jobs routes

@blueprint.route('/jobs/<job_id>', methods=['GET'])
@utils.auth.requires_login
def show_job(job_id):
    """
    Redirects to the appropriate /datasets/ or /models/ page
    """
    job = scheduler.get_job(job_id)
    if job is None:
        raise werkzeug.exceptions.NotFound(_('Job not found'))

    if isinstance(job, dataset.DatasetJob):
        return flask.redirect(flask.url_for('digits.dataset.views.show', job_id=job_id))
    if isinstance(job, model.ModelJob):
        return flask.redirect(flask.url_for('digits.model.views.show', job_id=job_id))
    if isinstance(job, pretrained_model.PretrainedModelJob):
        return flask.redirect(flask.url_for('digits.pretrained_model.views.show', job_id=job_id))
    else:
        raise werkzeug.exceptions.BadRequest(_('Invalid job type'))


@blueprint.route('/jobs/<job_id>', methods=['PUT'])
@utils.auth.requires_login(redirect=False)
def edit_job(job_id):
    """
    Edit a job's name and/or notes
    """
    job = scheduler.get_job(job_id)
    if job is None:
        raise werkzeug.exceptions.NotFound(_('Job not found'))

    if not utils.auth.has_permission(job, 'edit'):
        raise werkzeug.exceptions.Forbidden()

    # Edit name
    if 'job_name' in flask.request.form:
        name = flask.request.form['job_name'].strip()
        if not name:
            raise werkzeug.exceptions.BadRequest(_('name cannot be blank'))
        job._name = name
        job.emit_attribute_changed('name', job.name())
        # update form data so updated name gets used when cloning job
        if 'form.dataset_name.data' in job.form_data:
            job.form_data['form.dataset_name.data'] = name
        elif 'form.model_name.data' in job.form_data:
            job.form_data['form.model_name.data'] = name
        else:
            # we are utterly confused
            raise werkzeug.exceptions.BadRequest('Unable to edit job type %s' % job.job_type())
        logger.info('Set name to "%s".' % job.name(), job_id=job.id())

    # Edit notes
    if 'job_notes' in flask.request.form:
        notes = flask.request.form['job_notes'].strip()
        if not notes:
            notes = None
        job._notes = notes
        logger.info('Updated notes.', job_id=job.id())

    return '%s updated.' % job.job_type()


@blueprint.route('/datasets/<job_id>/status', methods=['GET'])
@blueprint.route('/models/<job_id>/status', methods=['GET'])
@blueprint.route('/jobs/<job_id>/status', methods=['GET'])
@utils.auth.requires_login
def job_status(job_id):
    """
    Returns a JSON objecting representing the status of a job
    """
    job = scheduler.get_job(job_id)
    result = {}
    if job is None:
        result['error'] = _('Job not found.')
    else:
        result['error'] = None
        result['status'] = job.status.name
        result['name'] = job.name()
        result['type'] = job.job_type()
    return json.dumps(result)


@blueprint.route('/pretrained_models/<job_id>', methods=['DELETE'])
@blueprint.route('/datasets/<job_id>', methods=['DELETE'])
@blueprint.route('/models/<job_id>', methods=['DELETE'])
@blueprint.route('/jobs/<job_id>', methods=['DELETE'])
@utils.auth.requires_login(redirect=False)
def delete_job(job_id):
    """
    Deletes a job
    """
    job = scheduler.get_job(job_id)
    if job is None:
        raise werkzeug.exceptions.NotFound(_('Job not found'))

    if not utils.auth.has_permission(job, 'delete'):
        raise werkzeug.exceptions.Forbidden()

    try:
        if scheduler.delete_job(job_id):
            return 'Job deleted.'
        else:
            raise werkzeug.exceptions.Forbidden('Job not deleted')
    except utils.errors.DeleteError as e:
        raise werkzeug.exceptions.Forbidden(str(e))


@blueprint.route('/jobs', methods=['DELETE'])
@utils.auth.requires_login(redirect=False)
def delete_jobs():
    """
    Deletes a list of jobs
    """
    not_found = 0
    forbidden = 0
    failed = 0
    job_ids = flask.request.form.getlist('job_ids[]')
    error = []
    for job_id in job_ids:

        try:
            job = scheduler.get_job(job_id)
            if job is None:
                not_found += 1
                continue

            if not utils.auth.has_permission(job, 'delete'):
                forbidden += 1
                continue

            if not scheduler.delete_job(job_id):
                failed += 1
                continue
        except Exception as e:
            error.append(str(e))
            pass

    if not_found:
        error.append('%d job%s not found.' % (not_found, '' if not_found == 1 else 's'))

    if forbidden:
        error.append('%d job%s not permitted to be deleted.' % (forbidden, '' if forbidden == 1 else 's'))

    if failed:
        error.append('%d job%s failed to delete.' % (failed, '' if failed == 1 else 's'))

    if len(error) > 0:
        error = ' '.join(error)
        raise werkzeug.exceptions.BadRequest(error)

    return 'Jobs deleted.'


@blueprint.route('/abort_jobs', methods=['POST'])
@utils.auth.requires_login(redirect=False)
def abort_jobs():
    """
    Aborts a list of jobs
    """
    not_found = 0
    forbidden = 0
    failed = 0
    errors = []
    job_ids = flask.request.form.getlist('job_ids[]')
    for job_id in job_ids:

        try:
            job = scheduler.get_job(job_id)
            if job is None:
                not_found += 1
                continue

            if not utils.auth.has_permission(job, 'abort'):
                forbidden += 1
                continue

            if not scheduler.abort_job(job_id):
                failed += 1
                continue

        except Exception as e:
            errors.append(e)
            pass

    if not_found:
        errors.append('%d job%s not found.' % (not_found, '' if not_found == 1 else 's'))

    if forbidden:
        errors.append('%d job%s not permitted to be aborted.' % (forbidden, '' if forbidden == 1 else 's'))

    if failed:
        errors.append('%d job%s failed to abort.' % (failed, '' if failed == 1 else 's'))

    if len(errors) > 0:
        raise werkzeug.exceptions.BadRequest(' '.join(errors))

    return 'Jobs aborted.'


@blueprint.route('/datasets/<job_id>/abort', methods=['POST'])
@blueprint.route('/models/<job_id>/abort', methods=['POST'])
@blueprint.route('/jobs/<job_id>/abort', methods=['POST'])
@utils.auth.requires_login(redirect=False)
def abort_job(job_id):
    """
    Aborts a running job
    """
    job = scheduler.get_job(job_id)
    if job is None:
        raise werkzeug.exceptions.NotFound(_('Job not found'))

    if scheduler.abort_job(job_id):
        return 'Job aborted.'
    else:
        raise werkzeug.exceptions.Forbidden(_('Job not aborted'))


@blueprint.route('/clone/<clone>', methods=['POST', 'GET'])
@utils.auth.requires_login
def clone_job(clone):
    """
    Clones a job with the id <clone>, populating the creation page with data saved in <clone>
    """

    # <clone> is the job_id to clone

    job = scheduler.get_job(clone)
    if job is None:
        raise werkzeug.exceptions.NotFound(_('Job not found'))

    if isinstance(job, dataset.GenericDatasetJob):
        return flask.redirect(
            flask.url_for('digits.dataset.generic.views.new', extension_id=job.extension_id) + '?clone=' + clone)
    if isinstance(job, dataset.ImageClassificationDatasetJob):
        return flask.redirect(flask.url_for('digits.dataset.images.classification.views.new') + '?clone=' + clone)
    if isinstance(job, dataset.GenericImageDatasetJob):
        return flask.redirect(flask.url_for('digits.dataset.images.generic.views.new') + '?clone=' + clone)
    if isinstance(job, model.ImageClassificationModelJob):
        return flask.redirect(flask.url_for('digits.model.images.classification.views.new') + '?clone=' + clone)
    if isinstance(job, model.GenericImageModelJob):
        return flask.redirect(flask.url_for('digits.model.images.generic.views.new') + '?clone=' + clone)
    else:
        raise werkzeug.exceptions.BadRequest(_('Invalid job type'))

# Error handling

'''
@app.errorhandler(Exception)
def handle_error(e):
    """
    Handle errors, formatting them as JSON if requested
    """
    error_type = type(e).__name__
    message = str(e)
    trace = None
    description = None
    status_code = 500
    if isinstance(e, werkzeug.exceptions.HTTPException):
        status_code = e.code
        description = e.description
    if app.debug:
        trace = traceback.format_exc()

    if request_wants_json():
        details = {
            'message': message,
            'type': error_type,
        }
        if description is not None:
            details['description'] = description
        if trace is not None:
            details['trace'] = trace.split('\n')
        return flask.jsonify({'error': details}), status_code
    else:
        message = message.replace('\\n', '<br />')
        if isinstance(e, digits.frameworks.errors.NetworkVisualizationError):
            trace = message
            message = ''
        return flask.render_template('error.html',
                                     title=error_type,
                                     message=message,
                                     description=description,
                                     trace=trace,
                                     ), status_code
'''
# Register this handler for all error codes
# Necessary for flask<=0.10.1
#for code in HTTP_STATUS_CODES:
#    if code not in [301]:
#        app.register_error_handler(code, handle_error)

# File serving


@blueprint.route('/files/<path:path>', methods=['GET'])
def serve_file(path):
    """
    Return a file in the jobs directory

    If you install the nginx.site file, nginx will serve files instead
    and this path will never be used
    """
    jobs_dir = config_value('jobs_dir')
    return flask.send_from_directory(jobs_dir, path)

# Path Completion


@blueprint.route('/autocomplete/path', methods=['GET'])
def path_autocomplete():
    """
    Return a list of paths matching the specified preamble

    """
    path = flask.request.args.get('query', '')

    if not os.path.isabs(path):
        # Only allow absolute paths by prepending forward slash
        path = os.path.sep + path

    suggestions = [os.path.abspath(p) for p in glob.glob(path + "*")]
    if platform.system() == 'Windows':
        # on windows, convert backslashes with forward slashes
        suggestions = [p.replace('\\', '/') for p in suggestions]

    result = {
        "suggestions": sorted(suggestions)
    }

    return json.dumps(result)


@blueprint.route('/extension-static/<extension_type>/<extension_id>/<path:filename>')
def extension_static(extension_type, extension_id, filename):
    """
    Returns static files from an extension's static directory.
    '/extension-static/view/image-segmentation/js/app.js'
    would send the file
    'digits/extensions/view/imageSegmentation/static/js/app.js'
    """

    extension = None
    if (extension_type == 'view'):
        extension = extensions.view.get_extension(extension_id)
    elif (extension_type == 'data'):
        extension = extensions.data.get_extension(extension_id)

    if extension is None:
        raise ValueError(_("Unknown extension '%(extension_id)s'", extension_id=extension_id))

    digits_root = os.path.dirname(os.path.abspath(digits.__file__))
    rootdir = os.path.join(digits_root, *['extensions', 'view', extension.get_dirname(), 'static'])
    return flask.send_from_directory(rootdir, filename)

# SocketIO functions

# /home


@socketio.on('connect', namespace='/home')
def on_connect_home():
    """
    Somebody connected to the homepage
    """
    pass


@socketio.on('disconnect', namespace='/home')
def on_disconnect_home():
    """
    Somebody disconnected from the homepage
    """
    pass

# /jobs


@socketio.on('connect', namespace='/jobs')
def on_connect_jobs():
    """
    Somebody connected to a jobs page
    """
    pass


@socketio.on('disconnect', namespace='/jobs')
def on_disconnect_jobs():
    """
    Somebody disconnected from a jobs page
    """
    pass


@socketio.on('join', namespace='/jobs')
def on_join_jobs(data):
    """
    Somebody joined a room
    """
    room = data['room']
    join_room(room)
    flask.session['room'] = room


@socketio.on('leave', namespace='/jobs')
def on_leave_jobs():
    """
    Somebody left a room
    """
    if 'room' in flask.session:
        room = flask.session['room']
        del flask.session['room']
        # print('>>> Somebody left room %s' % room)
        leave_room(room)