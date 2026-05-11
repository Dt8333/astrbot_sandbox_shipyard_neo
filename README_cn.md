# astrbot_sandbox_shipyard_neo

<div align="center">

<a href="./README.md">English</a> ｜ 简体中文

</div>

`astrbot_sandbox_shipyard_neo` 是 AstrBot 的 Shipyard Neo 沙盒驱动插件，也是更推荐的远程沙盒方案。它面向 Bay / Shipyard Neo 部署，除了 Shell、Python 和文件操作，还提供浏览器自动化和 Neo Skill 生命周期工具。

## 主要功能

1. 🛡️ 为 AstrBot 提供 `shipyard_neo` 沙盒驱动。
2. 💻 支持 Shell、Python、文件操作和浏览器能力。
3. 🌐 自动注册浏览器自动化工具。
4. 🧩 自动注册 Neo Skill 生命周期工具。
5. 📦 沙盒启动时会同步本地 AstrBot Skills。
6. 🔑 支持从 `credentials.json` 自动发现 Bay 凭据。

## 快速开始

### 安装插件

把插件克隆到 AstrBot 插件目录：

```bash
git clone https://github.com/zouyonghe/astrbot_sandbox_shipyard_neo.git data/plugins/astrbot_sandbox_shipyard_neo
```

然后重启 AstrBot，或在插件管理页重新加载插件。

### 启用 Shipyard Neo 沙盒驱动

先在 AstrBot 核心配置中启用沙盒模式，并把沙盒驱动设置为 `shipyard_neo`：

```json
{
  "provider_settings": {
    "computer_use_runtime": "sandbox",
    "sandbox": {
      "booter": "shipyard_neo"
    }
  }
}
```

## 配置项

| 键名 | 说明 |
| --- | --- |
| `shipyard_neo_endpoint` | Bay / Shipyard Neo API 地址，默认值为 `http://127.0.0.1:8114`。 |
| `shipyard_neo_access_token` | Bay API Key。留空时，本机自动启动会生成新密钥；外部端点会尝试自动发现。 |
| `shipyard_neo_profile` | 沙盒 profile，例如 `python-default`。 |
| `shipyard_neo_ttl` | 沙盒 TTL，单位秒。 |

如果 AstrBot 和 Bay 运行在同一个 Docker Compose 网络中，请把 `shipyard_neo_endpoint` 配成 Bay 服务名，并确保 AstrBot 能访问对应网络。

自动发现凭据时会检查：

- `$BAY_DATA_DIR/credentials.json`
- 当前工作目录下的 `credentials.json`

## 适合场景

- 当你需要在沙盒内执行浏览器自动化时，优先使用这个插件。
- 它还会提供 Neo Skill 生命周期工具，例如 payload、candidate、release、rollback、sync。
- 浏览器能力是否可用，取决于所选 profile 是否支持 browser。
- 插件销毁托管沙盒时会使用 `delete_sandbox=True` 清理资源。

## 依赖与限制

- 需要使用支持外部沙盒驱动插件的 AstrBot 版本。
- 依赖 `requirements.txt` 中的 `shipyard-neo-sdk`。
- 需要可用的 Bay / Shipyard Neo 服务。
- 需要有效的 Bay API Key，或者能被自动发现。
- 浏览器行为受 profile 和上游运行时支持情况影响。
- 如果只需要 Shell 或文件操作，经典 Shipyard 或 BoxLite 通常更轻。

## 仓库地址

- GitHub: https://github.com/zouyonghe/astrbot_sandbox_shipyard_neo
