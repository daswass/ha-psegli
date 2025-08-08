# PSEG Long Island Integration

This integration automatically fetches energy usage data from PSEG Long Island and updates Home Assistant's Energy Dashboard statistics.

## Features

- ✅ **Fully Automated Login** - No manual cookie management required
- ✅ **Automatic Cookie Refresh** - Handles expired cookies automatically
- ✅ **Energy Dashboard Integration** - Updates long-term statistics
- ✅ **Zero Manual Intervention** - Completely hands-off operation

## Setup

### 1. Install Playwright (Required)

**For Home Assistant Core/Docker:**

```bash
# SSH into your Home Assistant container
docker exec -it homeassistant bash

# Install Playwright and browsers
pip install playwright>=1.54.0
playwright install chromium
```

**For Home Assistant OS:**

```bash
# SSH into your Home Assistant OS
ssh root@your-ha-ip

# Install Playwright and browsers
pip install playwright>=1.54.0
playwright install chromium
```

**For Home Assistant Supervised:**

```bash
# SSH into your host system
ssh root@your-ha-ip

# Install Playwright and browsers
pip install playwright>=1.54.0
playwright install chromium
```

### 2. Add Credentials to secrets.yaml

Add your PSEG Long Island credentials to your `secrets.yaml` file:

```yaml
psegli_username: "your-email@example.com"
psegli_password: "your-password"
```

### 3. Install the Integration

1. Copy the `custom_components/psegli` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Add Integration**
4. Search for "PSEG Long Island" and add it

### 4. Installation Complete!

The integration will:

- Automatically log in using your credentials
- Handle reCAPTCHA automatically
- Refresh cookies when they expire
- Update energy statistics automatically

## How It Works

This integration uses advanced browser automation to:

1. **Automated Login** - Uses Playwright to simulate real browser interactions
2. **reCAPTCHA Bypass** - Handles invisible reCAPTCHA automatically
3. **Cookie Management** - Automatically refreshes expired authentication cookies
4. **Data Fetching** - Retrieves usage data and updates Home Assistant statistics

## Services

### Manual Statistics Update

You can manually trigger statistics updates:

```yaml
service: psegli.update_statistics
data:
  days_back: 7 # Optional: fetch data from 7 days ago
```

## Troubleshooting

### Playwright Installation Issues

If you see "Requirements for psegli not found: ['playwright>=1.54.0']":

1. **For Home Assistant Core/Docker:**

   ```bash
   docker exec -it homeassistant bash
   pip install playwright>=1.54.0
   playwright install chromium
   ```

2. **For Home Assistant OS:**

   ```bash
   ssh root@your-ha-ip
   pip install playwright>=1.54.0
   playwright install chromium
   ```

3. **For Home Assistant Supervised:**
   ```bash
   ssh root@your-ha-ip
   pip install playwright>=1.54.0
   playwright install chromium
   ```

### Credentials Not Found

- Ensure `psegli_username` and `psegli_password` are set in `secrets.yaml`
- Restart Home Assistant after updating secrets.yaml

### Login Failed

- Verify your PSEG Long Island credentials are correct
- Check that your account is not locked
- The integration will automatically retry

### No Data

- The integration updates statistics automatically
- Check the Energy Dashboard for your PSEG data
- Use the manual service to backfill historical data

## Technical Details

- **Browser Automation**: Uses Playwright for reliable login
- **reCAPTCHA Handling**: Simulates real mouse clicks to trigger invisible reCAPTCHA
- **Cookie Management**: Automatically refreshes expired authentication cookies
- **Statistics Integration**: Updates Home Assistant's long-term statistics API

## Support

For issues or questions, please open an issue on the GitHub repository.
