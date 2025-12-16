#!/usr/bin/env python3
"""
Telegram Git Bot Agent
=====================
從 Telegram 遠端執行 Git 指令

使用方式:
    /git <machine> <path> <command>
    /git home ~/projects/myapp pull
    /git office ~/work/api status
"""

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

# ============================================================
# 設定
# ============================================================

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

CONFIG_FILE = Path(__file__).parent / "config.json"


@dataclass
class Config:
    """Bot 設定"""

    machine_name: str
    allowed_paths: list[Path]
    allowed_user_ids: list[int]
    allowed_git_commands: list[str]
    command_timeout: int
    max_output_length: int

    @classmethod
    def load(cls, path: Path) -> "Config":
        """從 JSON 檔載入設定"""
        with open(path) as f:
            data = json.load(f)

        return cls(
            machine_name=data["machine_name"],
            allowed_paths=[
                Path(p).expanduser().resolve() for p in data["allowed_paths"]
            ],
            allowed_user_ids=data["allowed_user_ids"],
            allowed_git_commands=data["allowed_git_commands"],
            command_timeout=data.get("command_timeout", 60),
            max_output_length=data.get("max_output_length", 3500),
        )


config = Config.load(CONFIG_FILE)


# ============================================================
# 安全檢查
# ============================================================


def is_user_allowed(user_id: int) -> bool:
    """檢查使用者是否有權限"""
    if not config.allowed_user_ids:
        return True
    return user_id in config.allowed_user_ids


def is_path_allowed(target_path: Path) -> bool:
    """檢查路徑是否在允許範圍內（但不能是 ~ 本身）"""
    try:
        resolved = target_path.expanduser().resolve()
        home = Path.home().resolve()

        # 不允許直接操作 home 目錄本身
        if resolved == home:
            return False

        # 允許 home 底下的任何子資料夾
        for allowed in config.allowed_paths:
            if resolved == allowed or allowed in resolved.parents:
                return True
        return False
    except Exception:
        return False


def is_valid_git_command(cmd: str) -> tuple[bool, str]:
    """檢查是否為允許的 git 指令"""
    cmd = cmd.strip()
    if not cmd:
        return False, ""
    first_word = cmd.split()[0]
    return first_word in config.allowed_git_commands, first_word


def is_git_repo(path: Path) -> bool:
    """檢查是否為 git repository"""
    git_dir = path / ".git"
    return git_dir.exists() and git_dir.is_dir()


def sanitize_input(text: str) -> str:
    """移除危險字元"""
    return re.sub(r"[;&|`$(){}\\]", "", text)


def find_git_repos(base_path: Path, max_depth: int = 3) -> list[Path]:
    """遞迴尋找 git repositories"""
    repos = []

    def search(path: Path, depth: int):
        if depth > max_depth:
            return
        try:
            if (path / ".git").is_dir():
                repos.append(path)
                return
            for child in path.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    search(child, depth + 1)
        except PermissionError:
            pass

    search(base_path, 0)
    return sorted(repos)


# ============================================================
# Git 執行
# ============================================================


@dataclass
class GitResult:
    """Git 指令執行結果"""

    success: bool
    output: str
    return_code: int
    error: str | None = None


def execute_git_command(path: Path, git_cmd: str) -> GitResult:
    """在指定路徑執行 git 指令"""
    full_command = f"git {git_cmd}"

    try:
        result = subprocess.run(
            full_command,
            shell=True,
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=config.command_timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )

        output = result.stdout.strip() or result.stderr.strip() or "(無輸出)"

        if len(output) > config.max_output_length:
            output = output[: config.max_output_length] + "\n... (已截斷)"

        return GitResult(
            success=result.returncode == 0,
            output=output,
            return_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        return GitResult(
            success=False,
            output="",
            return_code=-1,
            error=f"超時 ({config.command_timeout}秒)",
        )
    except Exception as e:
        return GitResult(
            success=False,
            output="",
            return_code=-1,
            error=str(e),
        )


# ============================================================
# Telegram Handlers
# ============================================================


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /start"""
    user = update.effective_user
    user_id = user.id

    if not is_user_allowed(user_id):
        await update.message.reply_text(
            f"❌ 沒有權限\n\n你的 User ID: `{user_id}`",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"👋 嗨 {user.first_name}！\n\n"
        f"我是 `{config.machine_name}` 的 Git Bot\n\n"
        f"**使用方式:**\n"
        f"`/git {config.machine_name} <path> <command>`\n\n"
        f"**範例:**\n"
        f"```\n"
        f"/git {config.machine_name} ~/projects/app status\n"
        f"/git {config.machine_name} ~/projects/app pull\n"
        f"```\n\n"
        f"輸入 /help 查看說明",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /help"""
    if not is_user_allowed(update.effective_user.id):
        return

    commands = ", ".join(config.allowed_git_commands)

    await update.message.reply_text(
        f"📖 **Git Bot 使用說明**\n\n"
        f"**格式:**\n"
        f"`/git <machine> <path> <git_command>`\n\n"
        f"**允許的 git 指令:**\n"
        f"`{commands}`\n\n"
        f"**其他指令:**\n"
        f"• /status - Bot 狀態\n"
        f"• /list - 列出專案\n\n"
        f"**範例:**\n"
        f"```\n"
        f"/git {config.machine_name} ~/projects/app status\n"
        f"/git {config.machine_name} ~/projects/app pull\n"
        f"/git {config.machine_name} ~/projects/app log -5 --oneline\n"
        f"```",
        parse_mode="Markdown",
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /status"""
    user_id = update.effective_user.id

    if not is_user_allowed(user_id):
        await update.message.reply_text(
            f"❌ 沒有權限 (ID: `{user_id}`)", parse_mode="Markdown"
        )
        return

    paths_list = "\n".join(f"  • `{p}`" for p in config.allowed_paths)

    await update.message.reply_text(
        f"🤖 **Git Bot 狀態**\n\n"
        f"**機器:** `{config.machine_name}`\n"
        f"**狀態:** 🟢 運行中\n\n"
        f"**允許路徑:**\n{paths_list}",
        parse_mode="Markdown",
    )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /list"""
    if not is_user_allowed(update.effective_user.id):
        return

    await update.message.reply_text("🔍 掃描中...")

    all_repos = []
    for base in config.allowed_paths:
        if base.exists():
            repos = find_git_repos(base)
            all_repos.extend(repos)

    if not all_repos:
        await update.message.reply_text(
            "📁 沒有找到 Git repository\n\n"
            "允許的路徑:\n" + "\n".join(f"  • `{p}`" for p in config.allowed_paths),
            parse_mode="Markdown",
        )
        return

    repos_text = "\n".join(f"  • `{r}`" for r in all_repos[:30])
    if len(all_repos) > 30:
        repos_text += f"\n  ... 還有 {len(all_repos) - 30} 個"

    await update.message.reply_text(
        f"📁 **找到 {len(all_repos)} 個 Git Repo:**\n\n{repos_text}",
        parse_mode="Markdown",
    )


async def git_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /git"""
    user_id = update.effective_user.id

    if not is_user_allowed(user_id):
        await update.message.reply_text(
            f"❌ 沒有權限\n\nUser ID: `{user_id}`",
            parse_mode="Markdown",
        )
        return

    args = context.args

    if not args or len(args) < 3:
        await update.message.reply_text(
            f"📖 **使用方式:**\n"
            f"`/git <machine> <path> <command>`\n\n"
            f"**範例:**\n"
            f"```\n"
            f"/git {config.machine_name} ~/projects/app pull\n"
            f"/git {config.machine_name} ~/projects/app status\n"
            f"```\n\n"
            f"輸入 /list 查看專案",
            parse_mode="Markdown",
        )
        return

    machine = args[0]
    path_str = args[1]
    git_cmd = " ".join(args[2:])

    # 不是這台機器，忽略
    if machine.lower() != config.machine_name.lower():
        return

    processing_msg = await update.message.reply_text(
        f"🔄 `{config.machine_name}` 處理中...",
        parse_mode="Markdown",
    )

    # 清理輸入
    path_str = sanitize_input(path_str)
    git_cmd = sanitize_input(git_cmd)

    # 驗證指令
    is_valid, first_word = is_valid_git_command(git_cmd)
    if not is_valid:
        await processing_msg.edit_text(
            f"❌ 不允許的指令: `{first_word or '(空)'}`\n\n"
            f"允許: `{', '.join(config.allowed_git_commands)}`",
            parse_mode="Markdown",
        )
        return

    # 解析路徑
    try:
        target_path = Path(path_str).expanduser().resolve()
    except Exception:
        await processing_msg.edit_text(
            f"❌ 無效路徑: `{path_str}`", parse_mode="Markdown"
        )
        return

    # 檢查存在
    if not target_path.exists():
        suggestions = []
        for base in config.allowed_paths:
            if base.exists():
                repos = find_git_repos(base, max_depth=2)
                suggestions.extend(repos[:5])

        suggestion_text = ""
        if suggestions:
            suggestion_text = "\n\n**可能你要找:**\n" + "\n".join(
                f"  • `{s}`" for s in suggestions[:5]
            )

        await processing_msg.edit_text(
            f"❌ 資料夾不存在: `{target_path}`{suggestion_text}",
            parse_mode="Markdown",
        )
        return

    # 檢查是目錄
    if not target_path.is_dir():
        await processing_msg.edit_text(
            f"❌ 不是資料夾: `{target_path}`", parse_mode="Markdown"
        )
        return

    # 檢查允許範圍
    if not is_path_allowed(target_path):
        paths_list = "\n".join(f"  • `{p}`" for p in config.allowed_paths)
        await processing_msg.edit_text(
            f"❌ 路徑不在允許範圍: `{target_path}`\n\n**允許:**\n{paths_list}",
            parse_mode="Markdown",
        )
        return

    # 檢查 git repo
    if not is_git_repo(target_path):
        await processing_msg.edit_text(
            f"❌ 不是 Git Repo: `{target_path}`\n\n💡 沒有 `.git` 目錄",
            parse_mode="Markdown",
        )
        return

    # 執行
    logger.info(f"User {user_id}: git {git_cmd} in {target_path}")
    result = execute_git_command(target_path, git_cmd)

    project_name = target_path.name

    if result.error:
        await processing_msg.edit_text(
            f"❌ **{config.machine_name}** / `{project_name}`\n\n錯誤: {result.error}",
            parse_mode="Markdown",
        )
    elif result.success:
        await processing_msg.edit_text(
            f"✅ **{config.machine_name}** / `{project_name}`\n"
            f"📍 `git {git_cmd}`\n\n"
            f"```\n{result.output}\n```",
            parse_mode="Markdown",
        )
    else:
        await processing_msg.edit_text(
            f"⚠️ **{config.machine_name}** / `{project_name}`\n"
            f"📍 `git {git_cmd}` (exit: {result.return_code})\n\n"
            f"```\n{result.output}\n```",
            parse_mode="Markdown",
        )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """未知指令"""
    if not is_user_allowed(update.effective_user.id):
        return
    await update.message.reply_text("❓ 未知指令，輸入 /help 查看說明")


# ============================================================
# 主程式
# ============================================================


def main() -> None:
    """啟動 Bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN 未設定！")
        logger.error("請在 .env 設定: TELEGRAM_BOT_TOKEN=your_token")
        return

    logger.info(f"🚀 Starting Git Bot on [{config.machine_name}]")
    logger.info(f"📁 Allowed paths: {config.allowed_paths}")
    logger.info(f"👤 Allowed users: {config.allowed_user_ids}")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("git", git_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
