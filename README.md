# astrbot_sandbox_shipyard_neo

Chinese version: [`README_cn.md`](./README_cn.md)

`astrbot_sandbox_shipyard_neo` is an AstrBot sandbox runtime plugin that adds the `shipyard_neo` provider.

It targets Bay / Shipyard Neo workflows and adds browser automation plus Neo skill lifecycle tools.

## Features

- Provides the `shipyard_neo` sandbox runtime for AstrBot.
- Supports shell, Python, filesystem, and browser capabilities.
- Registers browser automation tools automatically.
- Registers Neo skill lifecycle tools automatically.
- Syncs local AstrBot skills into the sandbox when the sandbox boots.
- Supports automatic Bay credential discovery from `credentials.json`.

## Requirements

- An AstrBot build that supports external sandbox provider plugins.
- The Python dependency from `requirements.txt`: `shipyard-neo-sdk`.
- A running Bay / Shipyard Neo service.
- A valid Bay API key, unless it can be auto-discovered.

## Installation

Clone the plugin into AstrBot's plugin directory:

```bash
git clone https://github.com/zouyonghe/astrbot_sandbox_shipyard_neo.git data/plugins/astrbot_sandbox_shipyard_neo
```

Then restart AstrBot or reload plugins.

## Configuration

Enable sandbox runtime in AstrBot and select this provider:

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

Provider-specific options:

| Key | Description |
| --- | --- |
| `shipyard_neo_endpoint` | Bay / Shipyard Neo API endpoint. |
| `shipyard_neo_access_token` | Bay API key. If empty, the plugin tries to auto-discover it. |
| `shipyard_neo_profile` | Sandbox profile, for example `python-default`. |
| `shipyard_neo_ttl` | Sandbox TTL in seconds. |

Credential auto-discovery checks:

- `$BAY_DATA_DIR/credentials.json`
- `./credentials.json`

## Usage Notes

- This plugin is the best fit when you need browser execution inside the sandbox.
- It also exposes Neo-oriented skill lifecycle tools such as payload, candidate, release, rollback, and sync operations.
- Browser capability depends on the selected profile. A profile without browser support will not provide full browser behavior even though the plugin is installed.
- Managed sandbox cleanup uses `delete_sandbox=True` during teardown.

## Limitations

- This plugin depends on a working Bay / Shipyard Neo deployment.
- Browser behavior depends on the selected profile and upstream runtime support.
- The plugin is more specialized than the classic Shipyard runtime and may be unnecessary if you only need shell or file operations.

## Repository

- GitHub: https://github.com/zouyonghe/astrbot_sandbox_shipyard_neo
