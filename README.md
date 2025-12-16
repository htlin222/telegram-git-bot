# Telegram git bot

A Telegram bot for remote Git operations.

## Features

- Remote Git command execution from anywhere
- Multi-machine support (home, office)
- Security: path restrictions, command allowlist, user permissions
- Automatic scan for Git repositories

## Quick start

### 1. Install dependencies

```bash
uv sync
```

### 2. Set environment variables

```bash
cp .env.example .env
# Edit .env with your Telegram Bot Token
```

### 3. Configure config.json

```bash
cp config.json.example config.json
# Edit config.json with your settings
```

```json
{
    "machine_name": "home",
    "allowed_paths": ["~/"],
    "allowed_user_ids": [YOUR_TELEGRAM_USER_ID],
    "allowed_git_commands": ["status", "pull", "push", "fetch", "log", "diff", "branch"]
}
```

### 4. Run

```bash
uv run main.py
```

## Usage

In Telegram:

```
/git <machine> <path> <command>
```

Examples:

```
/git home ~/projects/myapp status
/git home ~/projects/myapp pull
/git home ~/projects/myapp log -5 --oneline
```

## Commands

| Command   | Description         |
| --------- | ------------------- |
| `/start`  | Start bot           |
| `/help`   | Display help        |
| `/status` | Bot status          |
| `/list`   | List Git repos      |
| `/git`    | Execute Git command |

## Documentation

Full tutorial: https://htlin222.github.io/telegram-git-bot/

## License

MIT
