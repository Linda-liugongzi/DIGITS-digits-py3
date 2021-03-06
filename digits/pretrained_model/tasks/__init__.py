# Copyright (c) 2016-2017, NVIDIA CORPORATION.  All rights reserved.


from .upload_pretrained import UploadPretrainedModelTask
from .caffe_upload import CaffeUploadTask
from .torch_upload import TorchUploadTask
from .tensorflow_upload import TensorflowUploadTask
from .tfpb_upload import TfpbUploadTask
from .hub_upload import HubUploadTask

__all__ = [
    'UploadPretrainedModelTask',
    'CaffeUploadTask',
    'TorchUploadTask',
    'TensorflowUploadTask',
    'TfpbUploadTask',
    'HubUploadTask'
]
