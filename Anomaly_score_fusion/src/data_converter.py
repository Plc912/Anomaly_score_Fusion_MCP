"""
数据转换器：将各种格式的输入数据转换为统一的时间序列格式
统一格式：List[Dict[str, Any]]，每个元素包含 'time' 和 'value' 键
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import csv
import json
from datetime import datetime


def convert_to_unified_format(
    data: Any,
    timestamp_column: Optional[str] = None,
    value_column: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    将各种格式的数据转换为统一格式
    
    统一格式：List[Dict[str, Any]]
    每个元素包含：
    - 'time': str - 时间戳字符串
    - 'value': float - 数值
    
    支持的输入格式：
    1. CSV文件路径（str）
    2. 字典列表（List[Dict]）- 已包含time和value键
    3. 时间戳和数值列表的元组 ((timestamps, values))
    
    参数:
    - data: 输入数据（文件路径、字典列表或元组）
    - timestamp_column: CSV文件的时间戳列名（如果输入是CSV文件）
    - value_column: CSV文件的数值列名（如果输入是CSV文件）
    
    返回:
    - List[Dict[str, Any]] - 统一格式的时间序列数据
    """
    if isinstance(data, str):
        # 输入是文件路径
        return _convert_from_csv(data, timestamp_column, value_column)
    elif isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict):
            # 输入是字典列表
            return _convert_from_dict_list(data)
        else:
            raise ValueError("不支持的列表格式，列表元素必须是字典")
    elif isinstance(data, tuple) and len(data) == 2:
        # 输入是(timestamps, values)元组
        timestamps, values = data
        return _convert_from_lists(timestamps, values)
    else:
        raise ValueError(f"不支持的数据格式: {type(data)}")


def _convert_from_csv(
    file_path: str,
    timestamp_column: Optional[str] = None,
    value_column: Optional[str] = None
) -> List[Dict[str, Any]]:
    """从CSV文件转换"""
    path = Path(file_path)
    
    # 如果只是文件名，尝试在data文件夹查找
    if not path.is_absolute() and not path.exists():
        base_dir = Path(__file__).parent.parent
        data_dir = base_dir / "data"
        if (data_dir / path.name).exists():
            path = data_dir / path.name
        elif path.name.startswith("data/") or path.name.startswith("@data/"):
            filename = path.name.lstrip("@").replace("data/", "")
            if (data_dir / filename).exists():
                path = data_dir / filename
    
    if not path.exists():
        raise FileNotFoundError(f"文件未找到: {file_path}")
    
    result = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        
        if reader.fieldnames is None:
            raise ValueError("CSV文件没有表头行")
        
        header = list(reader.fieldnames)
        
        # 自动检测列名
        if timestamp_column is None:
            timestamp_column = _detect_column(header, ["timestamp", "time", "date", "datetime", "ts"])
        if value_column is None:
            value_column = _detect_column(header, ["value", "lineid", "line_id", "id", "count", "num"])
        
        if timestamp_column not in header:
            raise ValueError(f"时间戳列 '{timestamp_column}' 未找到。可用列: {header}")
        if value_column not in header:
            raise ValueError(f"数值列 '{value_column}' 未找到。可用列: {header}")
        
        for row in reader:
            time_str = row.get(timestamp_column, "").strip()
            value_str = row.get(value_column, "").strip()
            
            if not time_str or not value_str:
                continue
            
            try:
                value = float(value_str)
                result.append({
                    "time": time_str,
                    "value": value
                })
            except (ValueError, TypeError):
                continue
    
    if not result:
        raise ValueError("CSV文件中没有有效数据")
    
    return result


def _convert_from_dict_list(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从字典列表转换（验证格式）"""
    result = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"列表元素必须是字典，但得到: {type(item)}")
        
        if "time" not in item or "value" not in item:
            raise ValueError(f"字典必须包含 'time' 和 'value' 键，但得到: {list(item.keys())}")
        
        try:
            value = float(item["value"])
            result.append({
                "time": str(item["time"]),
                "value": value
            })
        except (ValueError, TypeError) as e:
            raise ValueError(f"无法将 'value' 转换为浮点数: {item.get('value')}") from e
    
    return result


def _convert_from_lists(timestamps: List[str], values: List[float]) -> List[Dict[str, Any]]:
    """从时间戳和数值列表转换"""
    if len(timestamps) != len(values):
        raise ValueError(f"时间戳列表和数值列表长度不匹配: {len(timestamps)} vs {len(values)}")
    
    return [
        {"time": str(ts), "value": float(val)}
        for ts, val in zip(timestamps, values)
    ]


def _detect_column(header: List[str], candidates: List[str]) -> str:
    """检测列名"""
    header_lower = [h.lower() for h in header]
    
    # 精确匹配
    for candidate in candidates:
        if candidate.lower() in header_lower:
            idx = header_lower.index(candidate.lower())
            return header[idx]
    
    # 部分匹配
    for candidate in candidates:
        for col in header:
            if candidate.lower() in col.lower():
                return col
    
    # 如果没找到，返回第一列或最后一列
    return header[0] if candidates[0] in ["timestamp", "time", "date"] else header[-1]


def save_unified_data(
    data: List[Dict[str, Any]],
    output_path: Optional[str] = None,
    filename: Optional[str] = None
) -> str:
    """
    保存统一格式的数据到models文件夹
    
    参数:
    - data: 统一格式的时间序列数据
    - output_path: 输出文件路径（可选）
    - filename: 文件名（可选，如果不提供output_path则使用）
    
    返回:
    - str - 保存的文件路径
    """
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / "models"
    models_dir.mkdir(exist_ok=True)
    
    if output_path:
        path = Path(output_path)
        if not path.is_absolute():
            path = models_dir / path
    elif filename:
        path = models_dir / filename
    else:
        # 自动生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = models_dir / f"timeseries_{timestamp}.json"
    
    # 确保文件扩展名是.json
    if path.suffix != ".json":
        path = path.with_suffix(".json")
    
    # 保存为JSON格式
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return str(path)
