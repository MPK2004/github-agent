import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.coordinator import Coordinator


PREFERRED_STACK, SKILL_LEVEL = range(2)


STACK_OPTIONS = ["Python", "JavaScript", "Rust", "AI/ML"]
SKILL_OPTIONS = ["Beginner", "Intermediate", "Advanced"]
USERS_PATH = BASE_DIR / "storage" / "users.json"


def load_users() -> dict:
    if not USERS_PATH.exists():
        return {}
    try:
        with USERS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except Exception:
        return {}


def save_users(data: dict) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with USERS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    users = load_users()
    user_id = str(user.id)
    username = user.username or ""
    profile = users.get(user_id) or {}
    profile["username"] = username
    users[user_id] = profile
    save_users(users)
    text = (
        "Welcome to the AI Open Source Contribution Mentor Agent.\n\n"
        "Step 1: Choose your preferred stack:\n"
        "- Python\n- JavaScript\n- Rust\n- AI/ML\n\n"
        "Please reply with one of these exactly."
    )
    await update.message.reply_text(text)
    return PREFERRED_STACK


async def set_preferred_stack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    stack = (update.message.text or "").strip()
    if stack not in STACK_OPTIONS:
        await update.message.reply_text(
            "Please choose a valid stack: Python, JavaScript, Rust, or AI/ML."
        )
        return PREFERRED_STACK
    context.user_data["preferred_stack"] = stack
    await update.message.reply_text(
        "Great. Now choose your skill level:\n- Beginner\n- Intermediate\n- Advanced\n\n"
        "Reply with one of these exactly."
    )
    return SKILL_LEVEL


async def set_skill_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    level = (update.message.text or "").strip()
    if level not in SKILL_OPTIONS:
        await update.message.reply_text(
            "Please choose a valid level: Beginner, Intermediate, or Advanced."
        )
        return SKILL_LEVEL
    users = load_users()
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or ""
    profile = users.get(user_id) or {}
    profile["username"] = username
    profile["preferred_stack"] = context.user_data.get("preferred_stack", "")
    profile["skill_level"] = level.lower()
    users[user_id] = profile
    save_users(users)
    await update.message.reply_text(
        "Your preferences are saved.\n\n"
        "You can now use:\n"
        "/find_issue to discover suitable GitHub issues\n"
        "/analyze_issue <github_issue_url> to analyze a specific issue."
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END


async def find_issue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = load_users()
    user = update.effective_user
    user_id = str(user.id)
    profile = users.get(user_id)
    if not profile or not profile.get("preferred_stack") or not profile.get("skill_level"):
        await update.message.reply_text(
            "I do not have your preferences yet. Use /start to register your preferred stack and skill level."
        )
        return
    coordinator = Coordinator()
    reasoning = [
        "Step 1: Reading your saved preferences",
        "Step 2: Finding candidate GitHub issues for your stack",
        "Step 3: Evaluating difficulty and filtering for your level",
        "Step 4: Selecting the best matches for you",
    ]
    reasoning_text = "\n".join(reasoning)
    await update.message.reply_text("Reasoning trace:\n" + reasoning_text)
    result = await coordinator.handle_find_issue(profile)
    await update.message.reply_text(result)


async def analyze_issue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = load_users()
    user = update.effective_user
    user_id = str(user.id)
    profile = users.get(user_id)
    if not context.args:
        await update.message.reply_text(
            "Usage: /analyze_issue <github_issue_url>"
        )
        return
    issue_url = context.args[0]
    coordinator = Coordinator()
    reasoning = [
        "Step 1: Fetching issue details",
        "Step 2: Fetching repository README",
        "Step 3: Analyzing the problem",
        "Step 4: Planning a solution and PR template",
    ]
    reasoning_text = "\n".join(reasoning)
    await update.message.reply_text("Reasoning trace:\n" + reasoning_text)
    result = await coordinator.handle_analyze_issue(issue_url, profile)
    await update.message.reply_text(result)


async def main_async() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    application = (
        ApplicationBuilder()
        .token(token)
        .build()
    )
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PREFERRED_STACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_preferred_stack)],
            SKILL_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_skill_level)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("find_issue", find_issue))
    application.add_handler(CommandHandler("analyze_issue", analyze_issue))
    await application.run_polling()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()


