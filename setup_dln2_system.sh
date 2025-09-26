#!/bin/bash

# =============================================================================
# DLN2 System Setup Script
# Automated setup for Raspberry Pi Pico USB I/O Board (DLN2 compatible)
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
UDEV_RULES_FILE="/etc/udev/rules.d/99-dln2.rules"
LOG_FILE="$SCRIPT_DIR/dln2_setup.log"

# Functions
init_logging() {
    # Create log file with correct permissions in script directory
    touch "$LOG_FILE"
    chown "$USER_NAME:$USER_NAME" "$LOG_FILE"
}

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
    
    if [[ -z "$USER_NAME" ]]; then
        error "Could not determine the user name"
    fi
    
    log "Running as root for user: $USER_NAME"
}

check_system() {
    log "Checking system compatibility..."
    
    # Check if it's a Debian/Ubuntu based system
    if ! command -v apt &> /dev/null; then
        error "This script is designed for Debian/Ubuntu based systems"
    fi
    
    # Check kernel version
    KERNEL_VERSION=$(uname -r)
    log "Kernel version: $KERNEL_VERSION"
    
    success "System compatibility check passed"
}

update_system() {
    log "Updating system packages..."
    apt update > "$LOG_FILE" 2>&1
    success "System packages updated"
}

install_dependencies() {
    log "Installing required packages..."
    
    PACKAGES=(
        "python3"
        "python3-pip" 
        "python3-venv"
        "i2c-tools"
        "udev"
        "build-essential"
        "git"
        "cmake"
        "gcc-arm-none-eabi"
        "libnewlib-arm-none-eabi"
        "libstdc++-arm-none-eabi-newlib"
    )
    
    for package in "${PACKAGES[@]}"; do
        log "Installing $package..."
        apt install -y "$package" >> "$LOG_FILE" 2>&1
        success "$package installed"
    done
}

setup_user_groups() {
    log "Setting up user groups for hardware access..."
    
    # Groups needed for DLN2 and I2C access
    GROUPS=("dialout" "i2c" "spi" "gpio" "plugdev")
    
    for group in "${GROUPS[@]}"; do
        # Create group if it doesn't exist
        if ! getent group "$group" > /dev/null 2>&1; then
            log "Creating group: $group"
            groupadd "$group"
        fi
        
        # Add user to group
        log "Adding user $USER_NAME to group $group"
        usermod -a -G "$group" "$USER_NAME"
        success "User added to group: $group"
    done
}

create_udev_rules() {
    log "Creating udev rules for DLN2 device..."
    
    cat > "$UDEV_RULES_FILE" << 'EOF'
# DLN2 USB-I2C/SPI/GPIO adapter rules
# Raspberry Pi Pico USB I/O Board (DLN2 compatible)

# Main DLN2 device with driver binding
SUBSYSTEM=="usb", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="6170", MODE="0666", GROUP="plugdev", TAG+="uaccess"

# I2C devices created by DLN2
KERNEL=="i2c-[0-9]*", ACTION=="add", PROGRAM="/bin/sh -c 'echo %k | grep -q i2c && echo 1 || echo 0'", RESULT=="1", GROUP="i2c", MODE="0664"

# SPI devices created by DLN2  
SUBSYSTEM=="spidev", GROUP="spi", MODE="0664"

# GPIO devices
SUBSYSTEM=="gpio", GROUP="gpio", MODE="0664"

# USB serial ports (CDC-ACM)
KERNEL=="ttyACM*", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="6170", MODE="0666", GROUP="dialout"

# DLN2 driver loading and module binding
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="6170", RUN+="/bin/bash -c 'modprobe dln2; echo 1d50 6170 > /sys/bus/usb/drivers/dln2/new_id; modprobe gpio-dln2; modprobe i2c-dln2; modprobe spi-dln2; modprobe dln2-adc'"

# Alternative rules file for explicit module loading
EOF

    # Create additional udev rules file for module loading
    cat > "/etc/udev/rules.d/99-dln2-modules.rules" << 'EOF'
# DLN2 Module loading rules
# Ensures all DLN2 interface modules are loaded when device is connected

ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="6170", RUN+="/bin/bash -c 'sleep 1; echo 1d50 6170 > /sys/bus/usb/drivers/dln2/new_id 2>/dev/null || true; modprobe gpio-dln2 2>/dev/null || true; modprobe i2c-dln2 2>/dev/null || true; modprobe spi-dln2 2>/dev/null || true; modprobe dln2-adc 2>/dev/null || true'"
EOF

    success "udev rules created: $UDEV_RULES_FILE"
    success "module loading rules created: /etc/udev/rules.d/99-dln2-modules.rules"
}

reload_udev() {
    log "Reloading udev rules..."
    udevadm control --reload-rules
    udevadm trigger
    success "udev rules reloaded"
}

enable_i2c() {
    log "Checking I2C kernel modules..."
    
    # Load I2C modules
    if ! lsmod | grep -q "i2c_dev"; then
        log "Loading i2c-dev module..."
        modprobe i2c-dev
    fi
    
    # Add modules to load at boot
    if ! grep -q "i2c-dev" /etc/modules; then
        echo "i2c-dev" >> /etc/modules
        log "Added i2c-dev to /etc/modules"
    fi
    
    success "I2C modules configured"
}

setup_python_environment() {
    log "Setting up Python environment for user $USER_NAME..."
    
    # Switch to user context for Python setup
    sudo -u "$USER_NAME" bash << 'EOF'
# Create virtual environment in project directory
cd "$SCRIPT_DIR"
if [[ ! -d ".venv" ]]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate and install packages
source .venv/bin/activate
echo "Installing Python packages..."
pip install --upgrade pip
pip install smbus2 pyserial

echo "Python environment setup completed"
EOF

    success "Python environment configured"
}

create_helper_scripts() {
    log "Creating helper scripts..."
    
    # Device detection script
    cat > "$SCRIPT_DIR/check_dln2.sh" << 'EOF'
#!/bin/bash
echo "=== DLN2 Device Detection ==="
echo

echo "🔍 USB Devices:"
lsusb | grep -i "1d50:6170" || echo "❌ DLN2 device not found"
echo

echo "🔍 I2C Buses:"
ls -la /dev/i2c-* 2>/dev/null || echo "❌ No I2C buses found"
echo

echo "🔍 SPI Devices:"
ls -la /dev/spidev* 2>/dev/null || echo "ℹ️  No SPI devices found (created dynamically by DLN2)"
echo

echo "🔍 User Groups:"
groups $USER | tr ' ' '\n' | grep -E "(dialout|i2c|spi|gpio|plugdev)" | sed 's/^/✅ /'
echo

echo "🔍 DLN2 Drivers:"
if lsmod | grep -q "dln2"; then
    echo "✅ DLN2 modules loaded:"
    lsmod | grep dln2 | sed 's/^/  /'
else
    echo "❌ DLN2 modules not loaded"
fi
echo

echo "🔍 Python Environment:"
if [[ -f ".venv/bin/activate" ]]; then
    echo "✅ Virtual environment exists"
    source .venv/bin/activate
    python -c "import smbus2; print('✅ smbus2 available')" 2>/dev/null || echo "❌ smbus2 not available"
    deactivate
else
    echo "❌ Virtual environment not found"
fi
EOF

    chmod +x "$SCRIPT_DIR/check_dln2.sh"
    chown "$USER_NAME:$USER_NAME" "$SCRIPT_DIR/check_dln2.sh"
    
    # I2C scan script
    cat > "$SCRIPT_DIR/scan_i2c.sh" << 'EOF'
#!/bin/bash
echo "=== I2C Bus Scanner ==="
echo

if command -v i2cdetect >/dev/null 2>&1; then
    for i2cbus in /dev/i2c-*; do
        if [[ -c "$i2cbus" ]]; then
            bus_num=$(basename "$i2cbus" | sed 's/i2c-//')
            echo "🔍 Scanning I2C bus $bus_num:"
            i2cdetect -y "$bus_num"
            echo
        fi
    done
else
    echo "❌ i2c-tools not installed"
fi
EOF

    chmod +x "$SCRIPT_DIR/scan_i2c.sh" 
    chown "$USER_NAME:$USER_NAME" "$SCRIPT_DIR/scan_i2c.sh"
    
    success "Helper scripts created"
}

create_readme() {
    log "Creating setup documentation..."
    
    cat > "$SCRIPT_DIR/SETUP_README.md" << 'EOF'
# DLN2 System Setup

This system has been configured for DLN2 USB I/O Board support.

## ✅ What was installed:

### System Packages:
- Python 3 with pip and venv
- I2C tools (i2cdetect, i2cget, i2cset)
- Build tools (gcc-arm-none-eabi, cmake)
- Git and development tools

### User Groups:
Your user has been added to these groups:
- `dialout` - for USB serial access
- `i2c` - for I2C device access  
- `spi` - for SPI device access
- `gpio` - for GPIO access
- `plugdev` - for USB device access

### udev Rules:
- DLN2 device (1d50:6170) permissions configured
- Automatic I2C/SPI/GPIO device permissions
- USB serial port access enabled
- Automatic driver binding and module loading
- Enhanced module loading for all DLN2 interfaces

### Python Environment:
- Virtual environment created in `.venv/`
- Required packages installed: `smbus2`, `pyserial`

## 🔧 Usage:

### Check DLN2 Status:
```bash
./check_dln2.sh
```

### Scan I2C Buses:
```bash
./scan_i2c.sh
```

### Activate Python Environment:
```bash
source .venv/bin/activate
```

### Run SSD1306 Tests:
```bash
source .venv/bin/activate
cd ssd1306/
python test_ssd1306_128x32.py
```

## ⚠️ Important Notes:

1. **Logout and login again** for group changes to take effect
2. Connect your DLN2 device via USB
3. The device should appear as multiple I2C buses
4. SSD1306 display should be connected to I2C address 0x3C

## 🔍 Troubleshooting:

- If device not detected: check USB connection and run `lsusb`
- If I2C not working: check groups with `groups` command
- If Python imports fail: activate virtual environment first
- For permission issues: check udev rules with `udevadm info`

Enjoy your DLN2 setup! 🚀
EOF

    chown "$USER_NAME:$USER_NAME" "$SCRIPT_DIR/SETUP_README.md"
    success "Documentation created"
}

print_final_instructions() {
    echo
    echo "========================================"
    echo -e "${GREEN}🎉 DLN2 System Setup Complete!${NC}"
    echo "========================================"
    echo
    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo "1. Logout and login again (or reboot) for group changes"
    echo "2. Connect your DLN2 device via USB"
    echo "3. Run: ./check_dln2.sh to verify setup"
    echo "4. Test I2C: ./scan_i2c.sh"
    echo
    echo -e "${BLUE}📁 Files created:${NC}"
    echo "- $UDEV_RULES_FILE"
    echo "- /etc/udev/rules.d/99-dln2-modules.rules"
    echo "- $SCRIPT_DIR/check_dln2.sh"
    echo "- $SCRIPT_DIR/scan_i2c.sh" 
    echo "- $SCRIPT_DIR/SETUP_README.md"
    echo "- $SCRIPT_DIR/.venv/ (Python environment)"
    echo
    echo -e "${GREEN}✅ Log file: $LOG_FILE${NC}"
    echo
}

# Main execution
main() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} Starting DLN2 system setup..."
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} Script directory: $SCRIPT_DIR"
    
    check_root
    init_logging
    
    log "DLN2 system setup initialized"
    check_system
    update_system
    install_dependencies
    setup_user_groups
    create_udev_rules
    reload_udev
    enable_i2c
    setup_python_environment
    create_helper_scripts
    create_readme
    
    print_final_instructions
    
    success "DLN2 system setup completed successfully!"
}

# Run main function
main "$@"
