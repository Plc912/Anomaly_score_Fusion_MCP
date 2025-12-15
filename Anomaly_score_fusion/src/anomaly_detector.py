import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from sklearn.preprocessing import StandardScaler
from scipy import stats
from pyod.models.lof import LOF  # type: ignore
from pyod.models.knn import KNN  # type: ignore
from pyod.models.hbos import HBOS
import warnings
warnings.filterwarnings('ignore')



class AnomalyDetector:
    def __init__(self):
        self.scalers = {}
        self.models = {}
    
    async def detect(
        self,
        data: List[Dict[str, Any]],
        method: str = "lof",
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行异常检测
        
        Args:
            data: 统一格式的时间序列数据，List[Dict[str, Any]]，每个元素包含'time'和'value'键
            method: 检测方法名称（lof, knn, hbos, z_score, iqr, statistical）
            params: 算法参数
            
        Returns:
            检测结果字典，包含scores, labels, method, times, values
        """
        # 从统一格式中提取values
        values = np.array([item["value"] for item in data])
        times = [item["time"] for item in data]
        
        if len(values) < 2:
            raise ValueError("时间序列数据至少需要2个数据点")
        
        # 归一化数据（用于需要归一化的算法）
        values_2d = values.reshape(-1, 1)
        scaler = StandardScaler()
        values_scaled = scaler.fit_transform(values_2d).ravel()
        
        # 根据方法选择算法（只支持指定的方法）
        if method == "lof":
            scores, labels = self._lof(values_scaled, params)
        elif method == "knn":
            scores, labels = self._knn(values_scaled, params)
        elif method == "hbos":
            scores, labels = self._hbos(values_scaled, params)
        elif method == "z_score":
            scores, labels = self._z_score(values, params)
        elif method == "iqr":
            scores, labels = self._iqr(values, params)
        elif method == "statistical":
            scores, labels = self._statistical(values, params)
        else:
            raise ValueError(
                f"不支持的检测方法: {method}。"
                f"支持的方法: lof, knn, hbos, z_score, iqr, statistical"
            )
        
        return {
            "scores": scores.tolist() if isinstance(scores, np.ndarray) else scores,
            "labels": labels.tolist() if isinstance(labels, np.ndarray) else labels,
            "method": method,
            "times": times,
            "values": values.tolist()
        }
    #isolationforest
    #lof
    def _lof(self, values: np.ndarray, params: Optional[Dict]) -> tuple:
        """Local Outlier Factor异常检测"""
        if LOF is None:
            raise ImportError(
                "LOF需要pyod库支持。请安装或更新: pip install --upgrade pyod\n"
                "如果已安装，请尝试: pip uninstall pyod -y && pip install pyod"
            )
        
        n_neighbors = params.get("n_neighbors", 20) if params else 20
        contamination = params.get("contamination", 0.1) if params else 0.1
        
        model = LOF(n_neighbors=n_neighbors, contamination=contamination)
        values_2d = values.reshape(-1, 1)
        
        labels = model.fit_predict(values_2d)
        scores = model.decision_scores_
        
        # 归一化分数
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        labels = labels == 1
        
        return scores, labels
    #knn
    def _knn(self, values: np.ndarray, params: Optional[Dict]) -> tuple:
        """K-Nearest Neighbors异常检测"""
        if KNN is None:
            raise ImportError(
                "KNN需要pyod库支持。请安装或更新: pip install --upgrade pyod\n"
                "如果已安装，请尝试: pip uninstall pyod -y && pip install pyod"
            )
        
        n_neighbors = params.get("n_neighbors", 5) if params else 5
        contamination = params.get("contamination", 0.1) if params else 0.1
        
        model = KNN(n_neighbors=n_neighbors, contamination=contamination)
        values_2d = values.reshape(-1, 1)
        
        labels = model.fit_predict(values_2d)
        scores = model.decision_scores_
        
        # 归一化分数
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        labels = labels == 1
        
        return scores, labels
    #hbos
    def _hbos(self, values: np.ndarray, params: Optional[Dict]) -> tuple:
        """Histogram-based Outlier Score异常检测"""
        if HBOS is None:
            raise ImportError(
                "HBOS需要pyod库支持。请安装或更新: pip install --upgrade pyod\n"
                "如果已安装，请尝试: pip uninstall pyod -y && pip install pyod"
            )
        
        contamination = params.get("contamination", 0.1) if params else 0.1
        
        model = HBOS(contamination=contamination)
        values_2d = values.reshape(-1, 1)
        
        labels = model.fit_predict(values_2d)
        scores = model.decision_scores_
        
        # 归一化分数
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        labels = labels == 1
        
        return scores, labels
    #z_score
    def _z_score(self, values: np.ndarray, params: Optional[Dict]) -> tuple:
        """Z-score异常检测"""
        threshold = params.get("threshold", 3.0) if params else 3.0
        
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            scores = np.zeros_like(values)
            labels = np.zeros_like(values, dtype=bool)
        else:
            z_scores = np.abs((values - mean) / std)
            scores = z_scores / threshold  # 归一化到[0, 1]附近
            scores = np.clip(scores, 0, 1)
            labels = z_scores > threshold
        
        return scores, labels
    #iqr
    def _iqr(self, values: np.ndarray, params: Optional[Dict]) -> tuple:
        """IQR (Interquartile Range) 异常检测"""
        multiplier = params.get("multiplier", 1.5) if params else 1.5
        
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        if iqr == 0:
            scores = np.zeros_like(values)
            labels = np.zeros_like(values, dtype=bool)
        else:
            lower_bound = q1 - multiplier * iqr
            upper_bound = q3 + multiplier * iqr
            
            # 计算每个点到边界的距离
            distances = np.maximum(
                lower_bound - values,
                values - upper_bound
            )
            distances = np.maximum(distances, 0)
            
            max_distance = np.max(distances) if np.max(distances) > 0 else 1
            scores = distances / max_distance
            scores = np.clip(scores, 0, 1)
            
            labels = (values < lower_bound) | (values > upper_bound)
        
        return scores, labels
    #statistical
    def _statistical(self, values: np.ndarray, params: Optional[Dict]) -> tuple:
        """基于统计方法的异常检测（组合多种统计方法）"""
        # 计算Z-score
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            z_scores = np.zeros_like(values)
        else:
            z_scores = np.abs((values - mean) / std)
        
        # 计算修改后的Z-score（使用中位数）
        median = np.median(values)
        mad = np.median(np.abs(values - median))  # Median Absolute Deviation
        
        if mad == 0:
            modified_z_scores = np.zeros_like(values)
        else:
            modified_z_scores = np.abs(0.6745 * (values - median) / mad)
        
        # 组合两种方法
        combined_scores = (z_scores + modified_z_scores) / 2
        threshold = params.get("threshold", 3.0) if params else 3.0
        
        # 归一化
        max_score = np.max(combined_scores) if np.max(combined_scores) > 0 else 1
        scores = combined_scores / max_score
        scores = np.clip(scores, 0, 1)
        
        labels = combined_scores > threshold
        
        return scores, labels
    # 列出支持的方法
    def list_methods(self) -> List[str]:
        """列出所有支持的检测方法"""
        methods = [
            "z_score",
            "iqr",
            "statistical"
        ]
        
        # 只有pyod可用时才添加这些方法
        if LOF is not None and KNN is not None and HBOS is not None:
            methods.extend(["lof", "knn", "hbos"])
        
        return methods

