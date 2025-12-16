# Telegram Git Bot

� Telegram `��L Git � Bot Agent

## ��

- ��U0�`��L Git �
- /��_hhomeoffice
- �h���P6�}
  �(
  P
- �Ճ� Git repositories

## ���

### 1. �ݝ�

```bash
uv sync
```

### 2. -����x

```bash
cp .env.example .env
# �/ .envke`� Telegram Bot Token
```

### 3. -� config.json

```json
{
    "machine_name": "home",
    "allowed_paths": ["~/"],
    "allowed_user_ids": [`�_Telegram_User_ID],
    "allowed_git_commands": ["status", "pull", "push", "fetch", "log", "diff", "branch"]
}
```

### 4. �L

```bash
uv run main.py
```

## (�

( Telegram -

```
/git <machine> <path> <command>
```

ċ

```
/git home ~/projects/myapp status
/git home ~/projects/myapp pull
/git home ~/projects/myapp log -5 --oneline
```

## �h

| �         | �        |
| --------- | -------- |
| `/start`  | ��(      |
| `/help`   | (�       |
| `/status` | Bot �K   |
| `/list`   | �@ Git H |
| `/git`    | �L Git � |

## ��

�tYx��https://htlin222.github.io/telegram-git-bot/

## License

MIT
