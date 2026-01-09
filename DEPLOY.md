# Fly.io Deployment Guide

এই গাইড আপনাকে Fly.io-তে আপনার Telegram Bot Listener deploy করতে সাহায্য করবে।

## Prerequisites

1. Fly.io account (https://fly.io)
2. Fly CLI installed (https://fly.io/docs/hands-on/install-flyctl/)
3. MongoDB Atlas account (remote MongoDB) অথবা অন্য কোনো remote MongoDB

## Step 1: Fly.io CLI Setup

```bash
# Fly.io login করুন
fly auth login

# Fly.io app তৈরি করুন (যদি এখনো না করে থাকেন)
fly launch
```

## Step 2: Environment Variables Set করুন

```bash
# Telegram API credentials
fly secrets set API_ID=37118739
fly secrets set API_HASH=d02baf67c4f5d2e0586236c24e1248d1

# Bot username
fly secrets set BOT_USERNAME=roboucbot

# MongoDB configuration (MongoDB Atlas URI ব্যবহার করুন)
fly secrets set MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
fly secrets set MONGODB_DATABASE=telegram_bot
fly secrets set MONGODB_COLLECTION=bot_messages

# Session directory (Fly.io volume mount point)
fly secrets set SESSION_DIR=/app/sessions
```

## Step 3: Volume তৈরি করুন (Session File Storage)

```bash
# Volume তৈরি করুন
fly volumes create telegram_session --size 1 --region bom
```

## Step 4: Deploy করুন

```bash
# Deploy করুন
fly deploy
```

## Step 5: Authentication Setup

Fly.io-তে প্রথমবার authentication করতে হলে:

1. **Local-এ authenticate করুন:**
   ```bash
   # Local-এ run করুন
   python app.py
   ```
   এটি একটি session file তৈরি করবে (`telegram_listener.session`)

2. **Session file upload করুন Fly.io volume-এ:**
   ```bash
   # Fly.io machine-এ SSH করুন
   fly ssh console
   
   # Session file copy করুন
   # আপনার local machine থেকে:
   fly ssh sftp shell
   # তারপর session file upload করুন
   ```

   অথবা:

   ```bash
   # Direct copy (local থেকে)
   fly ssh sftp shell
   put telegram_listener.session /app/sessions/telegram_listener.session
   ```

## Step 6: App Start করুন

```bash
# App status check করুন
fly status

# Logs দেখুন
fly logs

# App open করুন browser-এ
fly open
```

## Important Notes

1. **MongoDB:** Fly.io-তে local MongoDB নেই, তাই MongoDB Atlas বা অন্য remote MongoDB ব্যবহার করুন।

2. **Session File:** Session file persist করার জন্য Fly.io volume ব্যবহার করা হচ্ছে। প্রথমবার authentication local-এ করে session file upload করতে হবে।

3. **Port:** App automatically `PORT` environment variable ব্যবহার করবে (Fly.io automatically set করে)।

4. **Health Check:** `/health` endpoint available আছে app status check করার জন্য।

## Troubleshooting

### Authentication Error
- Session file সঠিকভাবে upload হয়েছে কিনা check করুন
- Session file path সঠিক কিনা verify করুন (`/app/sessions/telegram_listener.session`)

### MongoDB Connection Error
- MongoDB URI সঠিক কিনা check করুন
- MongoDB Atlas-এ IP whitelist check করুন (Fly.io IP allow করুন)

### App Not Starting
- Logs check করুন: `fly logs`
- Environment variables check করুন: `fly secrets list`

## Useful Commands

```bash
# App status
fly status

# View logs
fly logs

# SSH into machine
fly ssh console

# Restart app
fly apps restart

# Scale app
fly scale count 1

# View secrets
fly secrets list
```
