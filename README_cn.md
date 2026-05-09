# astrbot_sandbox_shipyard_neo

英文版说明：[`README.md`](./README.md)

`astrbot_sandbox_shipyard_neo` 是一个为 AstrBot 提供 `shipyard_neo` 运行时的插件。

它面向 Bay / Shipyard Neo 场景，除了基础沙箱能力外，还提供浏览器自动化和 Neo skill 生命周期工具。

## 功能特性

- 为 AstrBot 提供 `shipyard_neo` 沙箱运行时。
- 支持 shell、Python、文件系统、浏览器能力。
- 自动注册浏览器自动化工具。
- 自动注册 Neo skill 生命周期工具。
- 沙箱启动时会同步本地 AstrBot skills。
- 支持从 `credentials.json` 自动发现 Bay 凭据。

## 依赖要求

- 需要使用已经支持外部 sandbox provider 插件的 AstrBot 版本。
- 依赖 `requirements.txt` 中的 `shipyard-neo-sdk`。
- 需要已经运行的 Bay / Shipyard Neo 服务。
- 需要有效的 Bay API Key，或者能被自动发现。

## 安装方式

把插件克隆到 AstrBot 的插件目录：

```bash
git clone https://github.com/zouyonghe/astrbot_sandbox_shipyard_neo.git data/plugins/astrbot_sandbox_shipyard_neo
```

然后重启 AstrBot，或重新加载插件。

## 配置方法

先在 AstrBot 核心配置中启用 sandbox，并把运行时设置为 `shipyard_neo`：

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

插件支持的配置项：

| 键名 | 说明 |
| --- | --- |
| `shipyard_neo_endpoint` | Bay / Shipyard Neo API 地址。 |
| `shipyard_neo_access_token` | Bay API Key。留空时会尝试自动发现。 |
| `shipyard_neo_profile` | 沙箱 profile，例如 `python-default`。 |
| `shipyard_neo_ttl` | 沙箱 TTL，单位秒。 |

自动发现凭据时会检查：

- `$BAY_DATA_DIR/credentials.json`
- 当前工作目录下的 `credentials.json`

## 使用说明

- 当你需要在沙箱内执行浏览器自动化时，这个插件是更合适的选择。
- 它还会暴露 Neo skill 生命周期相关工具，例如 payload、candidate、release、rollback、sync。
- 浏览器能力是否真正可用，取决于你选择的 profile 是否支持 browser。
- 插件在销毁托管沙箱时会使用 `delete_sandbox=True` 来清理资源。

## 限制说明

- 依赖可用的 Bay / Shipyard Neo 服务。
- 浏览器行为受 profile 和上游运行时支持情况影响。
- 如果你只需要 shell 或文件操作，这个插件可能比经典 Shipyard 运行时更重。

## 仓库地址

- GitHub: https://github.com/zouyonghe/astrbot_sandbox_shipyard_neo
