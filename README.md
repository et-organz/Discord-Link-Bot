# Discord Link & Media Tracker Bot

A feature-rich Discord bot that tracks links, images, GIFs, and videos posted in your server, takes links from social media sites such as Instragram, TikTok, X, and YouTube Shorts and embeds the videos, provides reaction-based rankings, supports media contests, and allows users to create GIFs from YouTube videos. 

---

## ✨ Features

- `/top_posts`: Shows top posts (links, images, GIFs, videos) based on reaction count.
- `/top_users`: Shows users with the most unique reactors.
- `/top_domain`: Displays the most frequently shared domain.
- `/makegif`: Converts a YouTube clip into a GIF.
- `/contest`: Shows weekly or monthly contest winners.
- `/help`: Lists all bot commands.

---

## 🔐 Permissions

- All commands **except** `/makegif` are restricted to server moderators.
- Moderators are identified by any of the following:
  - Administrator permission
  - Manage Messages permission
  - Any role containing "mod" or "admin" in the name (case-insensitive)

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/et-organz/Discord-Link-Bot
cd discord-link-bot
```

### 2. Install dependencies
```
pip install -r requirements.txt
```

### 3. Set up environment variables
Create a .env file and add your bot token:
```
API_KEY=your_discord_bot_token_here
```