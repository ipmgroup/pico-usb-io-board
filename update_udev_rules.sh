#!/bin/bash

# =============================================================================
# DLN2 udev Rules Update Script
# Updates udev rules for better DLN2 module loading
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

UDEV_RULES_FILE="/etc/udev/rules.d/99-dln2.rules"
MODULE_RULES_FILE="/etc/udev/rules.d/99-dln2-modules.rules"

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

update_udev_rules() {
    log "Updating DLN2 udev rules..."
    
    # Update main rules file
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

    success "Main udev rules updated: $UDEV_RULES_FILE"

    # Create module loading rules
    cat > "$MODULE_RULES_FILE" << 'EOF'
# DLN2 Module loading rules
# Ensures all DLN2 interface modules are loaded when device is connected

ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="6170", RUN+="/bin/bash -c 'sleep 1; echo 1d50 6170 > /sys/bus/usb/drivers/dln2/new_id 2>/dev/null || true; modprobe gpio-dln2 2>/dev/null || true; modprobe i2c-dln2 2>/dev/null || true; modprobe spi-dln2 2>/dev/null || true; modprobe dln2-adc 2>/dev/null || true'"
EOF

    success "Module loading rules created: $MODULE_RULES_FILE"
}

reload_udev() {
    log "Reloading udev rules..."
    udevadm control --reload-rules
    udevadm trigger
    success "udev rules reloaded"
}

apply_to_connected_device() {
    log "Checking for connected DLN2 device..."
    
    if lsusb | grep -q "1d50:6170"; then
        log "DLN2 device found, applying new rules..."
        
        # Load base driver
        modprobe dln2 2>/dev/null || true
        
        # Bind device to driver
        echo "1d50 6170" > /sys/bus/usb/drivers/dln2/new_id 2>/dev/null || true
        
        sleep 2
        
        # Load interface modules
        modprobe gpio-dln2 2>/dev/null || true
        modprobe i2c-dln2 2>/dev/null || true  
        modprobe spi-dln2 2>/dev/null || true
        modprobe dln2-adc 2>/dev/null || true
        
        success "New rules applied to connected device"
    else
        log "No DLN2 device connected, rules will apply on next connection"
    fi
}

main() {
    echo -e "${BLUE}=== DLN2 udev Rules Update ===${NC}"
    echo
    
    check_root
    update_udev_rules
    reload_udev
    apply_to_connected_device
    
    echo
    echo -e "${GREEN}🎉 udev rules updated successfully!${NC}"
    echo -e "${YELLOW}📋 Reconnect your DLN2 device to test new rules${NC}"
    echo
}

main "$@"
