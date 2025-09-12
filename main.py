import os
import csv
from typing import Dict, List, Optional, Tuple
import pandas as pd
from comfy.nodes import Node
from comfy.utils import register_node, get_full_path
from comfy.connections import SocketType

# 循环模式枚举定义
LOOP_MODES = ["single_pass", "repeat", "infinite"]
# 支持的文件格式
SUPPORTED_FORMATS = ["csv", "xlsx", "xls"]

# 表格数据缓存管理器（避免重复读取文件）
class TableDataCache:
    _cache: Dict[str, Tuple[pd.DataFrame, float]] = {}  # 路径: (数据, 最后修改时间)
    _CACHE_TTL = 300  # 缓存有效期(秒)

    @classmethod
    def get_data(cls, file_path: str) -> Optional[pd.DataFrame]:
        """获取缓存数据，若过期或不存在则重新读取"""
        if not os.path.exists(file_path):
            return None
        
        file_mtime = os.path.getmtime(file_path)
        cache_key = file_path
        
        # 检查缓存是否有效
        if cache_key in cls._cache:
            cached_data, cached_mtime = cls._cache[cache_key]
            if file_mtime == cached_mtime and (file_mtime + cls._CACHE_TTL) > pd.Timestamp.now().timestamp():
                return cached_data.copy()
        
        # 读取新数据并更新缓存
        try:
            if file_path.endswith((".xlsx", ".xls")):
                data = pd.read_excel(file_path, header=0)
            elif file_path.endswith(".csv"):
                data = pd.read_csv(file_path, header=0, encoding_errors="replace")
            else:
                return None
            
            # 清理列名（去除空格和特殊字符）
            data.columns = [str(col).strip().replace(" ", "_").replace(r"[^\w_]", "") for col in data.columns]
            cls._cache[cache_key] = (data, file_mtime)
            return data.copy()
        except Exception:
            return None

# 主循环节点实现
@register_node("TableDataLooper", "Data Handling")
class TableDataLooperNode(Node):
    def __init__(self):
        super().__init__()
        # 循环状态管理
        self.current_row: int = 0
        self.total_rows: int = 0
        self.remaining_repeats: int = 0
        self.table_data: Optional[pd.DataFrame] = None
        self.column_names: List[str] = []
        self.last_file_path: str = ""

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, List]]:
        """定义节点输入参数"""
        return {
            "required": {
                "file_path": ("STRING", {
                    "default": "",
                    "placeholder": "输入文件路径（.csv/.xlsx/.xls）",
                    "multiline": False,
                    "tooltip": "支持绝对路径或相对于ComfyUI根目录的相对路径"
                }),
                "file_format": (SUPPORTED_FORMATS, {
                    "default": "csv",
                    "label": "文件格式",
                    "tooltip": "选择对应的文件格式以确保正确解析"
                }),
                "loop_mode": (LOOP_MODES, {
                    "default": "single_pass",
                    "label": "循环模式",
                    "tooltip": "single_pass:单次循环|repeat:重复指定次数|infinite:无限循环"
                }),
                "repeat_count": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 1000,
                    "step": 1,
                    "tooltip": "仅在repeat模式下生效，指定循环次数"
                }),
                "start_row": ("INT", {
                    "default": 0,
                    "min": 0,
                    "step": 1,
                    "tooltip": "从第N行开始读取（0为第一行）"
                }),
                "refresh_cache": ("BOOLEAN", {
                    "default": False,
                    "label": "强制刷新缓存",
                    "tooltip": "忽略缓存，重新读取文件最新内容"
                })
            },
            "optional": {
                "trigger": ("TRIGGER", {}),  # 外部触发信号
            }
        }

    def get_output_sockets(self) -> Dict[str, SocketType]:
        """动态生成输出端口（根据表格列自动创建）"""
        outputs = {
            "trigger": ("TRIGGER", {}),  # 循环触发输出
            "current_row": ("INT", {
                "tooltip": "当前循环的行号（从0开始）"
            }),
            "total_rows": ("INT", {
                "tooltip": "表格总数据行数"
            }),
            "loop_complete": ("BOOLEAN", {
                "tooltip": "是否完成所有循环（single_pass/repeat模式下）"
            })
        }

        # 动态添加列数据输出端口
        if self.column_names:
            for col in self.column_names:
                # 根据列数据类型自动选择输出类型
                if self.table_data is not None and col in self.table_data.columns:
                    col_dtype = str(self.table_data[col].dtype)
                    if "int" in col_dtype:
                        outputs[col] = ("INT", {"tooltip": f"列[{col}]的整数数据"})
                    elif "float" in col_dtype:
                        outputs[col] = ("FLOAT", {"tooltip": f"列[{col}]的浮点数数据"})
                    else:
                        outputs[col] = ("STRING", {"tooltip": f"列[{col}]的文本数据"})
                else:
                    outputs[col] = ("STRING", {"tooltip": f"列[{col}]的数据"})

        return outputs

    def load_table_data(self, file_path: str, refresh_cache: bool) -> bool:
        """加载表格数据并初始化状态"""
        # 处理路径（支持相对路径）
        full_path = get_full_path(file_path) if file_path else ""
        if not full_path or not os.path.exists(full_path):
            self.table_data = None
            self.column_names = []
            self.total_rows = 0
            return False

        # 缓存刷新判断
        if refresh_cache or full_path != self.last_file_path:
            TableDataCache._cache.pop(full_path, None)  # 清除旧缓存
            self.last_file_path = full_path

        # 获取表格数据
        self.table_data = TableDataCache.get_data(full_path)
        if self.table_data is None:
            self.column_names = []
            self.total_rows = 0
            return False

        # 应用起始行设置
        if self.inputs.get("start_row", 0) > 0:
            self.table_data = self.table_data.iloc[self.inputs["start_row"]:]
        
        # 初始化列名和总行数
        self.column_names = list(self.table_data.columns)
        self.total_rows = len(self.table_data)
        self.current_row = 0  # 重置当前行
        self.remaining_repeats = self.inputs.get("repeat_count", 1)  # 重置重复次数
        return True

    def process(self, inputs: Dict) -> Dict:
        """节点核心处理逻辑"""
        self.inputs = inputs  # 保存输入参数

        # 1. 加载/刷新表格数据
        load_success = self.load_table_data(
            file_path=inputs.get("file_path", ""),
            refresh_cache=inputs.get("refresh_cache", False)
        )
        if not load_success or self.total_rows == 0:
            return {
                "trigger": None,
                "current_row": -1,
                "total_rows": 0,
                "loop_complete": True,
                **{col: "" for col in self.column_names}
            }

        # 2. 处理循环逻辑
        loop_mode = inputs.get("loop_mode", "single_pass")
        output_data = {"loop_complete": False}

        # 判断是否已完成循环
        if loop_mode == "single_pass" and self.current_row >= self.total_rows:
            output_data["loop_complete"] = True
            current_data_row = self.table_data.iloc[-1]  # 输出最后一行数据
        elif loop_mode == "repeat":
            if self.current_row >= self.total_rows:
                self.remaining_repeats -= 1
                self.current_row = 0  # 重置行索引
                if self.remaining_repeats <= 0:
                    output_data["loop_complete"] = True
                    current_data_row = self.table_data.iloc[-1]
                else:
                    current_data_row = self.table_data.iloc[self.current_row]
                    self.current_row += 1
            else:
                current_data_row = self.table_data.iloc[self.current_row]
                self.current_row += 1
        elif loop_mode == "infinite":
            if self.current_row >= self.total_rows:
                self.current_row = 0  # 重置行索引
            current_data_row = self.table_data.iloc[self.current_row]
            self.current_row += 1

        # 3. 准备输出数据
        output_data["current_row"] = self.current_row - 1 if not output_data["loop_complete"] else self.total_rows - 1
        output_data["total_rows"] = self.total_rows
        output_data["trigger"] = output_data["current_row"]  # 触发信号（用行号标识）

        # 4. 添加各列数据输出
        for col in self.column_names:
            if col in current_data_row:
                value = current_data_row[col]
                # 处理空值和特殊类型
                if pd.isna(value):
                    output_data[col] = "" if isinstance(value, str) else 0
                else:
                    # 类型转换（确保与输出端口类型匹配）
                    if "INT" in self.get_output_sockets()[col][0]:
                        output_data[col] = int(value) if pd.api.types.is_numeric_dtype(type(value)) else 0
                    elif "FLOAT" in self.get_output_sockets()[col][0]:
                        output_data[col] = float(value) if pd.api.types.is_numeric_dtype(type(value)) else 0.0
                    else:
                        output_data[col] = str(value)
            else:
                output_data[col] = ""

        return output_data

    @classmethod
    def IS_CHANGED(cls, inputs: Dict) -> float:
        """检测输入变化（用于ComfyUI节点更新机制）"""
        file_path = inputs.get("file_path", "")
        full_path = get_full_path(file_path) if file_path else ""
        
        # 若文件存在，返回文件修改时间；否则返回当前时间（强制更新）
        if os.path.exists(full_path):
            return os.path.getmtime(full_path)
        return pd.Timestamp.now().timestamp()

    def reset(self):
        """重置循环状态"""
        self.current_row = 0
        self.remaining_repeats = self.inputs.get("repeat_count", 1) if self.inputs else 1

# 辅助节点：表格列选择器（用于筛选需要输出的列）
@register_node("TableColumnFilter", "Data Handling")
class TableColumnFilterNode(Node):
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, List]]:
        return {
            "required": {
                "table_data": ("TABLE_DATA", {}),  # 接收表格数据对象
                "selected_columns": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "每行输入一个列名，空则保留所有列",
                    "tooltip": "指定需要保留的列，不区分大小写，空值表示保留所有列"
                })
            }
        }

    @classmethod
    def OUTPUT_TYPES(cls) -> Dict[str, List[SocketType]]:
        return {
            "required": [
                ("TABLE_DATA", {"tooltip": "筛选后的表格数据对象"}),
                ("COLUMN_LIST", {"tooltip": "筛选后的列名列表（字符串数组）"})
            ]
        }

    def process(self, inputs: Dict) -> Dict:
        table_data = inputs.get("table_data")
        selected_cols = [col.strip() for col in inputs.get("selected_columns", "").split("\n") if col.strip()]
        
        if not isinstance(table_data, pd.DataFrame) or table_data.empty:
            return {"TABLE_DATA": pd.DataFrame(), "COLUMN_LIST": []}
        
        # 处理列选择（不区分大小写）
        table_cols_lower = {col.lower(): col for col in table_data.columns}
        if selected_cols:
            valid_cols = [table_cols_lower[col.lower()] for col in selected_cols if col.lower() in table_cols_lower]
            filtered_data = table_data[valid_cols] if valid_cols else table_data
        else:
            filtered_data = table_data.copy()
        
        return {
            "TABLE_DATA": filtered_data,
            "COLUMN_LIST": list(filtered_data.columns)
        }

# 插件安装说明
def install_guide():
    guide = """
    # ComfyUI表格循环读取插件安装指南
    1. 将本文件保存到 ComfyUI/custom_nodes/ 目录下
    2. 安装依赖包：pip install pandas openpyxl xlrd
    3. 重启ComfyUI
    4. 在节点面板的"Data Handling"分类下可找到以下节点：
       - TableDataLooper: 主循环节点（读取文件并循环输出列数据）
       - TableColumnFilter: 列筛选节点（可选，用于筛选需要的列）
    
    # 使用说明
    1. TableDataLooper节点：
       - 输入文件路径（支持绝对路径或相对ComfyUI根目录的路径）
       - 选择文件格式（csv/xlsx/xls）
       - 设置循环模式（单次/重复/无限）
       - 连接输出列到下游节点（如文本节点、图像生成节点等）
       - 触发信号可用于控制循环节奏
    
    2. 数据类型自动适配：
       - 整数列自动输出INT类型
       - 浮点数列自动输出FLOAT类型
       - 其他类型自动输出STRING类型
    
    3. 缓存机制：
       - 默认缓存300秒，避免重复读取大文件
       - 可通过"强制刷新缓存"选项更新文件内容
    """
    print(guide)

# 安装指南打印（首次运行时触发）
if __name__ == "__main__":
    install_guide()
    