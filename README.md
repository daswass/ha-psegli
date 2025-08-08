# PSEG Long Island Home Assistant Integration

A Home Assistant integration for PSEG Long Island that provides automated energy usage data collection and statistics updates using a dedicated automation addon.

## 🚀 **Architecture Overview**

This integration uses a **two-component approach**:

1. **PSEG Long Island Automation Addon**: Handles automated login, reCAPTCHA bypass, and cookie management
2. **PSEG Long Island Integration**: Lightweight component that fetches energy data using the addon's authentication

### **How It Works:**

1. **User Configuration**: Enter PSEG credentials in the integration setup
2. **Automated Login**: Addon uses Playwright to handle reCAPTCHA and login
3. **Cookie Management**: Addon provides fresh authentication cookies to the integration
4. **Data Retrieval**: Integration fetches energy usage data from PSEG API
5. **Automatic Refresh**: Cookies are automatically refreshed when they expire

## 📋 **Prerequisites**

- Home Assistant OS, Core, or Supervised installation
- PSEG Long Island account credentials (username/email and password)
- Internet access for PSEG API calls

## 🔧 **Installation**

### **Step 1: Install the Automation Addon**

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

3. **Verify the addon is running:**
   - Check that the addon shows "Running" status
   - The addon provides a web interface at port 8000

### **Step 2: Install the Integration**

1. **Copy the integration files:**

   ```bash
   # From your HA system
   cp -r custom_components/psegli /config/custom_components/
   ```

2. **Restart Home Assistant**

3. **Add the integration:**
   - Go to **Settings** → **Devices & Services**
   - Click **Add Integration**
   - Search for **PSEG Long Island**
   - Enter your PSEG username/email and password
   - Click **Submit**

## ⚙️ **Configuration**

### **Integration Setup**

The integration configuration is simple - just enter your PSEG credentials:

- **Username/Email**: Your PSEG account email address
- **Password**: Your PSEG account password

### **Automatic Operation**

Once configured, the integration will:

- Automatically log in to PSEG using the addon
- Handle reCAPTCHA challenges transparently
- Maintain authentication cookies automatically
- Fetch energy usage data every 5 minutes
- Update Home Assistant Energy Dashboard statistics

## 🎯 **Features**

- **🔐 Automated Authentication**: No manual cookie management needed
- **🤖 reCAPTCHA Bypass**: Uses Playwright for automated login
- **📊 Energy Statistics**: Updates Home Assistant Energy Dashboard
- **🔄 Automatic Refresh**: Handles cookie expiration seamlessly
- **⏱️ Real-time Data**: Hourly interval data from PSEG

## 🔍 **How It Works**

1. **Initial Setup**: User enters PSEG credentials in integration setup
2. **Addon Communication**: Integration calls addon API to get fresh cookies
3. **Automated Login**: Addon uses Playwright to handle reCAPTCHA and login
4. **Cookie Provision**: Addon returns valid authentication cookies
5. **Data Fetching**: Integration uses cookies to call PSEG API
6. **Automatic Refresh**: Process repeats when cookies expire

## 🐛 **Troubleshooting**

### **Addon Not Available**

- Check if addon is running in **Settings** → **Add-ons**
- Verify addon logs for errors
- Ensure port 8000 is available
- Check addon health at `/api/health`

### **Integration Setup Issues**

- Verify addon is running before adding integration
- Check Home Assistant logs for configuration errors
- Ensure PSEG credentials are correct
- Verify internet connectivity

### **Authentication Issues**

- Check addon logs for login failures
- Verify PSEG account is active and not locked
- Ensure reCAPTCHA is accessible from your network
- Check if PSEG has changed their login process

### **Data Not Updating**

- Check integration logs for API errors
- Verify addon is providing valid cookies
- Check PSEG website accessibility
- Verify integration is enabled and running

## 📊 **Data Structure**

The integration provides:

- **Hourly Energy Usage**: kWh consumption per hour
- **Daily Totals**: Aggregated daily consumption
- **Statistics**: Long-term energy tracking
- **Energy Dashboard**: Integration with HA Energy features

## 🆘 **Support**

- **Addon Issues**: Check addon logs in Home Assistant
- **Integration Issues**: Check Home Assistant logs
- **PSEG Issues**: Verify account status on PSEG website
- **GitHub Issues**: Report bugs at [ha-psegli repository](https://github.com/daswass/ha-psegli)

## 🚀 **Advanced Usage**

### **Manual Refresh**

```yaml
service: psegli.update_statistics
```

### **Addon API Endpoints**

The addon provides these endpoints:

- `GET /health` - Health check
- `POST /login` - Login with username/password
- `POST /login-form` - Login with form data

## 📝 **Changelog**

### **v2.0.0**

- **Major Architecture Change**: Now uses Home Assistant addon for automation
- **Simplified Setup**: No more manual cookie management
- **Automated reCAPTCHA**: Playwright handles all browser automation
- **Repository Installation**: Addon installs from custom repository
- **User-Friendly Configuration**: Simple username/password form
- **Automatic Cookie Refresh**: Seamless authentication management

### **v1.0.0**

- Initial release with manual cookie management
- Basic PSEG API integration
- Energy Dashboard integration

## 🤝 **Contributing**

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: This integration requires the PSEG Long Island Automation Addon to function. The addon handles all browser automation and reCAPTCHA challenges automatically, making the integration much more user-friendly than previous versions.
