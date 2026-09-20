import os
import torch
import torch.nn as nn


def load_yolo_model(weights_path):
    from models.common import Conv

    ckpt = torch.load(weights_path, map_location=torch.device("cpu"), weights_only=False)
    model = ckpt.get("ema") or ckpt.get("model")
    model = model.float().fuse().eval()

    for m in model.modules():
        if type(m) in [nn.Hardswish, nn.LeakyReLU, nn.ReLU, nn.ReLU6, nn.SiLU]:
            m.inplace = True
        elif type(m) is Conv:
            m._non_persistent_buffers_set = set()

    return model