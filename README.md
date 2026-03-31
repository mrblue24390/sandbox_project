# 🔒 Secure CLI Sandbox

A secure, isolated command-line environment for executing safe CLI commands with resource restrictions and security monitoring.

## 📋 Table of Contents
- [Features](#features)
- [Security Measures](#security-measures)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Allowed Commands](#allowed-commands)
- [Blocked Commands](#blocked-commands)
- [Resource Limits](#resource-limits)
- [Architecture](#architecture)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

- **Complete Command Isolation**: Each command runs in a temporary, isolated directory
- **Resource Limitations**: CPU, memory, process, and file size limits
- **Command Whitelisting**: Only pre-approved commands can be executed
- **Dangerous Pattern Detection**: Blocks harmful command patterns and sequences
- **Automatic Logging**: All commands and outputs are logged for auditing
- **Command History**: Session command history tracking
- **No Shell Injection**: Safe command parsing without shell evaluation
- **Cross-Platform**: Works on Unix-like systems (Linux, macOS)

## 🛡️ Security Measures

### Command Validation
- **Whitelist-based**: Only allowed commands can execute
- **Pattern Detection**: Blocks dangerous patterns like pipes (`|`), redirections (`>`), and command chaining (`;`)
- **Path Restrictions**: Blocks directory traversal attempts (`..`)
- **Absolute Path Control**: Restricts access to system directories

### Resource Limits
| Resource | Limit | Purpose |
|----------|-------|---------|
| CPU Time | 5 seconds | Prevent infinite loops |
| Memory | 200 MB | Prevent memory exhaustion |
| Processes | 50 | Prevent fork bombs |
| File Size | 50 MB | Prevent disk filling |
| File Descriptors | 100 | Prevent resource exhaustion |

### Environment Isolation
- **Temporary Directory**: Each command gets a fresh temporary directory
- **Limited PATH**: Only `/bin` and `/usr/bin` are accessible
- **No Home Directory**: Isolated HOME directory in temp space
- **Dumb Terminal**: Disables fancy terminal features that could spawn processes

## 📋 Prerequisites

- **Python 3.6+**
- **Unix-like operating system** (Linux, macOS)
- Required Python modules (all in standard library):
  - `subprocess`
  - `tempfile`
  - `os`
  - `resource`
  - `datetime`
  - `shlex`
  - `signal`

## 🚀 Installation

1. **Clone or download the script:**
   ```bash
   git clone https://github.com/yourusername/secure-cli-sandbox.git
   cd secure-cli-sandbox
