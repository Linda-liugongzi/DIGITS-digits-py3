# Copyright (c) 2016-2017, NVIDIA CORPORATION.  All rights reserved.

import os
from digits.utils import subclass, override
from digits.status import Status
from digits.pretrained_model.tasks import UploadPretrainedModelTask
from flask_babel import lazy_gettext as _


@subclass
class TensorflowUploadTask(UploadPretrainedModelTask):

    def __init__(self, **kwargs):
        super(TensorflowUploadTask, self).__init__(**kwargs)

    @override
    def name(self):
        return _('Upload Pretrained Tensorflow Model')

    @override
    def get_model_def_path(self):
        """
        Get path to model definition
        """
        return os.path.join(self.job_dir, "network.py")

    @override
    def get_weights_path(self):
        """
        Get path to model weights
        """
        return os.path.join(self.job_dir, "snapshot.ckpt")

    @override
    def __setstate__(self, state):
        super(TensorflowUploadTask, self).__setstate__(state)

    @override
    def run(self, resources):

        self.move_file(self.weights_path[0], "snapshot.ckpt.data-00000-of-00001")
        self.move_file(self.weights_path[1], "snapshot.ckpt.index")
        self.move_file(self.weights_path[2], "snapshot.ckpt.meta")
        self.move_file(self.model_def_path, "network.py")

        if self.labels_path is not None:
            self.move_file(self.labels_path, "labels.txt")

        self.status = Status.DONE
