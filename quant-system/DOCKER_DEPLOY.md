# Docker 部署指南

## 🚀 快速启动

### 方式一：Docker Compose（推荐）

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式二：单独运行容器

```bash
# 构建镜像
docker build -t quant-system .

# 运行Dashboard
docker run -d \
  -p 8050-8053:8050-8053 \
  -p 8055:8055 \
  -v $(pwd)/data/db:/app/data/db \
  -v $(pwd)/data/cache:/app/data/cache \
  -v $(pwd)/config:/app/config \
  quant-system

# 运行调度器
docker run -d \
  -v $(pwd)/data/db:/app/data/db \
  -v $(pwd)/config:/app/config \
  quant-system \
  python scripts/run_scheduler.py start
```

---

## 📋 服务说明

| 服务名称 | 端口 | 说明 | 访问地址 |
|---------|------|------|---------|
| dashboard | 8050-8053, 8055 | 统一门户+5个看板 | http://localhost:8055 |
| scheduler | - | 定时任务调度器 | - |

### Dashboard端口分配：
- 8050: 策略回测看板
- 8051: 因子分析看板
- 8052: ML模型看板
- 8053: 实盘监控看板
- 8055: **统一门户（主入口）** ✨

---

## 🔧 配置说明

### 1. 数据持久化

通过Volume挂载，数据不会因容器重启丢失：

```yaml
volumes:
  - ./data/db:/app/data/db      # 数据库文件
  - ./data/cache:/app/data/cache # 采集缓存
  - ./data/backup:/app/data/backup # 备份文件
  - ./config:/app/config        # 配置文件
```

### 2. 时区设置

默认已设置为 `Asia/Shanghai`，如需修改：

```yaml
environment:
  - TZ=Asia/Shanghai
```

### 3. 券商配置（实盘交易）

1. 复制配置模板：
```bash
cp config/broker.yaml.example config/broker.yaml
```

2. 编辑 `config/broker.yaml`，填写真实券商信息：
```yaml
broker:
  type: "easytrader"  # 改为实盘模式
  simulation_mode: false  # 关闭模拟模式
```

⚠️ **注意**：实盘交易前请务必先在模拟模式下充分测试！

---

## 📦 常用命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f dashboard
docker-compose logs -f scheduler
```

### 进入容器
```bash
docker-compose exec dashboard bash
```

### 手动触发任务
```bash
# 进入容器后执行
docker-compose exec scheduler bash
python scripts/run_scheduler.py trigger data_collection
```

### 数据库备份
```bash
# 手动备份
docker-compose exec dashboard python -m utils.db_backup backup

# 查看备份列表
docker-compose exec dashboard python -m utils.db_backup list
```

---

## 🔄 服务重启与更新

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart dashboard
```

### 更新代码后重新构建
```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

---

## 🐛 故障排查

### 1. 端口被占用
```bash
# 检查端口占用
lsof -i :8055

# 修改docker-compose.yml中的端口映射
ports:
  - "8080:8055"  # 改为其他端口
```

### 2. 权限问题
```bash
# 修复数据目录权限
sudo chown -R 1000:1000 data/
```

### 3. 容器无法启动
```bash
# 查看启动日志
docker-compose logs --tail=50 dashboard

# 检查配置文件
ls -la config/
```

### 4. Healthcheck失败
```bash
# 手动检查服务
docker-compose exec dashboard curl http://localhost:8055

# 查看进程
docker-compose exec dashboard ps aux
```

---

## 📊 资源限制建议

根据数据量大小，建议调整资源限制：

```yaml
services:
  dashboard:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

---

## 🔒 安全建议

1. **不要在镜像中内置敏感信息** - 所有配置通过Volume挂载
2. **生产环境** 修改默认端口，设置防火墙规则
3. **实盘交易** 务必先在模拟模式下充分测试
4. **定期备份** 数据库文件到外部存储
5. **监控告警** 配置AlertManager，及时接收异常通知

---

## 📈 扩容方案

### 多实例部署（单机）
```yaml
services:
  dashboard-1:
    build: .
    ports:
      - "8050:8050"
    # ...

  dashboard-2:
    build: .
    ports:
      - "8060:8050"
    # ...
```

### 使用外部数据库（推荐）
- 将DuckDB替换为PostgreSQL/ClickHouse
- 使用共享存储挂载数据目录
- 配置主从复制和读写分离

---

## ✅ 部署检查清单

- [ ] Docker和Docker Compose已安装
- [ ] 数据目录权限正确
- [ ] 配置文件已准备（broker.yaml等）
- [ ] 端口未被占用
- [ ] 防火墙规则已配置
- [ ] 备份策略已设置
- [ ] 监控告警已配置

部署完成后访问：**http://your-server-ip:8055**
