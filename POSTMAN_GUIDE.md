# Postman Guide - Telegram Bot API Testing

এই guide আপনাকে Postman দিয়ে API test করতে সাহায্য করবে।

## API Base URL
```
https://tg-bot-lisener.fly.dev
```

## 1. Health Check (API Status)

### Request
- **Method:** `GET`
- **URL:** `https://tg-bot-lisener.fly.dev/health`
- **Headers:** None required

### Expected Response
```json
{
  "status": "ok",
  "bot_initialized": true,
  "listener_running": true
}
```

### Postman Steps:
1. Postman open করুন
2. New Request create করুন
3. Method: `GET` select করুন
4. URL: `https://tg-bot-lisener.fly.dev/health` দিন
5. Send button click করুন

---

## 2. Send Command

### Request (POST - Recommended)
- **Method:** `POST`
- **URL:** `https://tg-bot-lisener.fly.dev/api/send`
- **Headers:**
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
  ```json
  {
    "command": "Krate"
  }
  ```

### Request (GET - Alternative)
- **Method:** `GET`
- **URL:** `https://tg-bot-lisener.fly.dev/api/send?command=Krate`

### Postman Steps (POST):
1. New Request create করুন
2. Method: `POST` select করুন
3. URL: `https://tg-bot-lisener.fly.dev/api/send` দিন
4. **Headers tab:**
   - Key: `Content-Type`
   - Value: `application/json`
5. **Body tab:**
   - Select: `raw`
   - Dropdown: `JSON` select করুন
   - Body-তে এই JSON paste করুন:
     ```json
     {
       "command": "Krate"
     }
     ```
6. Send button click করুন

### Expected Response (Success):
```json
{
  "success": true,
  "command": "Krate",
  "sent_message_id": 12345,
  "response": {
    "message_id": 12346,
    "text": "Bot response here...",
    "date": "2025-01-15T10:30:00",
    "raw_data": {...}
  }
}
```

### Possible Errors:
- **503 Service Unavailable:** Bot listener not initialized
  ```json
  {
    "success": false,
    "error": "Bot listener not initialized. Please wait a moment and try again."
  }
  ```
- **400 Bad Request:** Command missing
  ```json
  {
    "success": false,
    "error": "Command parameter is required"
  }
  ```

---

## 3. Send Raw Message

### Request (POST - Recommended)
- **Method:** `POST`
- **URL:** `https://tg-bot-lisener.fly.dev/api/send-message-raw`
- **Headers:**
  ```
  Content-Type: application/json
  ```
- **Body (raw JSON):**
  ```json
  {
    "prefix": "ktp",
    "uid": "123456789",
    "diamonds": "100"
  }
  ```

### Request (GET - Alternative)
- **Method:** `GET`
- **URL:** `https://tg-bot-lisener.fly.dev/api/send-message-raw?prefix=ktp&uid=123456789&diamonds=100`

### Postman Steps (POST):
1. New Request create করুন
2. Method: `POST` select করুন
3. URL: `https://tg-bot-lisener.fly.dev/api/send-message-raw` দিন
4. **Headers tab:**
   - Key: `Content-Type`
   - Value: `application/json`
5. **Body tab:**
   - Select: `raw`
   - Dropdown: `JSON` select করুন
   - Body-তে এই JSON paste করুন:
     ```json
     {
       "prefix": "ktp",
       "uid": "123456789",
       "diamonds": "100"
     }
     ```
6. Send button click করুন

### Expected Response (Success):
```json
{
  "success": true,
  "status": "success",
  "uid": "123456789",
  "usedUc": [
    "BDMB-S-S-02536618 5494-2393-2291-4243"
  ]
}
```

### Expected Response (Failed):
```json
{
  "success": false,
  "status": "failed",
  "uid": "123456789"
}
```

---

## Troubleshooting

### 1. CORS Error
যদি CORS error পান:
- Postman-এ CORS issue হয় না (browser-এ হয়)
- যদি browser-এ test করেন, তাহলে CORS headers check করুন

### 2. 503 Service Unavailable
- Bot listener initialize হয়নি
- কিছুক্ষণ wait করুন এবং আবার try করুন
- Health check করুন: `GET /health`

### 3. Connection Error
- API URL সঠিক কিনা check করুন: `https://tg-bot-lisener.fly.dev`
- Internet connection check করুন
- Fly.io app running আছে কিনা check করুন

### 4. Timeout
- API response নিতে 15-30 seconds লাগতে পারে
- Postman-এ timeout increase করুন (Settings → General → Request timeout)

---

## Postman Collection (Import করার জন্য)

Postman collection import করতে পারেন:

1. Postman open করুন
2. Import button click করুন
3. Raw text tab select করুন
4. এই JSON paste করুন:

```json
{
  "info": {
    "name": "Telegram Bot API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "https://tg-bot-lisener.fly.dev/health",
          "protocol": "https",
          "host": ["tg-bot-lisener", "fly", "dev"],
          "path": ["health"]
        }
      }
    },
    {
      "name": "Send Command",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"command\": \"Krate\"\n}",
          "options": {
            "raw": {
              "language": "json"
            }
          }
        },
        "url": {
          "raw": "https://tg-bot-lisener.fly.dev/api/send",
          "protocol": "https",
          "host": ["tg-bot-lisener", "fly", "dev"],
          "path": ["api", "send"]
        }
      }
    },
    {
      "name": "Send Raw Message",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"prefix\": \"ktp\",\n  \"uid\": \"123456789\",\n  \"diamonds\": \"100\"\n}",
          "options": {
            "raw": {
              "language": "json"
            }
          }
        },
        "url": {
          "raw": "https://tg-bot-lisener.fly.dev/api/send-message-raw",
          "protocol": "https",
          "host": ["tg-bot-lisener", "fly", "dev"],
          "path": ["api", "send-message-raw"]
        }
      }
    }
  ]
}
```

---

## Quick Test Checklist

1. ✅ Health Check: `GET https://tg-bot-lisener.fly.dev/health`
2. ✅ Send Command: `POST https://tg-bot-lisener.fly.dev/api/send` with `{"command": "Krate"}`
3. ✅ Send Raw Message: `POST https://tg-bot-lisener.fly.dev/api/send-message-raw` with `{"prefix": "ktp", "uid": "123", "diamonds": "100"}`

---

## Notes

- সব requests HTTPS ব্যবহার করে
- POST requests-এর জন্য `Content-Type: application/json` header প্রয়োজন
- Response time 10-30 seconds হতে পারে (bot response wait করার জন্য)
- Error হলে response-এ `success: false` এবং `error` field থাকবে
