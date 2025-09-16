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
    RETURN_TYPES = ("STRING","INT","FLOAT","BOOLEAN", "IMAGE","STRING","STRING")
    RETURN_NAMES = ("字符串","整数","浮点数","布尔值","图像","status","show_help")
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
    def __encode(self,obj):
        obj_string = None
        obj_int = None
        obj_float = None
        obj_boolean = None
        obj_image = None
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
            if type(obj) == tuple:
                obj_string = json.dumps(list(obj),ensure_ascii=False)
            if type(obj) in [list,dict]:
                obj_string = json.dumps(obj,ensure_ascii=False)
        except:
            pass
        return obj_string,obj_int,obj_float,obj_boolean,obj_image
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
        script="",
    ):
        show_help=(
        "1. 脚本中可以使用a、b、c、d四个变量，分别对应输入的四个参数,可以是任意类型\n"
        "2. 脚本中返回结果需要赋值给RESULT变量，系统自动根据结果类型转换为相应的数据格式(数组、字典统一转换为字符串,如果是图像,则输出shape的字符串和原始图像)\n"
        "3. 脚本中可以使用print函数，用于打印日志。\n"
        "4. 脚本中可以使用import语句，导入python标准库或第三方库。\n"
        "5. 脚本中可以使用任何python语法。\n"
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
            exec(script,globals(),result_dict)
            result = result_dict.get("RESULT", "")
            result_string,result_int,result_float,result_boolean,result_image = self.__encode(result)
            status = f"所有内部变量为{result_dict}"
            return (result_string,result_int,result_float,result_boolean, result_image, status,show_help)
        except Exception as e:
            status = f"执行失败:{e}"
            return (None,None,None,None,None, status,show_help)

# 注册到ComfyUI
NODE_CLASS_MAPPINGS = {
    "pyScript": PyScript,
}

WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "WEB_DIRECTORY"]
