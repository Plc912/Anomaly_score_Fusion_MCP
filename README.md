# 时间序列异常检测MCP工具

## 📋 项目介绍

这是一个异常评分融合工具，融合多算法异常评分，重构误差+距离评分，提升稳健性，提供了完整的时序分析能力。工具支持多种异常检测算法、统计指标计算以及异常评分融合功能，采用模块化架构设计，易于扩展和维护。

### 核心特性

- ✅ **多种异常检测算法**：支持 Isolation Forest、LOF、KNN、HBOS、Z-score、IQR、Statistical 等7种算法
- ✅ **统计指标计算**：提供16种时间序列统计指标（均值、方差、偏度、峰度、自相关等）
- ✅ **异常评分融合**：支持8种融合策略（加权平均、排序融合、动态权重等）
- ✅ **CSV文件读取**：支持直接从CSV文件读取数据并执行异常检测
- ✅ **SSE流式接口**：支持Server-Sent Events实时数据流
- ✅ **标准化MCP接口**：清晰统一的接口设计，便于AI Agent集成
- ✅ **模块化架构**：算法、融合、统计模块独立，易于扩展
- ✅ **Docker容器化**：一键部署

## 🚀 环境搭建

### 系统要求

- **Python**: 3.11+
- **操作系统**: Windows / Linux / macOS
- **内存**: 建议 2GB+
- **磁盘**: 建议 1GB+ 可用空间

### 方式1：本地Python环境部署

#### 1. 安装Python依赖

```bash
# 安装依赖
pip install -r requirements.txt
```

#### 2. 启动服务器

```bash
python mcp_server.py
```

SSE端点为 `http://127.0.0.1:2250/sse`

### 方式2：Docker容器部署

#### 使用Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 使用Docker直接运行

```bash
# 构建镜像
docker build -t anomaly-fusion-mcp .

# 运行容器
docker run -d -p 2250:2250 --name anomaly_fusion anomaly-fusion-mcp
```

---

## 🔧 工具列表

本项目提供 **9个MCP工具**，分为以下类别：

### 1. 数据读取工具（3个）

#### `list_data_csv_files`

- **功能**：列出data文件夹下的所有CSV文件，帮助用户查看可用数据
- **参数**：无
- **返回**：文件列表，包含文件名、路径、列名等信息

#### `load_timeseries_csv`

- **功能**：从CSV文件读取时间序列数据（**支持自动检测列名**）
- **参数**：
  - `path`: CSV文件路径（**优先在data文件夹查找，支持模糊匹配**）
    - 仅文件名（如 `"OpenSSH_2k.log_structured.csv"`）会自动在data文件夹中查找
    - 支持模糊匹配：如果找不到精确匹配，会尝试查找包含该名称的文件
    - `data/` 前缀（如 `"data/OpenSSH_2k.log_structured.csv"`）
    - `@data/` 前缀（如 `"@data/OpenSSH_2k.log_structured.csv"`，@符号会被自动去除）
    - 相对路径或绝对路径
  - `timestamp_column`: 时间戳列名（**可选，None则自动检测**）
    - 自动检测优先级：timestamp > time > date > datetime > 第一列
  - `value_column`: 数值列名（**可选，None则自动检测**）
    - 自动检测优先级：value > lineid > id > count > 最后一列
  - `limit`: 可选，仅返回前N条记录
  - `dropna`: 是否跳过空值行（默认：True）
  - `auto_detect`: 是否启用自动列检测（默认：True）
- **返回**：时间戳列表、数值列表、文件信息

#### `detect_anomaly_from_csv`

- **功能**：从CSV文件直接读取数据并执行异常检测（**支持自动检测列名**）
- **参数**：
  - `path`: CSV文件路径（**优先在data文件夹查找，支持模糊匹配**，支持格式同上）
  - `method`: 检测方法（默认："isolation_forest"）
  - `timestamp_column`: 时间戳列名（**可选，None则自动检测**）
  - `value_column`: 数值列名（**可选，None则自动检测**）
  - `auto_detect`: 是否启用自动列检测（默认：True）
  - 其他算法参数（可选）
- **返回**：检测结果、异常点详情、专家建议

**使用示例**：

- 用户只需说："我想让你对OpenSSH_2k.log_structured.csv数据进行异常检测"
- 工具会自动：
  1. 在data文件夹查找该文件（支持模糊匹配）
  2. 自动检测合适的timestamp和value列
  3. 执行异常检测并返回结果

**使用示例**：

- `detect_anomaly_from_csv("HDFS_2k.log_structured.csv", timestamp_column="Date", value_column="LineId")`
- `detect_anomaly_from_csv("@data/HDFS_2k.log_structured.csv", timestamp_column="Date", value_column="LineId")`

### 2. 异常检测工具（1个）

#### `detect_anomaly`

- **功能**：对已有的时间序列数据执行异常检测
- **参数**：
  - `timestamps`: 时间戳列表
  - `values`: 数值列表
  - `method`: 检测方法（可选：isolation_forest, lof, knn, hbos, z_score, iqr, statistical）
  - 算法参数（可选）
- **返回**：异常评分、异常标签、检测方法信息

**支持的检测方法**：

- `isolation_forest` - Isolation Forest（孤立森林）
- `lof` - Local Outlier Factor（局部异常因子）
- `knn` - K-Nearest Neighbors（K近邻）
- `hbos` - Histogram-based Outlier Score（基于直方图）
- `z_score` - Z-score异常检测
- `iqr` - IQR (Interquartile Range) 异常检测
- `statistical` - 统计方法异常检测

### 3. 统计指标工具（1个）

#### `calculate_stats`

- **功能**：计算时间序列的统计指标
- **参数**：
  - `timestamps`: 时间戳列表
  - `values`: 数值列表
  - `metrics`: 可选，要计算的指标列表（为空则计算所有）
- **返回**：统计指标字典

**支持的统计指标**（16种）：

- 基础统计：mean, median, std, variance, min, max, range
- 分布特征：skewness, kurtosis, q1, q3, iqr
- 时序特征：autocorr, trend, volatility, entropy

### 4. 评分融合工具（2个）

#### `fuse_scores`

- **功能**：融合多个异常检测算法的评分
- **参数**：
  - `algorithm_scores`: 各算法的评分字典（例如：{"isolation_forest": 0.85, "lof": 0.72}）
  - `fusion_method`: 融合方法（默认："weighted_average"）
  - `weights`: 可选，融合权重字典
  - `label_threshold`: 可选，异常判定阈值（默认 0.5，可按业务调整）
- **返回**：融合评分、置信度、异常标签

**支持的融合方法**（8种）：

- `weighted_average` - 加权平均
- `average` - 简单平均
- `max` - 最大值
- `min` - 最小值
- `median` - 中位数
- `rank_fusion` - 排序融合
- `confidence_weighted` - 置信度加权
- `dynamic_weight` - 动态权重

#### `batch_fuse_scores`

- **功能**：批量融合多个数据点的异常评分
- **参数**：
  - `data_points`: 数据点列表（每个包含id和algorithm_scores）
  - `fusion_method`: 融合方法
  - `weights`: 可选，融合权重
  - `label_threshold`: 可选，异常判定阈值（默认 0.5，可按业务调整）
- **返回**：批量融合结果列表

### 5. 工具管理（2个）

#### `list_available_tools`

- **功能**：列出所有可用的工具、方法和指标
- **参数**：无
- **返回**：所有可用的检测方法、融合方法和统计指标列表

---

## ⚙️ 配置说明

### MCP客户端配置

```json
{
  "mcpServers": {
    "anomaly_fusion": {
      "name": "anomaly-fusion-mcp",
      "command": "python",
      "args": [
        "mcp_server.py"
      ],
      "transport": "sse",
      "port": 2250
    }
  }
}
```

### 环境变量

在 `docker-compose.yml` 中可配置：

- `PORT`: 服务端口（默认：2250）
- `LOG_LEVEL`: 日志级别（默认：INFO）

### CSV文件格式

示例数据文件位于 `data/sample_timeseries.csv`

**标准格式**：

```csv
timestamp,value
2024-01-01T00:00:00,2.02
2024-01-01T00:01:00,2.01
...
```

**要求**：

- 必须有表头行
- 时间戳列名默认为 `"timestamp"`（可通过参数修改）
- 数值列名默认为 `"value"`（可通过参数修改）

**特殊格式文件支持**：

对于非标准格式的CSV文件（如HDFS日志），可以通过参数指定列名：

- **HDFS日志文件示例**：

  ```csv
  LineId,Date,Time,Pid,Level,Component,Content,EventId,EventTemplate
  1,081109,203615,148,INFO,dfs.DataNode$PacketResponder,...
  ```

  使用方式：

  ```python
  detect_anomaly_from_csv(
      "HDFS_2k.log_structured.csv",
      timestamp_column="Date",  # 或 "Time"
      value_column="LineId"      # 使用LineId作为数值列
  )
  ```

**文件路径说明**：

- 所有数据文件应放在 `data/` 文件夹下
- 支持路径格式：
  - `"filename.csv"` - 自动在data文件夹查找
  - `"data/filename.csv"` - 明确指定data文件夹
  - `"@data/filename.csv"` - @符号会被自动去除

---

## 🌐 端口信息

### 服务端口

- **端口号**: `2250`
- **协议**: HTTP / SSE
- **访问地址**:
  - 服务地址：`http://127.0.0.1:2250`
  - SSE端点：`http://127.0.0.1:2250/sse`（AI客户端连接使用）

### 端口配置

- **Dockerfile**: EXPOSE 2250
- **docker-compose.yml**: ports "2250:2250"
- **mcp_server.py**: mcp.run(transport="sse", port=2250)

### 修改端口

如果需要修改端口，需要同时更新以下文件：

1. **mcp_server.py**（第420行）：

   ```python
   mcp.run(transport="sse", port=新端口号)
   ```
2. **docker-compose.yml**：

   ```yaml
   ports:
     - "新端口号:新端口号"
   environment:
     - PORT=新端口号
   ```
3. **mcp_config.json**：

   ```json
   "port": 新端口号
   ```

---

## 📝 注意事项

1. **数据格式**：时间序列数据需要至少2个数据点
2. **评分范围**：所有异常评分会被归一化到[0, 1]范围
3. **异常标签**：融合后的评分 > 0.5 判定为异常
4. **性能**：大批量数据建议使用批量融合接口
5. **SSE连接**：流式接口使用长连接，注意客户端超时设置

## 🤝 作者

作者：庞力铖  	 邮箱：3522236586@qq.com

GitHub仓库：
