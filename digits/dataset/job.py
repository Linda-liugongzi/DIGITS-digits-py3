# Copyright (c) 2014-2017, NVIDIA CORPORATION.  All rights reserved.


from digits.job import Job
from digits.utils import subclass
from flask_babel import lazy_gettext as _

# NOTE: Increment this every time the pickled object changes
PICKLE_VERSION = 1


@subclass
class DatasetJob(Job):
    """
    A Job that creates a dataset
    """

    def __init__(self, **kwargs):
        """
        """
        super(DatasetJob, self).__init__(**kwargs)
        self.pickver_job_dataset = PICKLE_VERSION

    def get_backend(self):
        """
        Return the DB backend used to create this dataset
        """
        raise NotImplementedError(_('Please implement me'))

    def get_entry_count(self, stage):
        """
        Return the number of entries in the DB matching the specified stage
        """
        raise NotImplementedError(_('Please implement me'))

    def get_feature_db_path(self, stage):
        """
        Return the absolute feature DB path for the specified stage
        """
        raise NotImplementedError(_('Please implement me'))

    def get_feature_dims(self):
        """
        Return the shape of the feature N-D array
        """
        raise NotImplementedError(_('Please implement me'))

    def get_label_db_path(self, stage):
        """
        Return the absolute label DB path for the specified stage
        """
        raise NotImplementedError(_('Please implement me'))

    def get_mean_file(self):
        """
        Return the mean file
        """
        raise NotImplementedError(_('Please implement me'))