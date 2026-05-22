import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)
from github import Github, GithubException
import base64
import mimetypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is missing!")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable is missing!")
if not GITHUB_USERNAME:
    raise ValueError("GITHUB_USERNAME environment variable is missing!")

WAITING_REPO_NAME = 1
WAITING_FILES = 2

user_sessions = {}


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 নতুন Repo বানাও", callback_data="new_repo"),
            InlineKeyboardButton("📋 আমার Repos", callback_data="list_repos"),
        ],
        [
            InlineKeyboardButton("📤 ফাইল আপলোড করো", callback_data="upload_files"),
            InlineKeyboardButton("🔗 লাইভ লিংক পাও", callback_data="get_link"),
        ],
        [
            InlineKeyboardButton("🗑️ Repo মুছে ফেলো", callback_data="delete_repo"),
            InlineKeyboardButton("ℹ️ সাহায্য", callback_data="help"),
        ],
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 মেইন মেনুতে ফিরে যাও", callback_data="main_menu")]
    ])


def cancel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ বাতিল করো", callback_data="main_menu")]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 স্বাগতম, *{user.first_name}*!\n\n"
        "আমি তোমার *GitHub Deploy Bot* 🚀\n\n"
        "তুমি যা করতে পারবে:\n"
        "• নতুন GitHub Repo বানাতে পারবে\n"
        "• ফাইল আপলোড করলে সরাসরি GitHub-এ push হবে\n"
        "• HTML ফাইল হলে লাইভ ওয়েবসাইট লিংক পাবে\n"
        "• Python বট ফাইল হলে Render-এ deploy করতে পারবে\n\n"
        "নিচের বাটন থেকে শুরু করো 👇"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await query.edit_message_text(
            "🏠 *মেইন মেনু*\n\nকী করতে চাও?",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    elif data == "new_repo":
        user_sessions[query.from_user.id] = {"action": "new_repo"}
        await query.edit_message_text(
            "📁 *নতুন Repo বানাও*\n\n"
            "Repo-র নাম লিখো:\n"
            "_(শুধু ইংরেজি, হাইফেন ব্যবহার করতে পারো। যেমন: my-bot, telegram-project)_",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )

    elif data == "upload_files":
        if query.from_user.id not in user_sessions or "repo" not in user_sessions.get(query.from_user.id, {}):
            await query.edit_message_text(
                "⚠️ *প্রথমে একটি Repo সিলেক্ট করো!*\n\n"
                "📋 'আমার Repos' থেকে একটি Repo বেছে নাও অথবা নতুন বানাও।",
                parse_mode="Markdown",
                reply_markup=back_keyboard()
            )
            return

        repo_name = user_sessions[query.from_user.id]["repo"]
        user_sessions[query.from_user.id]["action"] = "upload"
        await query.edit_message_text(
            f"📤 *ফাইল আপলোড মোড চালু*\n\n"
            f"✅ সিলেক্টেড Repo: `{repo_name}`\n\n"
            f"এখন ফাইল পাঠাও! একে একে যেকোনো ফাইল পাঠাতে পারো:\n"
            f"• `main.py`, `requirements.txt` → Telegram Bot\n"
            f"• `index.html`, CSS, JS → Website\n"
            f"• যেকোনো ফাইল\n\n"
            f"_আপলোড শেষে /done লিখো_",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )

    elif data == "list_repos":
        await show_repos(query)

    elif data == "get_link":
        await show_link(query)

    elif data == "delete_repo":
        await show_repos_for_delete(query)

    elif data == "help":
        await query.edit_message_text(
            "ℹ️ *সাহায্য*\n\n"
            "*কীভাবে ব্যবহার করবে:*\n\n"
            "1️⃣ 'নতুন Repo বানাও' বাটন চাপো\n"
            "2️⃣ Repo-র নাম দাও\n"
            "3️⃣ 'ফাইল আপলোড করো' বাটন চাপো\n"
            "4️⃣ ফাইলগুলো পাঠাও\n"
            "5️⃣ /done লিখলে সব push হয়ে যাবে\n"
            "6️⃣ 'লাইভ লিংক পাও' বাটন চাপলে লিংক পাবে\n\n"
            "*HTML ফাইলের জন্য:*\n"
            "GitHub Pages অটো চালু হবে এবং লাইভ লিংক পাবে 🌐\n\n"
            "*Python বট ফাইলের জন্য:*\n"
            "Render.com-এ deploy করার লিংক পাবে 🚀",
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )

    elif data.startswith("select_repo:"):
        repo_name = data.split(":", 1)[1]
        if query.from_user.id not in user_sessions:
            user_sessions[query.from_user.id] = {}
        user_sessions[query.from_user.id]["repo"] = repo_name
        user_sessions[query.from_user.id]["action"] = "upload"

        await query.edit_message_text(
            f"✅ *Repo সিলেক্ট হয়েছে!*\n\n"
            f"📁 Repo: `{repo_name}`\n\n"
            f"এখন ফাইল পাঠাও! আপলোড শেষে /done লিখো।",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )

    elif data.startswith("delete_confirm:"):
        repo_name = data.split(":", 1)[1]
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ হ্যাঁ, মুছে ফেলো", callback_data=f"delete_yes:{repo_name}"),
                InlineKeyboardButton("❌ না, রাখো", callback_data="main_menu"),
            ]
        ])
        await query.edit_message_text(
            f"⚠️ *নিশ্চিত করো*\n\n"
            f"`{repo_name}` repo টি মুছে ফেলতে চাও?\n"
            f"_এই কাজ আর ফেরানো যাবে না!_",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif data.startswith("delete_yes:"):
        repo_name = data.split(":", 1)[1]
        try:
            g = Github(GITHUB_TOKEN)
            user = g.get_user(GITHUB_USERNAME)
            repo = user.get_repo(repo_name)
            repo.delete()
            await query.edit_message_text(
                f"🗑️ *Repo মুছে ফেলা হয়েছে!*\n\n`{repo_name}` সফলভাবে ডিলিট হয়েছে।",
                parse_mode="Markdown",
                reply_markup=back_keyboard()
            )
        except Exception as e:
            await query.edit_message_text(
                f"❌ *এরর হয়েছে:* {str(e)}",
                parse_mode="Markdown",
                reply_markup=back_keyboard()
            )


async def show_repos(query):
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user(GITHUB_USERNAME)
        repos = list(user.get_repos())

        if not repos:
            await query.edit_message_text(
                "📋 *তোমার কোনো Repo নেই!*\n\nনতুন Repo বানাও।",
                parse_mode="Markdown",
                reply_markup=back_keyboard()
            )
            return

        buttons = []
        for repo in repos[:10]:
            buttons.append([InlineKeyboardButton(
                f"📁 {repo.name}",
                callback_data=f"select_repo:{repo.name}"
            )])
        buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")])

        await query.edit_message_text(
            "📋 *তোমার Repos*\n\nকোনটায় ফাইল আপলোড করতে চাও?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ *এরর:* {str(e)}",
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )


async def show_repos_for_delete(query):
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user(GITHUB_USERNAME)
        repos = list(user.get_repos())

        if not repos:
            await query.edit_message_text(
                "📋 *তোমার কোনো Repo নেই!*",
                parse_mode="Markdown",
                reply_markup=back_keyboard()
            )
            return

        buttons = []
        for repo in repos[:10]:
            buttons.append([InlineKeyboardButton(
                f"🗑️ {repo.name}",
                callback_data=f"delete_confirm:{repo.name}"
            )])
        buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")])

        await query.edit_message_text(
            "🗑️ *কোন Repo মুছবে?*\n\n_সাবধান! মুছলে ফেরানো যাবে না।_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ *এরর:* {str(e)}",
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )


async def show_link(query):
    user_id = query.from_user.id
    if user_id not in user_sessions or "repo" not in user_sessions.get(user_id, {}):
        await query.edit_message_text(
            "⚠️ *প্রথমে একটি Repo সিলেক্ট করো!*",
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )
        return

    repo_name = user_sessions[user_id]["repo"]
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user(GITHUB_USERNAME)
        repo = user.get_repo(repo_name)

        # Check if HTML files exist (GitHub Pages)
        has_html = False
        try:
            contents = repo.get_contents("")
            for content in contents:
                if content.name.endswith(".html"):
                    has_html = True
                    break
        except:
            pass

        github_link = repo.html_url
        pages_link = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"

        text = f"🔗 *লিংক সমূহ*\n\n"
        text += f"📁 GitHub Repo:\n`{github_link}`\n\n"

        if has_html:
            # Enable GitHub Pages
            try:
                repo.enable_pages(source={"branch": "main", "path": "/"})
            except:
                pass
            text += f"🌐 লাইভ ওয়েবসাইট:\n`{pages_link}`\n\n"
            text += "_⏳ GitHub Pages চালু হতে ১-২ মিনিট লাগতে পারে_\n\n"

        text += f"🚀 Render Deploy লিংক:\nhttps://render.com/deploy"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📁 GitHub Repo খোলো", url=github_link)],
            [InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")]
        ])

        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    except Exception as e:
        await query.edit_message_text(
            f"❌ *এরর:* {str(e)}",
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id in user_sessions and user_sessions[user_id].get("action") == "new_repo":
        repo_name = text.strip().replace(" ", "-")
        try:
            g = Github(GITHUB_TOKEN)
            user = g.get_user(GITHUB_USERNAME)
            repo = user.create_repo(
                repo_name,
                description=f"Created by GitHub Deploy Bot",
                private=False,
                auto_init=True
            )
            user_sessions[user_id] = {"repo": repo_name, "action": "upload"}

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 এখনই ফাইল আপলোড করো", callback_data="upload_files")],
                [InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")]
            ])

            await update.message.reply_text(
                f"✅ *Repo তৈরি হয়েছে!*\n\n"
                f"📁 নাম: `{repo_name}`\n"
                f"🔗 লিংক: {repo.html_url}\n\n"
                f"এখন ফাইল আপলোড করো!",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except GithubException as e:
            await update.message.reply_text(
                f"❌ *Repo বানাতে পারিনি!*\n\n"
                f"কারণ: {e.data.get('message', str(e))}\n\n"
                f"_হয়তো এই নামে আগেই Repo আছে।_",
                parse_mode="Markdown",
                reply_markup=back_keyboard()
            )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_sessions or "repo" not in user_sessions.get(user_id, {}):
        await update.message.reply_text(
            "⚠️ *প্রথমে একটি Repo সিলেক্ট করো!*\n\n"
            "/start দিয়ে মেনু খোলো।",
            parse_mode="Markdown"
        )
        return

    repo_name = user_sessions[user_id]["repo"]

    # Get file info
    if update.message.document:
        file = update.message.document
        file_name = file.file_name
    else:
        await update.message.reply_text("❌ শুধু ফাইল পাঠাও।")
        return

    await update.message.reply_text(f"⏳ `{file_name}` আপলোড হচ্ছে...", parse_mode="Markdown")

    try:
        tg_file = await context.bot.get_file(file.file_id)
        file_bytes = await tg_file.download_as_bytearray()
        file_content = base64.b64encode(bytes(file_bytes)).decode("utf-8")

        g = Github(GITHUB_TOKEN)
        gh_user = g.get_user(GITHUB_USERNAME)
        repo = gh_user.get_repo(repo_name)

        # Check if file already exists
        try:
            existing = repo.get_contents(file_name)
            repo.update_file(
                path=file_name,
                message=f"Update {file_name} via Telegram Bot",
                content=file_bytes,
                sha=existing.sha
            )
            action = "আপডেট"
        except:
            repo.create_file(
                path=file_name,
                message=f"Add {file_name} via Telegram Bot",
                content=file_bytes
            )
            action = "আপলোড"

        # Detect file type for extra info
        extra = ""
        if file_name.endswith(".html"):
            extra = "\n🌐 HTML ফাইল পেয়েছি! `/done` লিখলে লাইভ লিংক পাবে।"
        elif file_name == "requirements.txt":
            extra = "\n🐍 Python requirements ফাইল পেয়েছি!"
        elif file_name == "main.py":
            extra = "\n🤖 Bot main file পেয়েছি!"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 আরো ফাইল পাঠাও", callback_data="upload_files")],
            [InlineKeyboardButton("✅ শেষ করো (/done)", callback_data="get_link")],
        ])

        await update.message.reply_text(
            f"✅ *`{file_name}` সফলভাবে {action} হয়েছে!*"
            f"{extra}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ *আপলোড ব্যর্থ হয়েছে!*\n\nকারণ: {str(e)}",
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_sessions or "repo" not in user_sessions.get(user_id, {}):
        await update.message.reply_text(
            "⚠️ কোনো active session নেই।\n/start দিয়ে শুরু করো।"
        )
        return

    repo_name = user_sessions[user_id]["repo"]

    try:
        g = Github(GITHUB_TOKEN)
        gh_user = g.get_user(GITHUB_USERNAME)
        repo = gh_user.get_repo(repo_name)

        contents = repo.get_contents("")
        has_html = any(f.name.endswith(".html") for f in contents)
        has_python = any(f.name.endswith(".py") for f in contents)

        github_link = repo.html_url
        pages_link = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"

        text = f"🎉 *সব ফাইল GitHub-এ push হয়ে গেছে!*\n\n"
        text += f"📁 Repo: `{repo_name}`\n"
        text += f"🔗 GitHub: {github_link}\n\n"

        buttons = [[InlineKeyboardButton("📁 GitHub Repo খোলো", url=github_link)]]

        if has_html:
            try:
                repo.enable_pages(source={"branch": "main", "path": "/"})
            except:
                pass
            text += f"🌐 লাইভ ওয়েবসাইট:\n{pages_link}\n"
            text += "_⏳ ১-২ মিনিট পর লাইভ হবে_\n\n"
            buttons.append([InlineKeyboardButton("🌐 ওয়েবসাইট খোলো", url=pages_link)])

        if has_python:
            render_link = f"https://render.com/deploy?repo={github_link}"
            text += f"🚀 Render-এ deploy করতে:\n{render_link}\n\n"
            buttons.append([InlineKeyboardButton("🚀 Render-এ Deploy করো", url="https://render.com")])

        buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")])

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ *এরর:* {str(e)}",
            parse_mode="Markdown",
            reply_markup=back_keyboard()
        )


import asyncio

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot চালু হয়েছে...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
