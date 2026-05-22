# 🚀 GitHub Deploy Bot

টেলিগ্রাম বটের মাধ্যমে যেকোনো ফাইল GitHub-এ push করো!

## ✨ ফিচারসমূহ

- 📁 নতুন GitHub Repo বানাও সরাসরি বট থেকে
- 📤 ফাইল পাঠালেই GitHub-এ push হয়ে যাবে
- 🌐 HTML ফাইলের জন্য GitHub Pages লিংক পাবে
- 🤖 Python বট ফাইল হলে Render deploy লিংক পাবে
- 🗑️ Repo ডিলিট করার অপশন
- সুন্দর বাংলা বাটন মেনু

## ⚙️ সেটআপ

### ১. Environment Variables

Render.com-এ এই ৩টি variable সেট করো:

```
BOT_TOKEN=তোমার_টেলিগ্রাম_বট_টোকেন
GITHUB_TOKEN=তোমার_github_personal_access_token
GITHUB_USERNAME=তোমার_github_username
```

### ২. GitHub Token বানানো

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token" ক্লিক করো
3. এই permissions দাও:
   - `repo` (সব)
   - `delete_repo`
4. Token কপি করে রাখো

### ৩. Telegram Bot Token

1. [@BotFather](https://t.me/BotFather) তে যাও
2. `/newbot` দাও
3. Token কপি করো

### ৪. Render.com-এ Deploy

1. এই ফাইলগুলো GitHub-এ push করো
2. Render.com → New Web Service
3. GitHub repo কানেক্ট করো
4. Environment variables সেট করো
5. Deploy!

## 📱 ব্যবহার করার নিয়ম

1. `/start` দাও
2. "নতুন Repo বানাও" চাপো
3. Repo-র নাম দাও
4. ফাইল পাঠাও
5. `/done` লিখলে সব push হবে এবং লিংক পাবে

## 📁 ফাইল স্ট্রাকচার

```
github-deploy-bot/
├── main.py          # মূল বট কোড
├── requirements.txt # Python dependencies
├── Procfile         # Render start command
└── README.md        # এই ফাইল
```
