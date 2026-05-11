# astrbot_sandbox_shipyard_neo

<div align="center">

English ｜ <a href="./README_cn.md">简体中文</a>

</div>

`astrbot_sandbox_shipyard_neo` is the Shipyard Neo sandbox driver plugin for AstrBot, and the recommended remote sandbox option. It targets Bay / Shipyard Neo deployments and adds browser automation plus Neo Skill lifecycle tools on top of shell, Python, and file operations.

## Key Features

1. 🛡️ Provides the `shipyard_neo` sandbox driver for AstrBot.
2. 💻 Supports shell, Python, file operations, and browser capabilities.
3. 🌐 Registers browser automation tools automatically.
4. 🧩 Registers Neo Skill lifecycle tools automatically.
5. 📦 Syncs local AstrBot Skills when the sandbox boots.
6. 🔑 Supports automatic Bay credential discovery from `credentials.json`.

## Quick Start

### Install the Plugin

Clone the plugin into AstrBot's plugin directory:

```bash
git clone https://github.com/zouyonghe/astrbot_sandbox_shipyard_neo.git data/plugins/astrbot_sandbox_shipyard_neo
```

Then restart AstrBot, or reload plugins from the plugin management page.

### Enable the Shipyard Neo Sandbox Driver

Enable sandbox mode in AstrBot and select the `shipyard_neo` sandbox driver:

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

## Configuration

| Key | Description |
| --- | --- |
| `shipyard_neo_endpoint` | Bay / Shipyard Neo API endpoint. |
| `shipyard_neo_access_token` | Bay API key. If empty, the plugin tries to auto-discover it. |
| `shipyard_neo_profile` | Sandbox profile, for example `python-default`. |
| `shipyard_neo_ttl` | Sandbox TTL in seconds. |

Credential auto-discovery checks:

- `$BAY_DATA_DIR/credentials.json`
- `./credentials.json`

## Best For

- Use this plugin when you need browser automation inside the sandbox.
- It also exposes Neo Skill lifecycle tools such as payload, candidate, release, rollback, and sync operations.
- Browser capability depends on the selected profile. A profile without browser support will not provide full browser behavior even though the plugin is installed.
- Managed sandbox cleanup uses `delete_sandbox=True` during teardown.

## Requirements and Limitations

- AstrBot must support external sandbox driver plugins.
- The Python dependency from `requirements.txt`: `shipyard-neo-sdk`.
- A working Bay / Shipyard Neo service is required.
- A valid Bay API key is required unless it can be auto-discovered.
- This plugin depends on a working Bay / Shipyard Neo deployment.
- Browser behavior depends on the selected profile and upstream runtime support.
- If you only need shell or file operations, classic Shipyard or BoxLite is usually lighter.

## Repository

- GitHub: https://github.com/zouyonghe/astrbot_sandbox_shipyard_neo
