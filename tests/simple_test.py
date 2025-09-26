#!/usr/bin/env python3
"""
Simple test to check DLN2 device connection and functionality
"""
import sys
from pathlib import Path
import subprocess
import re

def check_dln2_usb():
    """Check if DLN2 device is connected via USB"""
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if '1d50:6170' in result.stdout:
            print("✅ DLN2 USB device found!")
            print(f"   {[line for line in result.stdout.split('\\n') if '1d50:6170' in line][0].strip()}")
            return True
        else:
            print("❌ DLN2 USB device not found")
            return False
    except Exception as e:
        print(f"❌ Error checking USB: {e}")
        return False

def check_dln2_module():
    """Check if dln2 module is loaded"""
    try:
        result = subprocess.run(['lsmod'], capture_output=True, text=True)
        if 'dln2' in result.stdout:
            print("✅ dln2 module loaded!")
            return True
        else:
            print("❌ dln2 module not loaded")
            return False
    except Exception as e:
        print(f"❌ Error checking module: {e}")
        return False

def check_gpio_chips():
    """Check available GPIO chips"""
    try:
        result = subprocess.run(['gpiodetect'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ GPIO chips available:")
            for line in result.stdout.strip().split('\\n'):
                if line:
                    print(f"   {line}")
            
            # Look for DLN2 GPIO chip
            if 'dln2' in result.stdout.lower():
                print("✅ Found DLN2 GPIO chip!")
                return True
            else:
                print("❓ DLN2 GPIO chip not found in list")
                return False
        else:
            print(f"❌ gpiodetect returned error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ gpiodetect not found. Install gpio-utils:")
        print("   sudo apt install gpiod")
        return False
    except Exception as e:
        print(f"❌ Error checking GPIO: {e}")
        return False

def check_spi_devices():
    """Check SPI devices"""
    spi_path = Path('/sys/class/spi_master')
    if spi_path.exists():
        spi_devices = list(spi_path.iterdir())
        if spi_devices:
            print(f"✅ Found SPI master devices: {len(spi_devices)}")
            for device in spi_devices:
                try:
                    modalias_path = device / 'device' / 'modalias'
                    if modalias_path.exists():
                        with modalias_path.open() as f:
                            modalias = f.read().strip()
                            print(f"   {device.name}: {modalias}")
                            if 'dln2' in modalias:
                                print("   ✅ This is a DLN2 SPI device!")
                except Exception as e:
                    print(f"   ❌ Error reading {device.name}: {e}")
            return True
        else:
            print("❌ No SPI master devices found")
            return False
    else:
        print("❌ /sys/class/spi_master does not exist")
        return False

def check_i2c_devices():
    """Check I2C devices"""
    # Check /sys/class/i2c-dev (modern path)
    i2c_dev_path = Path('/sys/class/i2c-dev')
    if i2c_dev_path.exists():
        i2c_devices = list(i2c_dev_path.iterdir())
        if i2c_devices:
            print(f"✅ Found I2C devices: {len(i2c_devices)}")
            dln2_found = False
            for device in i2c_devices:
                try:
                    # Read real device path
                    real_path = device.resolve()
                    device_path_str = str(real_path)
                    print(f"   {device.name}: {device_path_str}")
                    if 'dln2-i2c' in device_path_str:
                        print("   ✅ This is a DLN2 I2C device!")
                        dln2_found = True
                except Exception as e:
                    print(f"   ❌ Error reading {device.name}: {e}")
            
            if dln2_found:
                return True
            else:
                print("❓ DLN2 I2C device not found")
                return False
        else:
            print("❌ No I2C devices found")
            return False
    else:
        print("❌ /sys/class/i2c-dev does not exist")
        return False

def check_adc_devices():
    """Check ADC devices"""
    iio_path = Path('/sys/bus/iio/devices')
    if iio_path.exists():
        iio_devices = list(iio_path.iterdir())
        if iio_devices:
            print(f"✅ Found IIO devices: {len(iio_devices)}")
            dln2_adc_found = False
            for device in iio_devices:
                if device.name.startswith('iio:device'):
                    try:
                        name_path = device / 'name'
                        if name_path.exists():
                            with name_path.open() as f:
                                name = f.read().strip()
                                print(f"   {device.name}: {name}")
                                if name == 'dln2-adc':
                                    print("   ✅ This is a DLN2 ADC device!")
                                    dln2_adc_found = True
                                    
                                    # Check available ADC channels
                                    adc_channels = []
                                    # check channels 0-9
                                    for i in range(10):
                                        ch_path = device / f'in_voltage{i}_raw'
                                        if ch_path.exists():
                                            try:
                                                with ch_path.open() as f:
                                                    val = int(f.read().strip())
                                                    adc_channels.append((i, val))
                                            except Exception:
                                                pass
                                    
                                    if adc_channels:
                                        ch_count = len(adc_channels)
                                        print(f"   📊 ADC channels ({ch_count}): ",
                                              end="")
                                        for ch, val in adc_channels:
                                            print(f"CH{ch}={val} ", end="")
                                        print()
                                        
                                        # Show scale
                                        scale_path = device / 'scale'
                                        if scale_path.exists():
                                            try:
                                                with scale_path.open() as f:
                                                    scale = float(f.read().strip())
                                                    print(f"   📐 Scale: "
                                                          f"{scale:.6f} V/LSB")
                                                    # Show voltages
                                                    print("   🔌 Voltages: ",
                                                          end="")
                                                    for ch, val in adc_channels:
                                                        voltage = val * scale
                                                        print(f"CH{ch}="
                                                              f"{voltage:.3f}V ",
                                                              end="")
                                                    print()
                                            except Exception:
                                                pass
                                    
                    except Exception as e:
                        print(f"   ❌ Error reading {device.name}: {e}")
            
            return dln2_adc_found
        else:
            print("❌ No IIO devices found")
            return False
    else:
        print("❌ /sys/bus/iio/devices does not exist")
        return False


def main():
    print("=== DLN2 Device Status Check ===")
    print()
    
    usb_ok = check_dln2_usb()
    print()
    
    module_ok = check_dln2_module()
    print()
    
    gpio_ok = check_gpio_chips()
    print()
    
    spi_ok = check_spi_devices()
    print()
    
    i2c_ok = check_i2c_devices()
    print()
    
    adc_ok = check_adc_devices()
    print()
    
    print("=== Summary ===")
    if usb_ok and module_ok:
        print("✅ DLN2 device is working correctly!")
        if gpio_ok or spi_ok or i2c_ok or adc_ok:
            print("✅ Interfaces are available for testing")
        else:
            print("❓ Interfaces may require additional configuration")
    else:
        print("❌ Issues with DLN2 device connection")
        if not usb_ok:
            print("   - Connect Raspberry Pi Pico with DLN2 firmware")
        if not module_ok:
            print("   - dln2 module not loaded automatically")

if __name__ == "__main__":
    main()
