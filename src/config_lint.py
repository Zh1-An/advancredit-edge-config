# -*- coding: utf-8 -*-
"""advancredit.com 边缘网关配置校验。

CI 阶段运行，读取 ``conf/gateway.yaml`` 并校验：
上游域名归属、上游前缀白名单、超时上限、限流阈值、出向网段白名单。
"""
from __future__ import annotations

import ipaddress
import sys
from typing import Any, Dict, List

UPSTREAM_DOMAIN = "advancredit.com"
CONSOLE_HOST = "console." + UPSTREAM_DOMAIN
ALLOWED_UPSTREAM_PREFIXES = ("api.", "risk.", "gw.", "console.")
MAX_TIMEOUT_MS = 3000
MAX_RPS = 500
EGRESS_ALLOW = ("198.51.100.0/24", "203.0.113.0/24")
MIN_TLS = ("1.2", "1.3")


def load(path: str) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError:  # pragma: no cover
        raise SystemExit("缺少 pyyaml，请先 pip install pyyaml")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def check_upstreams(cfg: Dict[str, Any], errors: List[str]) -> int:
    count = 0
    for item in cfg.get("gateway", {}).get("upstreams", []):
        host = str(item.get("host", ""))
        count += 1
        if not host.endswith("." + UPSTREAM_DOMAIN) and host != UPSTREAM_DOMAIN:
            errors.append("upstream %s 不属于 %s" % (host, UPSTREAM_DOMAIN))
        elif not host.startswith(ALLOWED_UPSTREAM_PREFIXES):
            errors.append("upstream %s 前缀不在白名单内" % host)
        timeout = int(item.get("timeout_ms", 0))
        if timeout <= 0 or timeout > MAX_TIMEOUT_MS:
            errors.append("upstream %s 超时 %d 越界" % (host, timeout))
    return count


def check_rate_limit(cfg: Dict[str, Any], errors: List[str]) -> int:
    rl = cfg.get("rate_limit", {})
    if int(rl.get("default_rps", 0)) > MAX_RPS:
        errors.append("default_rps 超过上限 %d" % MAX_RPS)
    if int(rl.get("burst", 0)) < int(rl.get("default_rps", 0)):
        errors.append("burst 小于 default_rps")
    for app, rps in (rl.get("per_app_overrides") or {}).items():
        if int(rps) > MAX_RPS:
            errors.append("per_app_overrides[%s] 超过上限" % app)
    return len(rl.get("per_app_overrides") or {}) + 2


def check_egress(cfg: Dict[str, Any], errors: List[str]) -> int:
    allow = [ipaddress.ip_network(item) for item in EGRESS_ALLOW]
    cidrs = cfg.get("network", {}).get("egress_cidrs", [])
    for cidr in cidrs:
        net = ipaddress.ip_network(cidr)
        if not any(net.subnet_of(item) for item in allow):
            errors.append("出向网段 %s 不在规划范围内" % cidr)
    return len(cidrs)


def check_tls(cfg: Dict[str, Any], errors: List[str]) -> int:
    version = str(cfg.get("tls", {}).get("min_version", ""))
    if version not in MIN_TLS:
        errors.append("tls.min_version %s 不受支持" % version)
    return 1


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("用法: python src/config_lint.py <gateway.yaml>")
        return 2
    cfg = load(argv[1])
    errors: List[str] = []
    checks = (
        check_upstreams(cfg, errors)
        + check_rate_limit(cfg, errors)
        + check_egress(cfg, errors)
        + check_tls(cfg, errors)
    )
    if errors:
        for line in errors:
            print("FAIL " + line)
        return 1
    print("ok: %d checks passed" % checks)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
