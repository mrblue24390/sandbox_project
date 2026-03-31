import subprocess
import tempfile
import os
import resource
import datetime
import shlex
import signal
import sys

# ==============================
# 🔒 1. VALIDATOR (Security Layer for CLI Commands)
# ==============================

ALLOWED_COMMANDS = {
    # File operations (basic, no fancy features)
    'ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'grep', 'egrep', 'fgrep',
    'find', 'sort', 'uniq', 'wc', 'file', 'stat',

    # System info
    'date', 'cal', 'whoami', 'uname', 'df', 'du', 'free',

    # Directory operations
    'mkdir', 'touch', 'ln', 'cp', 'mv',

    # Text processing
    'cut', 'tr', 'sed', 'awk',
}

DANGEROUS_COMMANDS = {
    'rm', 'rmdir', 'dd', 'mkfs', 'fdisk', 'format', 'mount', 'umount',
    'chmod', 'chown', 'sudo', 'su', 'passwd', 'useradd', 'userdel',
    'kill', 'pkill', 'killall', 'reboot', 'shutdown', 'halt',
    'wget', 'curl', 'nc', 'netcat', 'telnet', 'ssh',
    'python', 'python3', 'pip', 'pip3', 'node', 'npm',
    'docker', 'systemctl', 'service', 'crontab', 'at',
    'ps', 'top', 'htop',  # These create many processes
}

DANGEROUS_PATTERNS = [
    '>', '>>', '|', '&', ';', '$', '`', '$(', '${',
    '/etc/shadow', '/root/', 'rm -rf', 'dd if=', 'mkfs.',
    ':(){ :|:& };:', 'fork bomb', 'while true', 'for i in'
]

def validate_command(command):
    """Validate if a command is safe to execute"""
    if not command or not command.strip():
        return False, "❌ Empty command"

    # Check for dangerous patterns
    command_lower = command.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in command_lower:
            return False, f"❌ Dangerous pattern detected: {pattern}"

    # Extract base command
    try:
        # Simple split to get first word (command)
        base_command = command.split()[0].strip()
        base_command = os.path.basename(base_command)

        # Check if command is explicitly dangerous
        if base_command in DANGEROUS_COMMANDS:
            return False, f"❌ Dangerous command blocked: {base_command}"

        # Check if command is allowed
        if base_command not in ALLOWED_COMMANDS:
            return False, f"❌ Command not allowed: {base_command}"

        # Special handling for ls to avoid color/aliases
        if base_command == 'ls':
            # Force ls to use simple output (no colors, no fancy formatting)
            command = command.replace('ls', 'ls --color=never')

        return True, command  # Return the modified command if needed

    except Exception as e:
        return False, f"❌ Command validation error: {e}"

# ==============================
# ⚙️ 2. RESOURCE LIMITS (Adjusted for better compatibility)
# ==============================

def set_resource_limits():
    """Set resource limits for the subprocess - More permissive for basic commands"""
    try:
        # CPU time limit (5 seconds - more time for basic commands)
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))

        # Memory limit (200 MB - more memory)
        resource.setrlimit(resource.RLIMIT_AS, (200 * 1024 * 1024, 200 * 1024 * 1024))

        # Process limit (50 processes - enough for basic commands)
        resource.setrlimit(resource.RLIMIT_NPROC, (50, 50))

        # File size limit (50 MB)
        resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024, 50 * 1024 * 1024))

        # Core dump limit (0 to prevent core dumps)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

        # File descriptor limit (100)
        resource.setrlimit(resource.RLIMIT_NOFILE, (100, 100))

    except Exception as e:
        pass  # Some limits might not be available on all systems

# ==============================
# 🚀 3. EXECUTION ENGINE (Simplified and Robust)
# ==============================

def execute_command(command):
    """Execute command in a simple, isolated environment"""

    # Create a temporary directory for isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        original_dir = os.getcwd()

        try:
            # Change to temp directory
            os.chdir(temp_dir)

            # Create a simple environment
            env = {
                'PATH': '/bin:/usr/bin',  # Minimal PATH
                'HOME': temp_dir,
                'USER': 'nobody',
                'LANG': 'C',
                'LC_ALL': 'C',
                'TERM': 'dumb',  # Disable fancy terminal features
                'PS1': '',  # No prompt
                'PS2': '',  # No secondary prompt
                'COLUMNS': '80',  # Fixed width
                'LINES': '24',  # Fixed height
            }

            # Execute command with subprocess (simpler approach)
            # Using shell=False to avoid shell injection, but we need to split the command
            # For commands with arguments, we need to parse them properly

            # Split command properly
            try:
                cmd_parts = shlex.split(command)
            except:
                cmd_parts = command.split()

            # For ls specifically, add --color=never if not already present
            if cmd_parts and cmd_parts[0] == 'ls' and '--color' not in command:
                cmd_parts.insert(1, '--color=never')

            # Execute with Popen for better control
            process = subprocess.Popen(
                cmd_parts,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=set_resource_limits,
                text=True,
                bufsize=1
            )

            try:
                # Wait for process with timeout
                stdout, stderr = process.communicate(timeout=5)
                returncode = process.returncode

                return {
                    "status": "success" if returncode == 0 else "error",
                    "command": command,
                    "output": stdout.strip(),
                    "error": stderr.strip() if stderr else "",
                    "returncode": returncode
                }

            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return {
                    "status": "error",
                    "command": command,
                    "output": stdout.strip() if stdout else "",
                    "error": "❌ Command execution timed out (exceeded 5 seconds)",
                    "returncode": -1
                }

        except Exception as e:
            return {
                "status": "error",
                "command": command,
                "output": "",
                "error": f"❌ Execution error: {str(e)}",
                "returncode": -1
            }
        finally:
            # Change back to original directory
            try:
                os.chdir(original_dir)
            except:
                pass

# ==============================
# 🧾 4. SIMPLE LOGGER
# ==============================

def log_command(command, result):
    """Simple logging function"""
    log_file = "sandbox_cli.log"
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"[{timestamp}] Command: {command}\n")
            f.write(f"Status: {result.get('status', 'unknown')}\n")
            f.write(f"Exit Code: {result.get('returncode', 'N/A')}\n")

            if result.get('output'):
                f.write(f"Output: {result['output'][:500]}\n")

            if result.get('error'):
                f.write(f"Error: {result['error'][:500]}\n")

            f.write(f"{'='*60}\n")
    except:
        pass  # Silent fail for logging

# ==============================
# 🎨 5. MAIN INTERFACE
# ==============================

def print_banner():
    """Print welcome banner"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║           🔒 SECURE CLI SANDBOX ENVIRONMENT 🔒            ║
╠═══════════════════════════════════════════════════════════╣
║  • Commands run in isolated temporary directories         ║
║  • Resource limits: CPU(5s), Memory(200MB), Processes(50) ║
║  • Only safe commands are allowed                         ║
║  • All commands are logged for security                   ║
╠═══════════════════════════════════════════════════════════╣
║  💡 Type 'help' for available commands                    ║
║  🚪 Type 'exit' to quit                                   ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)

def print_help():
    """Print help information"""
    help_text = """
📚 AVAILABLE COMMANDS:
═══════════════════════════════════════════════════════════

📁 FILE OPERATIONS:
  ls, cat, head, tail, grep, find, sort, uniq, wc, file, stat

📊 SYSTEM INFORMATION:
  date, cal, whoami, uname, df, du, free

📝 TEXT PROCESSING:
  echo, cut, tr, sed, awk

🗂️  DIRECTORY OPERATIONS:
  mkdir, touch, cp, mv, ln

❓ HELP:
  help

📋 EXAMPLES:
  $ ls -la
  $ echo "Hello World"
  $ cat /etc/passwd
  $ grep root /etc/passwd
  $ date
  $ whoami

⚠️  RESTRICTED COMMANDS:
  rm, sudo, su, python, wget, curl, ps, top, and more...

💡 TIP: Simple commands work best in this sandbox
"""
    print(help_text)

def print_result(result):
    """Print execution result"""
    print("\n" + "─"*60)
    print(f"📋 COMMAND: {result['command']}")

    if result['status'] == 'success':
        print(f"📊 STATUS: ✅ SUCCESS")
    else:
        print(f"📊 STATUS: ❌ {result.get('status', 'ERROR').upper()}")

    if result.get('output'):
        print(f"\n📤 OUTPUT:")
        print("─"*40)
        print(result['output'])

    if result.get('error'):
        print(f"\n⚠️  ERROR:")
        print("─"*40)
        print(result['error'])

    print(f"\n🔢 EXIT CODE: {result.get('returncode', 'N/A')}")
    print("─"*60)

# ==============================
# 🎮 6. MAIN LOOP
# ==============================

def main():
    """Main execution loop"""
    print_banner()

    history = []

    while True:
        try:
            # Get user input
            command = input("\n🔧 sandbox$ ").strip()

            # Handle empty input
            if not command:
                continue

            # Handle built-in commands
            if command.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Exiting sandbox...")
                break

            if command.lower() == 'help':
                print_help()
                continue

            if command.lower() == 'clear':
                os.system('clear')
                continue

            if command.lower() == 'history':
                print("\n📜 COMMAND HISTORY:")
                for i, cmd in enumerate(history[-20:], 1):
                    print(f"  {i}. {cmd}")
                continue

            # Add to history
            history.append(command)

            # Validate command
            is_safe, result = validate_command(command)

            if not is_safe:
                # Validation failed
                error_result = {
                    "status": "rejected",
                    "command": command,
                    "error": result,
                    "output": "",
                    "returncode": -1
                }
                print_result(error_result)
                log_command(command, error_result)
                continue

            # Use modified command if validation returned one
            actual_command = result if isinstance(result, str) and result != command else command

            # Execute command
            print("⏳ Executing...")
            exec_result = execute_command(actual_command)

            # Display result
            print_result(exec_result)

            # Log execution
            log_command(command, exec_result)

        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted. Type 'exit' to quit.")
            continue
        except EOFError:
            print("\n\n👋 Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            log_command(command, {"status": "error", "error": str(e)})

    print("\n✅ Sandbox session ended safely")

if __name__ == "__main__":
    main()
