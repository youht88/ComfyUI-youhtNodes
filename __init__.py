import os
import io
import base64
import traceback
import random
from typing import List, Tuple, Optional
import json

import numpy as np
import torch
from PIL import Image

from langchain_openai  import ChatOpenAI

class ContainsAnyDict(dict):
    def __contains__(self, key):
        return True

class PyScript:
    """
    使用OpenRouter进行文生图的节点
    """
    CATEGORY = "youht"
    FUNCTION = "generate"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("result", "status")
    OUTPUT_NODE = False
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "script": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "a": ("*",{"forceInput":False}),
                "b": ("*",{"forceInput":False}),
                "c": ("*",{"forceInput":False}),
                "d": ("*",{"forceInput":False})
            }
        }
    @classmethod
    def VALIDATE_INPUTS(s, input_types):
        return True

    def generate(
        self,
        a="",
        b="",
        c="",
        d="",
        script="",
    ):
        """动态执行脚本"""
        try:
            try:
                a=json.loads(str(a))
            except:
                pass
            try:
                b=json.loads(str(b))
            except:
                pass
            try:
                c=json.loads(str(c))
            except:
                pass
            try:
                d=json.loads(str(d))
            except:
                pass
            result_dict={"a":a,
                         "b":b,
                         "c":c,
                         "d":d}
            exec(script,globals(),result_dict)
            result = result_dict.get("RESULT", "")
            if type(result) != str:
                result = json.dumps(result,ensure_ascii=False)
            status = f"所有内部变量为{result_dict}"
            return (result, status)
        except Exception as e:
            status = f"执行失败:{e}"
            return (None, status)

# 注册到ComfyUI
NODE_CLASS_MAPPINGS = {
    "pyScript": PyScript,
}

WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "WEB_DIRECTORY"]
