# Copyright (c) 2016, NVIDIA CORPORATION.  All rights reserved.


import os

from digits import utils
from digits.utils import subclass
from flask_wtf import FlaskForm
from wtforms import validators
from flask_babel import lazy_gettext as _


@subclass
class DatasetForm(FlaskForm):
    """
    A form used to create a Sunnybrook dataset
    """

    def validate_folder_path(form, field):
        if not field.data:
            pass
        else:
            # make sure the filesystem path exists
            if not os.path.exists(field.data) or not os.path.isdir(field.data):
                raise validators.ValidationError(
                    'Folder does not exist or is not reachable')
            else:
                return True

    story_folder = utils.forms.StringField(
        _('Story folder'),
        validators=[
            validators.DataRequired(),
            validate_folder_path,
            ],
        tooltip=_("Specify the path to a folder of stories - filenames are "
                  "expected to have this format: qa[1-N]*[train|test].txt")
        )

    task_id = utils.forms.SelectField(
        _('Task ID'),
        choices=[
            ('all', _('All')),
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5'),
            ('6', '6'),
            ('7', '7'),
            ('8', '8'),
            ('9', '9'),
            ('10', '10'),
            ('11', '11'),
            ('12', '12'),
            ('13', '13'),
            ('14', '14'),
            ('15', '15'),
            ('16', '16'),
            ('17', '17'),
            ('18', '18'),
            ('19', '19'),
            ('20', '20'),
            ],
        default='1',
        tooltip=_("Select a task to train on or 'all' to train a joint model "
                  "on all tasks.")
        )

    pct_val = utils.forms.IntegerField(
        _('for validation'),
        default=10,
        validators=[
            validators.NumberRange(min=0, max=100)
            ],
        tooltip=_("You can choose to set apart a certain percentage of images "
                  "from the training images for the validation set.")
        )


@subclass
class InferenceForm(FlaskForm):

    def validate_file_path(form, field):
        if not field.data:
            pass
        else:
            # make sure the filesystem path exists
            if not os.path.exists(field.data) and not os.path.isdir(field.data):
                raise validators.ValidationError(
                    'File does not exist or is not reachable')
            else:
                return True
    """
    A form used to perform inference on a text classification dataset
    """
    snippet = utils.forms.TextAreaField(
        _('Story/Question'),
        tooltip=_("Write all sentences there and end with a question")
    )
