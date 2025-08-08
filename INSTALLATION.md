# PSEG Long Island Integration - Complete Installation Guide

This guide will walk you through installing both the **Automation Addon** and the **Main Integration** for PSEG Long Island using the new repository-based approach.

## 🎯 **What We're Installing**

1. **PSEG Long Island Automation Addon** - Handles automated login and reCAPTCHA
2. **PSEG Long Island Integration** - Fetches energy data and updates statistics

## 📋 **Prerequisites**

- Home Assistant OS, Core, or Supervised installation
- PSEG Long Island account credentials (username/email and password)
- Internet access for PSEG API calls
- Basic familiarity with Home Assistant

## 🚀 **Step 1: Install the Automation Addon**

### **1.1: Add the Custom Repository**

1. Go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the three dots menu (⋮) → **Repositories**
3. Add: `https://github.com/daswass/ha-psegli`
4. Click **Add**

### **1.2: Install the Addon**

1. Find **PSEG Long Island Automation** in the store
2. Click **Install**
3. Wait for installation to complete
4. Click **Start**

### **1.3: Verify Addon is Running**

- The addon should show **Running** status
- Check logs for any errors
- Verify port 8000 is available
- The addon provides a web interface at port 8000

## 🔌 **Step 2: Install the Main Integration**

### **2.1: Copy Integration Files**

SSH into your Home Assistant system and run:

```bash
# Copy the integration
cp -r /path/to/your/download/custom_components/psegli /config/custom_components/
```

**Alternative**: If you have the repository cloned locally, you can copy from there:

```bash
# From your local repository
cp -r custom_components/psegli /config/custom_components/
```

### **2.2: Restart Home Assistant**

- Go to **Settings** → **System** → **Restart**
- Click **Restart**
- Wait for restart to complete

## ⚙️ **Step 3: Add the Integration**

### **3.1: Add Integration**

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **PSEG Long Island**
4. Click on it

### **3.2: Configuration**

The integration will now show a proper configuration form:

- **Username/Email**: Enter your PSEG account email address
- **Password**: Enter your PSEG account password
- Click **Submit**

**Important**: Use your real PSEG credentials!

## ✅ **Step 4: Verification**

### **4.1: Check Integration Status**

- Go to **Settings** → **Devices & Services**
- Find **PSEG Long Island**
- Status should show **Loaded**

### **4.2: Check Addon Status**

- Go to **Settings** → **Add-ons**
- Find **PSEG Long Island Automation**
- Status should show **Running**

### **4.3: Check Logs**

- Go to **Settings** → **System** → **Logs**
- Look for PSEG-related entries
- Should see successful login and data fetching

## 🔍 **How It Works Now**

### **New Architecture Benefits**

1. **Simplified Setup**: No more `secrets.yaml` configuration
2. **User-Friendly**: Simple username/password form
3. **Automatic**: Addon handles all browser automation
4. **Secure**: Credentials stored in Home Assistant configuration
5. **Repository-Based**: Easy updates and installation

### **What Happens During Setup**

1. **User Input**: You enter PSEG credentials in the integration form
2. **Addon Communication**: Integration calls addon API to get fresh cookies
3. **Automated Login**: Addon uses Playwright to handle reCAPTCHA and login
4. **Cookie Provision**: Addon returns valid authentication cookies
5. **Data Fetching**: Integration uses cookies to call PSEG API
6. **Automatic Refresh**: Process repeats when cookies expire

## 🐛 **Troubleshooting**

### **Addon Installation Issues**

- **Repository Not Found**: Verify the URL is correct: `https://github.com/daswass/ha-psegli`
- **Installation Fails**: Check Home Assistant logs for errors
- **Port Conflicts**: Ensure port 8000 is available

### **Integration Setup Issues**

- **Form Not Showing**: Verify addon is running before adding integration
- **Configuration Errors**: Check Home Assistant logs for details
- **Credentials Rejected**: Verify PSEG account is active

### **Authentication Issues**

- **Login Fails**: Check addon logs for Playwright errors
- **reCAPTCHA Issues**: Verify addon can reach PSEG website
- **Account Locked**: Check if PSEG has locked your account

### **Data Not Updating**

- **API Errors**: Check integration logs for PSEG API issues
- **Cookie Issues**: Verify addon is providing valid cookies
- **Network Issues**: Check if PSEG website is accessible

## 🔧 **Advanced Configuration**

### **Addon Options**

The addon runs with default settings that work for most users. If you need to customize:

- **Port**: Default is 8000
- **Browser**: Uses Chromium with headless mode
- **Timeout**: 60 seconds for login process

### **Integration Options**

- **Scan Interval**: Default is 5 minutes
- **Statistics Update**: Automatic hourly updates
- **Error Handling**: Automatic retry with exponential backoff

## 📊 **What You Get**

### **Sensors**

- **Total Energy**: Cumulative energy consumption
- **Daily Usage**: Energy used today
- **Current Usage**: Real-time energy consumption
- **Temperature**: Current temperature (if available)

### **Energy Dashboard**

- **Hourly Data**: 15-minute interval energy usage
- **Daily Totals**: Aggregated daily consumption
- **Long-term Tracking**: Historical energy statistics
- **Cost Analysis**: Energy cost calculations (if rates available)

## 🚀 **Next Steps**

### **Automation Ideas**

```yaml
automation:
  - alias: "High Energy Usage Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.psegli_current_usage
      above: 10
    action:
      service: notify.mobile_app
      data:
        message: "High energy usage detected: {{ states('sensor.psegli_current_usage') }} kWh"
```

### **Custom Dashboards**

- Create energy monitoring dashboards
- Set up energy cost tracking
- Monitor peak usage times
- Track energy efficiency improvements

## 🆘 **Getting Help**

### **Where to Look**

1. **Home Assistant Logs**: Settings → System → Logs
2. **Addon Logs**: Settings → Add-ons → PSEG Long Island Automation → Logs
3. **Integration Logs**: Developer Tools → Services → Logs

### **Common Issues**

- **Addon not starting**: Check port conflicts and dependencies
- **Integration not loading**: Verify file permissions and restart HA
- **Authentication failures**: Check PSEG account status and credentials

### **Support Resources**

- **GitHub Issues**: [ha-psegli repository](https://github.com/daswass/ha-psegli)
- **Home Assistant Community**: [community.home-assistant.io](https://community.home-assistant.io)
- **Documentation**: This guide and the main README

---

**Note**: This new architecture makes the integration much more user-friendly than previous versions. The addon handles all the complex browser automation, while the integration focuses on data collection and presentation.
