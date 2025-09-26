#!/bin/bash

# =============================================================================
# Quick DLN2 System Check
# Fast verification that DLN2 setup is working correctly
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🔍 DLN2 System Quick Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if DLN2 device is connected
echo -e "${YELLOW}1. USB Device Detection:${NC}"
if lsusb | grep -q "1d50:6170"; then
    echo -e "   ${GREEN}✅ DLN2 device found (1d50:6170)${NC}"
    DLN2_FOUND=true
else
    echo -e "   ${RED}❌ DLN2 device not found${NC}"
    echo -e "   ${YELLOW}   → Check USB connection${NC}"
    DLN2_FOUND=false
fi
echo

# Check user groups
echo -e "${YELLOW}2. User Groups:${NC}"
USER_GROUPS=$(groups $USER)
REQUIRED_GROUPS=("dialout" "i2c" "spi" "gpio" "plugdev")
MISSING_GROUPS=()

for group in "${REQUIRED_GROUPS[@]}"; do
    if echo "$USER_GROUPS" | grep -q "\b$group\b"; then
        echo -e "   ${GREEN}✅ $group${NC}"
    else
        echo -e "   ${RED}❌ $group${NC}"
        MISSING_GROUPS+=("$group")
    fi
done

if [ ${#MISSING_GROUPS[@]} -gt 0 ]; then
    echo -e "   ${YELLOW}   → Missing groups: ${MISSING_GROUPS[*]}${NC}"
    echo -e "   ${YELLOW}   → Run setup script or logout/login${NC}"
fi
echo

# Function to check if I2C bus is DLN2
is_dln2_i2c_bus() {
    local bus_num=$1
    local i2c_dev_path="/sys/class/i2c-dev/i2c-$bus_num"
    
    if [ -d "$i2c_dev_path" ]; then
        local real_path=$(readlink -f "$i2c_dev_path")
        if [[ "$real_path" == *"dln2"* ]]; then
            return 0  # true
        fi
    fi
    return 1  # false
}

# Check DLN2 I2C buses
echo -e "${YELLOW}3. DLN2 I2C Buses:${NC}"
DLN2_I2C_COUNT=0
DLN2_I2C_BUSES=()

for bus in /dev/i2c-*; do
    if [ -c "$bus" ]; then
        BUS_NUM=$(basename "$bus" | sed 's/i2c-//')
        if is_dln2_i2c_bus "$BUS_NUM"; then
            DLN2_I2C_COUNT=$((DLN2_I2C_COUNT + 1))
            DLN2_I2C_BUSES+=("$BUS_NUM")
            echo -e "   ${BLUE}   → /dev/i2c-$BUS_NUM (DLN2)${NC}"
        fi
    fi
done

if [ "$DLN2_I2C_COUNT" -gt 0 ]; then
    echo -e "   ${GREEN}✅ Found $DLN2_I2C_COUNT DLN2 I2C bus(es)${NC}"
    
    # Show total I2C buses for reference
    TOTAL_I2C_BUSES=$(ls /dev/i2c-* 2>/dev/null | wc -l)
    SYSTEM_I2C_BUSES=$((TOTAL_I2C_BUSES - DLN2_I2C_COUNT))
    echo -e "   ${BLUE}   (Total I2C buses: $TOTAL_I2C_BUSES, System: $SYSTEM_I2C_BUSES, DLN2: $DLN2_I2C_COUNT)${NC}"
else
    echo -e "   ${RED}❌ No DLN2 I2C buses found${NC}"
    echo -e "   ${YELLOW}   → Check DLN2 connection and kernel modules${NC}"
    
    # Show system buses for debugging
    TOTAL_I2C_BUSES=$(ls /dev/i2c-* 2>/dev/null | wc -l)
    if [ "$TOTAL_I2C_BUSES" -gt 0 ]; then
        echo -e "   ${YELLOW}   → Found $TOTAL_I2C_BUSES system I2C buses (not DLN2)${NC}"
    fi
fi

# Update I2C_BUSES variable to reflect only DLN2 buses
I2C_BUSES=$DLN2_I2C_COUNT
echo

# Check udev rules
echo -e "${YELLOW}4. udev Rules:${NC}"
if [ -f "/etc/udev/rules.d/99-dln2.rules" ]; then
    echo -e "   ${GREEN}✅ DLN2 udev rules present${NC}"
else
    echo -e "   ${RED}❌ DLN2 udev rules missing${NC}"
    echo -e "   ${YELLOW}   → Run setup script as sudo${NC}"
fi
echo

# Check Python environment
echo -e "${YELLOW}5. Python Environment:${NC}"
if [ -f ".venv/bin/activate" ]; then
    echo -e "   ${GREEN}✅ Virtual environment exists${NC}"
    
    # Test Python packages
    source .venv/bin/activate 2>/dev/null
    if python -c "import smbus2" 2>/dev/null; then
        echo -e "   ${GREEN}✅ smbus2 package available${NC}"
    else
        echo -e "   ${RED}❌ smbus2 package missing${NC}"
        echo -e "   ${YELLOW}   → Run: pip install smbus2${NC}"
    fi
    
    if python -c "import serial" 2>/dev/null; then
        echo -e "   ${GREEN}✅ pyserial package available${NC}"
    else
        echo -e "   ${RED}❌ pyserial package missing${NC}"
        echo -e "   ${YELLOW}   → Run: pip install pyserial${NC}"
    fi
    deactivate 2>/dev/null
else
    echo -e "   ${RED}❌ Virtual environment missing${NC}"
    echo -e "   ${YELLOW}   → Run setup script${NC}"
fi
echo

# SSD1306 auto-configuration check
echo -e "${YELLOW}6. SSD1306 Configuration:${NC}"
if [ -f "ssd1306_config.py" ]; then
    echo -e "   ${GREEN}✅ Auto-configuration file exists${NC}"
    
    # Check if we can detect I2C bus and device
    if [ "$DLN2_FOUND" = true ] && [ "$I2C_BUSES" -gt 0 ]; then
        echo -e "   ${BLUE}   → Testing DLN2 I2C device detection...${NC}"
        source .venv/bin/activate 2>/dev/null
        if python -c "
import sys
sys.path.insert(0, '.')
try:
    from ssd1306_autodetect import SSD1306AutoConfig
    config = SSD1306AutoConfig()
    bus, addr = config.detect_display()
    print(f'   ${GREEN}✅ SSD1306 found on DLN2 I2C bus {bus}, address {addr:#x}${NC}')
except Exception as e:
    print(f'   ${YELLOW}⚠️  Auto-detection: {e}${NC}')
" 2>/dev/null; then
            :
        fi
        deactivate 2>/dev/null
    fi
else
    echo -e "   ${YELLOW}⚠️  Auto-configuration not available${NC}"
    echo -e "   ${YELLOW}   → Use test scripts manually${NC}"
fi
echo

# Overall status
echo -e "${BLUE}========================================${NC}"
if [ "$DLN2_FOUND" = true ] && [ ${#MISSING_GROUPS[@]} -eq 0 ] && [ "$I2C_BUSES" -gt 0 ]; then
    echo -e "${GREEN}🎉 System Status: READY${NC}"
    echo -e "${GREEN}   Your DLN2 setup is working correctly!${NC}"
    echo
    echo -e "${YELLOW}💡 Next steps:${NC}"
    echo -e "   ${BLUE}→ Connect SSD1306 display to DLN2 I2C pins${NC}"
    echo -e "   ${BLUE}→ Run: source .venv/bin/activate${NC}"
    echo -e "   ${BLUE}→ Test: python ssd1306/test_ssd1306_128x32.py${NC}"
else
    echo -e "${YELLOW}⚠️  System Status: NEEDS ATTENTION${NC}"
    echo -e "${YELLOW}   Some components need configuration${NC}"
    echo
    echo -e "${YELLOW}💡 Recommendations:${NC}"
    if [ "$DLN2_FOUND" = false ]; then
        echo -e "   ${BLUE}→ Connect DLN2 device via USB${NC}"
    fi
    if [ ${#MISSING_GROUPS[@]} -gt 0 ]; then
        echo -e "   ${BLUE}→ Logout and login to apply group changes${NC}"
    fi
    if [ "$I2C_BUSES" -eq 0 ]; then
        echo -e "   ${BLUE}→ Check DLN2 driver and I2C kernel modules${NC}"
    fi
    echo -e "   ${BLUE}→ Run setup script if needed: sudo ./setup_dln2_system.sh${NC}"
fi
echo -e "${BLUE}========================================${NC}"
