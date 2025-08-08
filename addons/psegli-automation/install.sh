#!/bin/bash
# Installation script for PSEG Long Island Automation Addon

echo "🚀 Installing PSEG Long Island Automation Addon..."

# Check if we're in the right directory
if [ ! -f "config.yaml" ]; then
    echo "❌ Error: Please run this script from the addon directory"
    exit 1
fi

# Copy to Home Assistant addons directory
ADDON_DIR="/config/addons/local/psegli-automation"

echo "📁 Creating addon directory..."
mkdir -p "$ADDON_DIR"

echo "📋 Copying addon files..."
cp -r . "$ADDON_DIR/"

echo "🔧 Setting permissions..."
chmod +x "$ADDON_DIR/install.sh"

echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Go to Home Assistant → Settings → Add-ons → Add-on Store"
echo "2. Click on 'Local Add-ons'"
echo "3. Find 'PSEG Long Island Automation' and click 'Install'"
echo "4. Start the addon"
echo ""
echo "The PSEG Long Island integration will automatically use this addon!"
