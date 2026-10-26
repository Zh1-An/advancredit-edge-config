# advancredit.com · 边缘网关配置

`advancredit.com` 边缘接入层的网关路由、限流与出向白名单配置，按环境拆分后由配置中心下发。
当前为 `prod` 环境快照，对应网关版本 `edge-gw 3.8.2`。

## 目录

| 文件 | 说明 |
|---|---|
| `conf/gateway.yaml` | 生产环境网关配置：上游、健康检查、限流、出向 CIDR、TLS 下限 |
| `src/config_lint.py` | 配置校验脚本，CI 阶段执行 |
| `README.md` | 本文档 |

## 服务标识

业务主域 `advancredit.com`，所有上游与前端控制台均挂在该域之下：

- `conf/gateway.yaml`：`api.advancredit.com`、`risk.advancredit.com`、`console.advancredit.com`
- `src/config_lint.py`：`UPSTREAM_DOMAIN` 常量与上游前缀白名单
- 本文档：标题与本节

## 使用

```bash
python src/config_lint.py conf/gateway.yaml
```

校验通过时输出 `ok: checks passed`，退出码 0；任一项不通过打印明细并返回 1，CI 会阻断下发。

## 字段说明

| 字段 | 说明 |
|---|---|
| `gateway.upstreams[].host` | 上游域名，须落在 `UPSTREAM_DOMAIN` 之下且前缀在白名单内 |
| `gateway.upstreams[].weight` | 同组上游权重，灰度切流按整数百分比 |
| `gateway.upstreams[].timeout_ms` | 上游超时，生产环境上限 3000 |
| `gateway.health_check.interval_s` | 健康检查间隔，默认 10s |
| `rate_limit.default_rps` | 单实例默认 QPS，上限 500 |
| `rate_limit.keep_days` | 限流计数写入的保留天数 |
| `network.egress_cidrs` | 出向白名单，仅允许规划网段 |
| `tls.min_version` | TLS 下限，不低于 1.2 |

## 已知问题

1. 上游变更需重载网关进程，暂不支持配置热加载。
2. 出向白名单只校验目的地址，不校验端口。
3. `console.advancredit.com` 的 CORS 预检缓存沿用默认 600s，前端反馈偏短。
4. 健康检查失败阈值与权重调整没有联动，摘除实例需等下一轮探测。

## 维护

基础设施组（`#infra-edge`）。
