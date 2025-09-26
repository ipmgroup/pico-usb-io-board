# DLN2 System Setup Guide

This repository includes automated setup scripts for configuring your system to work with the Raspberry Pi Pico USB I/O Board (DLN2 compatible device).

## 🚀 Quick Start

### 1. Run System Setup (One-time)
```bash
sudo ./setup_dln2_system.sh
```

This script will:
- Install required system packages
- Add your user to necessary groups  
- Configure udev rules for DLN2 device access
- Set up I2C kernel modules
- Create Python virtual environment with required packages
- Generate helper scripts and documentation

### 2. Logout and Login
**Important:** After running the setup script, you must logout and login again (or reboot) for group membership changes to take effect.

### 3. Verify Setup
```bash
./quick_check.sh
```

This will check:
- DLN2 device detection
- User group membership
- I2C bus availability 
- udev rules configuration
- Python environment and packages
- SSD1306 auto-detection (if connected)

## 📋 What Gets Installed

### System Packages:
- **Development tools**: `build-essential`, `cmake`, `gcc-arm-none-eabi`
- **Python**: `python3`, `python3-pip`, `python3-venv`  
- **Hardware tools**: `i2c-tools`, `udev`
- **Version control**: `git`

### User Groups:
Your user will be added to these groups for hardware access:
- `dialout` - USB serial device access
- `i2c` - I2C device access
- `spi` - SPI device access  
- `gpio` - GPIO access
- `plugdev` - USB device access

### udev Rules:
Creates `/etc/udev/rules.d/99-dln2.rules` with permissions for:
- DLN2 device (VID:PID = 1d50:6170)
- Dynamically created I2C buses
- SPI devices
- GPIO devices  
- USB serial ports (CDC-ACM)

### Python Environment:
- Virtual environment in `.venv/`
- Required packages: `smbus2`, `pyserial`

## 🔧 Usage Examples

### Basic Device Check:
```bash
# Quick system verification
./quick_check.sh

# Check USB devices
lsusb | grep 1d50:6170

# List I2C buses  
ls -la /dev/i2c-*

# Scan for I2C devices
./scan_i2c.sh
```

### Python Development:
```bash
# Activate virtual environment
source .venv/bin/activate

# Run SSD1306 tests
cd ssd1306/
python test_ssd1306_128x32.py

# Auto-detect display and test
python auto_detect_ssd1306.py
```

### I2C Communication:
```bash  
# Scan DLN2 I2C bus for devices
i2cdetect -y -r 15

# Read from SSD1306 at address 0x3c on DLN2 bus
i2cget -y 15 0x3c

# Manual I2C operations
source .venv/bin/activate
python -c "
import smbus2
bus = smbus2.SMBus(15)  # Use DLN2 bus number (typically 15)
data = bus.read_byte(0x3c)  # Read from SSD1306
print(f'Device response: {data:#x}')
"
```

## 📁 Generated Files

After running the setup script, you'll find:

### Helper Scripts:
- `quick_check.sh` - DLN2 device verification script
- `scan_i2c.sh` - I2C bus scanning utility  
- `run_ssd1306_demos.sh` - SSD1306 display demonstration runner

### Documentation:
- `SETUP_README.md` - Auto-generated setup information (created by setup script)
- `dln2_setup.log` - Setup process log file
- This `INSTALL.md` - Complete setup and usage guide

### Configuration:
- `.venv/` - Python virtual environment for isolated package management
- `dln2_setup.log` - Detailed setup process log with timestamps

## ⚠️ Troubleshooting

### Device Not Found:
```bash
# Check USB connection
lsusb | grep -i dln2

# Check kernel messages  
dmesg | grep -i usb | tail -20

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Permission Issues:
```bash  
# Check current groups
groups

# Verify udev rules
ls -la /etc/udev/rules.d/99-dln2.rules

# Test device permissions
ls -la /dev/i2c-*
```

### I2C Problems:
```bash
# Load I2C modules manually
sudo modprobe i2c-dev

# Check module loading
lsmod | grep i2c

# Verify I2C bus permissions
ls -la /dev/i2c-* 
```

### Python Issues:
```bash
# Recreate virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install smbus2 pyserial

# Test imports
python -c "import smbus2; print('OK')"
```

## 🎯 Hardware Setup

### DLN2 Device:
- Connect via USB-C cable
- Device should enumerate as VID:PID = 1d50:6170
- Creates one DLN2 I2C bus (typically i2c-15) among system buses

### SSD1306 Display Connection:
- **VCC** → 3.3V or 5V
- **GND** → Ground  
- **SDA** → I2C Data (DLN2 I2C bus, typically i2c-15)
- **SCL** → I2C Clock (same bus as SDA)
- **Address**: Usually 0x3C or 0x3D

### Supported Features:
- **Display**: SSD1306 128x32 OLED with dual colors
- **I2C**: Multiple buses, auto-detection
- **Auto-config**: Dynamic bus/address detection
- **USB Serial**: CDC-ACM for debugging

## 📊 System Requirements

- **OS**: Ubuntu 20.04+ or Debian 11+
- **Kernel**: 5.4+ (for DLN2 driver support)
- **USB**: USB 2.0+ port
- **Python**: 3.8+
- **Disk**: ~500MB for tools and environment

## 🔄 Updates

To update the system configuration:
```bash
# Pull latest changes
git pull

# Re-run setup if needed  
sudo ./setup_dln2_system.sh

# Verify configuration
./quick_check.sh
```

---

## 📞 Support

If you encounter issues:

1. **Run diagnostics**: `./quick_check.sh`
2. **Check logs**: `/tmp/dln2_setup.log` 
3. **Verify hardware**: Ensure DLN2 device is connected
4. **Test manually**: Use `lsusb`, `i2cdetect`, etc.
5. **Restart services**: Logout/login or reboot

The setup scripts are idempotent and safe to run multiple times.

Happy coding with your DLN2 device! 🚀
