# PSEG Long Island Automation Addon

This Home Assistant addon provides automated login services for PSEG Long Island using Playwright. It runs in its own container and exposes a web API for cookie generation.

**Version**: 2.1.2

## Features

- 🚀 **Automated Login**: Uses Playwright to handle reCAPTCHA and login
- 🔐 **Cookie Generation**: Returns fresh authentication cookies
- 🌐 **Web API**: Simple HTTP endpoints for integration use
- 🐳 **Docker-based**: Runs in isolated container with all dependencies
- 📱 **Home Assistant Integration**: Works seamlessly with PSEG Long Island integration

## Installation

### **Option 1: Repository Installation (Recommended)**

1. **Add the custom repository:**

   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click the three dots menu (⋮) → **Repositories**
   - Add: `https://github.com/daswass/ha-psegli`
   - Click **Add**

2. **Install the addon:**
   - Find **PSEG Long Island Automation** in the store
   - Click **Install**
   - Wait for installation to complete
   - Click **Start**

### **Option 2: Local Installation**

1. **Copy to Addons Directory**: Copy this folder to your Home Assistant `addons` directory
2. **Install Addon**: Go to Settings → Add-ons → Add-on Store → Local Add-ons
3. **Start Addon**: Click "Install" then "Start"

## API Endpoints

### Health Check

```
GET /health
```

### Login (JSON)

```
POST /login
Content-Type: application/json

{
  "username": "your_email@example.com",
  "password": "your_password"
}
```

### Login (Form Data)

```
POST /login-form
Content-Type: application/x-www-form-urlencoded

username=your_email@example.com&password=your_password
```

## Response Format

```json
{
  "success": true,
  "cookies": {
    "ASP.NET_SessionId": "abc123...",
    "__RequestVerificationToken": "xyz789...",
    "other_cookies": "..."
  }
}
```

## Integration Usage

The PSEG Long Island integration will automatically use this addon when available. No additional configuration needed.

## Troubleshooting

- **Port Conflicts**: Ensure port 8000 is available
- **Browser Issues**: Check addon logs for Playwright errors
- **Network Issues**: Verify addon can reach PSEG website

## Development

To build locally:

```bash
docker build -t psegli-automation .
docker run -p 8000:8000 psegli-automation
```
