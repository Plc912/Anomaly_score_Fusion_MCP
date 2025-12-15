"""
时间序列异常检测MCP服务器
使用FastMCP框架封装，支持SSE协议和MCP标准接口
"""
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastmcp import FastMCP

from src.anomaly_detector import AnomalyDetector
from src.stats_calculator import StatsCalculator
from src.fusion_engine import FusionEngine
from src.data_converter import convert_to_unified_format, save_unified_data

# 创建FastMCP实例
mcp = FastMCP("anomaly-fusion-mcp", debug=True, log_level="INFO")

# 全局实例（延迟初始化）
anomaly_detector = None
stats_calculator = None
fusion_engine = None


def _init_engines():
    """延迟初始化引擎"""
    global anomaly_detector, stats_calculator, fusion_engine
    if anomaly_detector is None:
        anomaly_detector = AnomalyDetector()
        stats_calculator = StatsCalculator()
        fusion_engine = FusionEngine()


@mcp.tool()
async def detect_anomaly(
    data: List[Dict[str, Any]],
    method: str = "lof",
    contamination: Optional[float] = None,
    threshold: Optional[float] = None,
    n_neighbors: Optional[int] = None,
    save_data: bool = True,
) -> Dict[str, Any]:
    """
    对统一格式的时间序列数据执行异常检测。
    
    输入数据格式：List[Dict[str, Any]]，每个元素包含：
    - 'time': str - 时间戳字符串
    - 'value': float - 数值
    
    参数:
    - data: List[Dict[str, Any]] - 统一格式的时间序列数据
    - method: str - 检测方法，可选: lof, knn, hbos, z_score, iqr, statistical（默认: lof）
    - contamination: Optional[float] - 异常比例（lof, knn, hbos使用，默认0.1）
    - threshold: Optional[float] - 阈值（z_score, statistical使用，默认3.0）
    - n_neighbors: Optional[int] - 邻居数量（lof, knn使用，默认20/5）
    - save_data: bool - 是否保存转换后的数据到models文件夹（默认True）
    
    返回:
    - Dict包含: scores, labels, method, anomaly_count, total_points, saved_path等
    """
    _init_engines()
    
    # 验证数据格式
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("数据必须是包含至少一个元素的列表")
    
    if not all(isinstance(item, dict) and "time" in item and "value" in item for item in data):
        raise ValueError("数据格式错误：每个元素必须是包含'time'和'value'键的字典")
    
    # 保存转换后的数据
    saved_path = None
    if save_data:
        try:
            saved_path = save_unified_data(data)
        except Exception as e:
            # 保存失败不影响检测
            pass
    
    # 准备检测参数
    params = {}
    if contamination is not None:
        params["contamination"] = contamination
    if threshold is not None:
        params["threshold"] = threshold
    if n_neighbors is not None:
        params["n_neighbors"] = n_neighbors
    
    # 执行检测
    result = await anomaly_detector.detect(data, method, params)
    
    return {
        "status": "ok",
        "method": method,
        "scores": result["scores"],
        "labels": result["labels"],
        "times": result.get("times", []),
        "values": result.get("values", []),
        "anomaly_count": sum(result["labels"]),
        "total_points": len(result["labels"]),
        "saved_path": saved_path
    }


@mcp.tool()
async def calculate_stats(
    data: List[Dict[str, Any]],
    metrics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    计算时间序列统计指标
    
    输入数据格式：List[Dict[str, Any]]，每个元素包含：
    - 'time': str - 时间戳字符串
    - 'value': float - 数值
    
    参数:
    - data: List[Dict[str, Any]] - 统一格式的时间序列数据
    - metrics: Optional[List[str]] - 要计算的指标列表，为空则计算所有
        可选: mean, median, std, variance, min, max, range, skewness, kurtosis,
             q1, q3, iqr, autocorr, trend, volatility, entropy
    
    返回:
    - Dict包含: metrics (Dict[str, float])
    """
    _init_engines()
    
    # 验证数据格式
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("数据必须是包含至少一个元素的列表")
    
    if not all(isinstance(item, dict) and "time" in item and "value" in item for item in data):
        raise ValueError("数据格式错误：每个元素必须是包含'time'和'value'键的字典")
    
    # 转换为TimeSeriesData格式（用于兼容stats_calculator）
    from src.models import TimeSeriesData
    timestamps = [item["time"] for item in data]
    values = [item["value"] for item in data]
    ts_data = TimeSeriesData(timestamps=timestamps, values=values)
    
    result = await stats_calculator.calculate(ts_data, metrics)
    
    return {
        "status": "ok",
        "metrics": result["metrics"],
        "timestamp": datetime.now().isoformat()
    }


@mcp.tool()
async def fuse_scores(
    algorithm_scores: Dict[str, float],
    fusion_method: str = "weighted_average",
    weights: Optional[Dict[str, float]] = None,
    label_threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    融合多个异常检测算法的评分
    
    参数:
    - algorithm_scores: Dict[str, float] - 各算法的评分字典，如 {"reconstruction_error": 0.85, "distance_score": 0.72}
    - fusion_method: str - 融合方法，可选: weighted_average, average, max, min, median, rank_fusion, confidence_weighted, dynamic_weight
    - weights: Optional[Dict[str, float]] - 融合权重（用于weighted_average等方法）
    - label_threshold: float - 判定异常的阈值（默认0.5，可按业务调整）
    
    返回:
    - Dict包含: fused_score (float), confidence (float), anomaly_label (bool), method (str)
    """
    _init_engines()
    
    result = await fusion_engine.fuse(
        algorithm_scores,
        fusion_method,
        weights,
        label_threshold,
    )
    
    return {
        "status": "ok",
        **result
    }


@mcp.tool()
async def batch_fuse_scores(
    data_points: List[Dict[str, Any]],
    fusion_method: str = "weighted_average",
    weights: Optional[Dict[str, float]] = None,
    label_threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    批量融合多个数据点的异常评分
    
    参数:
    - data_points: List[Dict[str, Any]] - 数据点列表，每个包含id和algorithm_scores
        示例: [{"id": 1, "algorithm_scores": {"algo1": 0.8, "algo2": 0.7}}, ...]
    - fusion_method: str - 融合方法
    - weights: Optional[Dict[str, float]] - 融合权重
    - label_threshold: float - 判定异常的阈值（默认0.5，可按业务调整）
    
    返回:
    - Dict包含: results (List[Dict])
    """
    _init_engines()
    
    results = []
    for item in data_points:
        result = await fusion_engine.fuse(
            item["algorithm_scores"],
            fusion_method,
            weights,
            label_threshold,
        )
        results.append({
            "id": item.get("id"),
            **result
        })
    
    return {
        "status": "ok",
        "count": len(results),
        "results": results
    }


@mcp.tool()
async def detect_anomaly_from_csv(
    path: str,
    timestamp_column: Optional[str] = None,
    value_column: Optional[str] = None,
    method: str = "lof",
    contamination: Optional[float] = None,
    threshold: Optional[float] = None,
    n_neighbors: Optional[int] = None,
    save_data: bool = True,
) -> Dict[str, Any]:
    """
    从CSV文件读取数据并执行异常检测。
    工具会自动将CSV数据转换为统一格式（List[Dict]，每个元素包含'time'和'value'键），
    然后使用指定的异常检测算法进行分析。
    
    支持的文件路径格式（优先在data文件夹查找）：
    - 仅文件名（如 "OpenSSH_2k.log_structured.csv"）会自动在data文件夹中查找
    - data/ 前缀（如 "data/OpenSSH_2k.log_structured.csv"）
    - @data/ 前缀（如 "@data/OpenSSH_2k.log_structured.csv"，@符号会被自动去除）
    - 相对路径或绝对路径
    
    参数:
    - path: str - CSV文件路径
    - timestamp_column: Optional[str] - CSV中时间戳列的名称，None则自动检测
    - value_column: Optional[str] - CSV中数值列的名称，None则自动检测
    - method: str - 异常检测方法，可选: lof, knn, hbos, z_score, iqr, statistical（默认: lof）
    - contamination: Optional[float] - 异常比例（lof, knn, hbos使用，默认0.1）
    - threshold: Optional[float] - 阈值（z_score, statistical使用，默认3.0）
    - n_neighbors: Optional[int] - 邻居数量（lof, knn使用）
    - save_data: bool - 是否保存转换后的数据到models文件夹（默认True）
    
    返回:
    - Dict包含: detection结果、anomaly_points、suggestions、saved_path等
    """
    _init_engines()
    
    # 使用数据转换器将CSV转换为统一格式
    unified_data = convert_to_unified_format(
        path,
        timestamp_column=timestamp_column,
        value_column=value_column
    )
    
    # 保存转换后的数据
    saved_path = None
    if save_data:
        try:
            from pathlib import Path
            filename = Path(path).stem + "_unified.json"
            saved_path = save_unified_data(unified_data, filename=filename)
        except Exception:
            pass
    
    # 准备检测参数
    params = {}
    if contamination is not None:
        params["contamination"] = contamination
    if threshold is not None:
        params["threshold"] = threshold
    if n_neighbors is not None:
        params["n_neighbors"] = n_neighbors
    
    # 执行异常检测
    result = await anomaly_detector.detect(unified_data, method, params)
    
    # 找出异常点的详细信息
    anomaly_points = []
    for i, (is_anomaly, score, time, value) in enumerate(zip(
        result["labels"],
        result["scores"],
        result["times"],
        result["values"]
    )):
        if is_anomaly:
            anomaly_points.append({
                "index": i,
                "time": time,
                "value": value,
                "score": round(score, 4)
            })
    
    # 生成建议
    suggestions = []
    anomaly_count = sum(result["labels"])
    total_points = len(result["labels"])
    anomaly_ratio = anomaly_count / total_points if total_points > 0 else 0
    
    if anomaly_count == 0:
        suggestions.append("✅ 未检测到异常数据，数据看起来正常")
    else:
        suggestions.append(f"⚠️ 检测到 {anomaly_count} 个异常点（占比 {anomaly_ratio*100:.2f}%）")
        
        if anomaly_ratio > 0.1:
            suggestions.append("⚠️ 异常点比例较高（>10%），建议检查数据质量或调整检测参数")
        
        if anomaly_ratio < 0.01:
            suggestions.append("✅ 异常点比例很低，数据质量良好")
        
        # 找出最异常的5个点
        if anomaly_points:
            top_anomalies = sorted(anomaly_points, key=lambda x: x["score"], reverse=True)[:5]
            suggestions.append(f"🔍 最异常的5个点：")
            for idx, point in enumerate(top_anomalies, 1):
                suggestions.append(
                    f"   {idx}. 时间: {point['time']}, 值: {point['value']}, "
                    f"异常评分: {point['score']:.4f}"
                )
    
    return {
        "status": "ok",
        "source": {
            "path": path,
            "total_points": total_points,
            "saved_path": saved_path
        },
        "detection": {
            "method": method,
            "anomaly_count": anomaly_count,
            "total_points": total_points,
            "anomaly_ratio": round(anomaly_ratio, 4),
            "scores": [round(s, 4) for s in result["scores"]],
            "labels": result["labels"]
        },
        "anomaly_points": anomaly_points,
        "suggestions": suggestions
    }


@mcp.tool()
async def list_available_tools() -> Dict[str, Any]:
    """
    列出所有可用的工具、方法和指标
    
    返回:
    - Dict包含所有可用的检测方法、融合方法和统计指标
    """
    _init_engines()
    
    return {
        "status": "ok",
        "anomaly_detection_methods": anomaly_detector.list_methods(),
        "fusion_methods": fusion_engine.list_methods(),
        "statistical_metrics": stats_calculator.list_metrics()
    }


if __name__ == "__main__":
    # 启动MCP服务器，使用SSE传输协议
    mcp.run(transport="sse", port=2250)

