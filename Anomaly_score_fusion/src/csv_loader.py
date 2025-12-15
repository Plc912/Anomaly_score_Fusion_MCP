from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import csv
import pandas as pd


def _resolve_csv_path(path: str) -> Path:
    """
    解析CSV文件路径，支持多种路径格式
    支持格式：
    - 绝对路径
    - 相对路径（如 "data/file.csv"）
    - 仅文件名（如 "file.csv"）会自动在data文件夹查找
    - @data/ 前缀（如 "@data/file.csv" 或 "data/file.csv"）
    - 模糊匹配：如果找不到精确匹配，会尝试在data文件夹中查找包含该名称的文件
    """
    # 处理 @data/ 前缀，去掉 @ 符号
    normalized_path = path.lstrip('@').strip()
    
    candidate = Path(normalized_path).expanduser()
    search_order = []
    
    cwd = Path.cwd()
    base_dir = Path(__file__).parent.parent  # 项目根目录
    data_dir = base_dir / "data"
    
    if candidate.is_absolute():
        search_order.append(candidate)
    else:
        # 优先查找data文件夹（因为用户说所有数据都在data文件夹下）
        # 1. 如果路径以 data/ 开头（包括 @data/），提取文件名并在data文件夹查找
        if normalized_path.startswith('data/'):
            filename = Path(normalized_path).name
            search_order.append((data_dir / filename).resolve())
            search_order.append((cwd / "data" / filename).resolve())
        # 2. 如果只是文件名（没有路径分隔符），优先在data文件夹查找
        elif candidate.parent == Path(".") or str(candidate.parent) == ".":
            filename = candidate.name
            search_order.append((data_dir / filename).resolve())
            search_order.append((cwd / "data" / filename).resolve())
        
        # 3. 尝试相对路径的其他位置（包括原始路径和data/路径）
        search_order.append((cwd / candidate).resolve())
        search_order.append((base_dir / candidate).resolve())
        
        # 如果原始路径包含data/，也尝试直接路径
        if normalized_path.startswith('data/'):
            search_order.append((base_dir / normalized_path).resolve())
            search_order.append((cwd / normalized_path).resolve())
    
    # 查找存在的文件
    for option in search_order:
        if option.exists() and option.is_file():
            return option
    
    # 如果精确匹配失败，尝试模糊匹配（在data文件夹中查找包含该名称的文件）
    if not candidate.is_absolute():
        search_dirs = [data_dir, cwd / "data"]
        filename_lower = candidate.name.lower()
        
        for search_dir in search_dirs:
            if search_dir.exists() and search_dir.is_dir():
                # 精确匹配（忽略大小写）
                for file_path in search_dir.glob("*.csv"):
                    if file_path.name.lower() == filename_lower:
                        return file_path.resolve()
                
                # 部分匹配：文件名包含搜索关键词
                search_keywords = filename_lower.replace('.csv', '').replace('_', ' ').split()
                for file_path in search_dir.glob("*.csv"):
                    file_lower = file_path.name.lower()
                    # 检查是否所有关键词都在文件名中
                    if all(keyword in file_lower for keyword in search_keywords if len(keyword) > 2):
                        return file_path.resolve()
                
                # 最后尝试：文件名开头匹配
                for file_path in search_dir.glob("*.csv"):
                    if file_path.name.lower().startswith(filename_lower.replace('.csv', '')):
                        return file_path.resolve()
    
    # 如果都不存在，返回最后一个候选路径（用于错误提示）
    return candidate if candidate.is_absolute() else search_order[-1] if search_order else candidate


def load_timeseries_from_csv(
    path: str,
    timestamp_column: str = "timestamp",
    value_column: str = "value",
    limit: Optional[int] = None,
    dropna: bool = True,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """
    从CSV文件加载时间序列数据
    
    参数:
    - path: str - CSV文件路径（支持相对路径、绝对路径，或仅文件名）
    - timestamp_column: str - 时间戳列名，默认 "timestamp"
    - value_column: str - 数值列名，默认 "value"
    - limit: Optional[int] - 仅返回前N条记录（用于快速测试）
    - dropna: bool - 是否跳过空值行，默认 True
    - encoding: str - 文件编码，默认 "utf-8"
    
    返回:
    - Dict包含: timestamps (List[str]), values (List[float]), path (str), total_rows (int)
    """
    target = _resolve_csv_path(path)
    
    if not target.exists():
        raise FileNotFoundError(
            f"CSV文件未找到: {target}\n"
            f"尝试的路径包括:\n"
            f"  - {target}\n"
            f"  - {Path.cwd() / path}\n"
            f"  - {Path(__file__).parent.parent / 'data' / Path(path).name}"
        )
    
    timestamps = []
    values = []
    total_rows = 0
    
    try:
        with target.open("r", encoding=encoding, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            
            if reader.fieldnames is None:
                raise ValueError("CSV文件没有表头行")
            
            header = reader.fieldnames
            
            # 检查必需的列
            if timestamp_column not in header:
                raise ValueError(
                    f"时间戳列 '{timestamp_column}' 未在CSV文件中找到。"
                    f"可用列: {list(header)}"
                )
            
            if value_column not in header:
                raise ValueError(
                    f"数值列 '{value_column}' 未在CSV文件中找到。"
                    f"可用列: {list(header)}"
                )
            
            # 读取数据
            for row in reader:
                total_rows += 1
                
                timestamp = row.get(timestamp_column)
                value_str = row.get(value_column)
                
                # 处理空值
                if dropna and (not timestamp or not value_str or timestamp.strip() == "" or value_str.strip() == ""):
                    continue
                
                try:
                    value = float(value_str)
                    timestamps.append(timestamp.strip() if timestamp else "")
                    values.append(value)
                    
                    # 限制返回数量
                    if limit is not None and len(values) >= limit:
                        break
                        
                except (ValueError, TypeError) as e:
                    if not dropna:
                        raise ValueError(
                            f"第 {total_rows} 行的数值列 '{value_column}' 无法转换为浮点数: {value_str!r}"
                        ) from e
    
    except Exception as e:
        raise ValueError(f"读取CSV文件失败: {str(e)}") from e
    
    if len(values) == 0:
        raise ValueError(f"CSV文件中没有有效数据（共读取 {total_rows} 行）")
    
    return {
        "status": "ok",
        "path": str(target),
        "timestamp_column": timestamp_column,
        "value_column": value_column,
        "total_rows": total_rows,
        "returned_rows": len(values),
        "timestamps": timestamps,
        "values": values
    }


def list_data_files() -> List[Dict[str, Any]]:
    """
    列出data文件夹下的所有CSV文件
    
    返回:
    - List[Dict] 包含文件信息：name, path, columns
    """
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    cwd = Path.cwd()
    
    files = []
    search_dirs = [data_dir, cwd / "data"]
    
    for search_dir in search_dirs:
        if search_dir.exists() and search_dir.is_dir():
            for file_path in search_dir.glob("*.csv"):
                try:
                    # 读取文件头获取列名
                    with file_path.open("r", encoding="utf-8", newline="") as f:
                        reader = csv.DictReader(f)
                        columns = list(reader.fieldnames) if reader.fieldnames else []
                    
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path),
                        "columns": columns,
                        "size": file_path.stat().st_size
                    })
                except Exception:
                    # 如果读取失败，至少返回文件名
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path),
                        "columns": [],
                        "size": file_path.stat().st_size if file_path.exists() else 0
                    })
    
    # 去重（按文件名）
    seen = set()
    unique_files = []
    for f in files:
        if f["name"] not in seen:
            seen.add(f["name"])
            unique_files.append(f)
    
    return unique_files


def auto_detect_columns(header: List[str]) -> Tuple[str, str]:
    """
    自动检测CSV文件的timestamp和value列
    
    参数:
    - header: CSV文件的列名列表
    
    返回:
    - (timestamp_column, value_column) 元组
    """
    header_lower = [col.lower() for col in header]
    
    # 检测时间戳列（优先级顺序）
    timestamp_candidates = [
        "timestamp", "time", "date", "datetime", "ts",
        "day", "hour", "minute"
    ]
    
    timestamp_column = None
    for candidate in timestamp_candidates:
        # 精确匹配
        if candidate in header_lower:
            idx = header_lower.index(candidate)
            timestamp_column = header[idx]
            break
        # 部分匹配
        for col in header:
            if candidate in col.lower():
                timestamp_column = col
                break
        if timestamp_column:
            break
    
    # 如果没找到，使用第一列
    if not timestamp_column and header:
        timestamp_column = header[0]
    
    # 检测数值列（优先级顺序）
    value_candidates = [
        "value", "lineid", "line_id", "id", "count", "num", "number",
        "score", "metric", "val", "amount", "quantity"
    ]
    
    value_column = None
    for candidate in value_candidates:
        # 精确匹配
        if candidate in header_lower:
            idx = header_lower.index(candidate)
            value_column = header[idx]
            break
        # 部分匹配
        for col in header:
            if candidate in col.lower():
                value_column = col
                break
        if value_column:
            break
    
    # 如果没找到，尝试找数值类型的列
    if not value_column and header:
        # 优先使用LineId（常见于日志文件）
        for col in header:
            if "lineid" in col.lower() or "id" in col.lower():
                value_column = col
                break
        
        # 如果还是没找到，使用最后一列
        if not value_column:
            value_column = header[-1]
    
    return timestamp_column or "timestamp", value_column or "value"

