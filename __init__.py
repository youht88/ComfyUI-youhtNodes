import json
import torch
import base64
class ContainsAnyDict(dict):
    def __contains__(self, key):
        return True

class PyScript:
    """
    使用OpenRouter进行文生图的节点
    """
    CATEGORY = "youht"
    FUNCTION = "generate"
    RETURN_TYPES = ("STRING","INT","FLOAT","BOOLEAN", "IMAGE","AUDIO","STRING","STRING")
    RETURN_NAMES = ("字符串","整数","浮点数","布尔值","图像","音频","status","show_help")
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
                "d": ("*",{"forceInput":False}),
                "arg_name": ("STRING",{"multiline": False,"default":"xyz"}),
            }
        }
    @classmethod
    def VALIDATE_INPUTS(s, input_types):
        return True
    def __encode(self,obj):
        obj_string = None
        obj_int = None
        obj_float = None
        obj_boolean = None
        obj_image = None
        obj_audio = None
        try:
            if type(obj) == str:
                obj_string = obj
                try:
                    obj_int = int(obj)
                except:
                    pass
                try:
                    obj_float = float(obj)
                except:
                    pass
                if obj.lower() in ["true","yes"]:
                    obj_boolean = True
                if obj.lower() in ["false","no"]:
                    obj_boolean = False
            if type(obj) == int:
                obj_int = obj
                try:
                    obj_string = str(obj_int)
                except:
                    pass
                try:
                    obj_float = float(obj)
                except:
                    pass
                try:
                    obj_boolean = bool(obj)
                except:
                    pass
            if type(obj) == float:
                obj_float = obj
                try:
                    obj_string = str(obj_float)
                except:
                    pass
                try:
                    obj_int = int(obj_float)
                except:
                    pass
                try:
                    obj_boolean = bool(obj)
                except:
                    pass
            if type(obj) == bool:
                obj_boolean = obj
                obj_string = "true" if obj else "false"
                obj_int = 1 if obj else 0 
                obj_float = 1.0 if obj else 0.0
            if type(obj) == torch.Tensor:
                shape = obj.shape
                if len(shape)==3:
                    obj_image = obj.unsqueeze(0)
                if len(shape)==4:
                    obj_image = obj
                if obj_image:
                    obj_string = json.dumps(obj_image.shape,ensure_ascii=False)
            if type(obj) == dict:
                if "waveform" in obj and "sample_rate" in obj and type(obj["waveform"]) == torch.Tensor and type(obj["sample_rate"])==int:
                    obj_audio = obj
                    obj_int = obj["sample_rate"]
                    obj_string = json.dumps(obj["waveform"].shape,ensure_ascii=False)
                else:
                    obj_string = json.dumps(obj,ensure_ascii=False) 
            if type(obj) == tuple:
                obj_string = json.dumps(list(obj),ensure_ascii=False)
            if type(obj) == list:
                obj_string = json.dumps(obj,ensure_ascii=False)
        except:
            pass
        return obj_string,obj_int,obj_float,obj_boolean,obj_image,obj_audio
    def __decode(self,obj):
        if type(obj) == str:
            try:
                return json.loads(obj)
            except:
                pass
        return obj
    def generate(
        self,
        a="",
        b="",
        c="",
        d="",
        arg_name="",
        script="",
        **kwargs
    ):
        show_help=(
        "1. 脚本中可以使用a、b、c、d四个变量，分别对应输入的四个参数,可以是任意类型\n"
        "2. 脚本中返回结果需要赋值给RESULT变量，系统自动根据结果类型转换为相应的数据格式(数组、字典统一转换为字符串)\n"
        "3. 脚本中可以使用print函数，用于打印日志。\n"
        "4. 脚本中可以使用import语句，导入python标准库或第三方库。\n"
        "5. 脚本中可以使用任何python语法。\n"
        "6. 如果RESULT是3维或4维torch.Tensor对象，则被认为是图像。输出shape的字符串和原始图像\n"
        "7. 如果RESULT变量是一个包含waveform和sample_rate两个键的字典，且waveform为torch.Tensor类型，sample_rate为int类型,则被认为是音频。输出shape的字符串和音频\n"
        "8. 如果没有结果可能script脚本执行出错了，可以查看stats错误信息。status默认情况下是所有变量值"
        "9. 可以使用arg_name指定要增加或删除的参数名，然后在script脚本中使用这个参数。增加参数时如果arg_name是预制的参数则忽略，删除时如果arg_name是预制的参数或不存在则忽略"
        "示例:\n"
        "name=a\n"
        "age=b\n"
        "x =  f\"我是{name},我今年{age}岁\"\n"
        "RESULT=x\n"
        )
        try:
            """动态执行脚本"""
            result_dict={
                "a":self.__decode(a),
                "b":self.__decode(b),
                "c":self.__decode(c),
                "d":self.__decode(d)
            } 
            result_dict.update({key:self.__decode(kwargs[key]) for  key in kwargs})  
            exec(script,globals(),result_dict)
            result = result_dict.get("RESULT", "")
            result_string,result_int,result_float,result_boolean,result_image,result_audio = self.__encode(result)
            status = f"所有内部变量为{result_dict}"
            return (result_string,result_int,result_float,result_boolean, result_image, result_audio,status,show_help)
        except Exception as e:
            status = f"执行失败:{e}"
            return (None,None,None,None,None,None, status,show_help)

# 注册到ComfyUI
NODE_CLASS_MAPPINGS = {
    "pyScript": PyScript,
}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "WEB_DIRECTORY"]
