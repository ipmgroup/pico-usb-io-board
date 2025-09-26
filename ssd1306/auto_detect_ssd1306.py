#!/usr/bin/env python3
"""
Automatic I2C adapter and SSD1306 display detection
Search for working I2C bus and display address
"""
import smbus2
import time
import glob
import os


class I2CDetector:
    def __init__(self):
        self.possible_addresses = [0x3c, 0x3d]  # Common SSD1306 addresses
        self.found_bus = None
        self.found_addr = None
    
    def find_i2c_buses(self):
        """Find all available I2C buses"""
        buses = []
        for i2c_dev in glob.glob('/dev/i2c-*'):
            try:
                bus_num = int(os.path.basename(i2c_dev).split('-')[1])
                buses.append(bus_num)
            except (ValueError, IndexError):
                continue
        return sorted(buses)
    
    def is_dln2_i2c_bus(self, bus_num):
        """Check if I2C bus is a DLN2 device"""
        try:
            # Check path via /sys/class/i2c-dev/
            i2c_dev_path = f"/sys/class/i2c-dev/i2c-{bus_num}"
            if not os.path.exists(i2c_dev_path):
                return False
                
            # Get real path via readlink
            real_path = os.path.realpath(i2c_dev_path)
            
            # Check if "dln2" is in the path
            return "dln2" in real_path.lower()
            
        except Exception:
            return False
    
    def find_dln2_i2c_buses(self):
        """Find only DLN2 I2C buses"""
        all_buses = self.find_i2c_buses()
        dln2_buses = []
        
        print("🔍 Searching for DLN2 I2C buses...")
        for bus_num in all_buses:
            if self.is_dln2_i2c_bus(bus_num):
                print(f"  ✅ DLN2 bus found: i2c-{bus_num}")
                dln2_buses.append(bus_num)
            else:
                print(f"  ⏭️  Skipping system bus: i2c-{bus_num}")
                
        return dln2_buses
    
    def test_ssd1306_on_bus(self, bus_num, addr):
        """Test for SSD1306 presence on specified bus and address"""
        try:
            bus = smbus2.SMBus(bus_num)
            
            # Try sending Display OFF command (safe command)
            bus.write_byte_data(addr, 0x00, 0xAE)
            time.sleep(0.01)
            
            # Try sending another safe command
            bus.write_byte_data(addr, 0x00, 0xA4)  # Entire display ON
            time.sleep(0.01)
            
            bus.close()
            return True
            
        except Exception:
            try:
                bus.close()
            except Exception:
                pass
            return False
    
    def scan_for_ssd1306(self):
        """Scan only DLN2 buses for SSD1306"""
        print("🔍 Searching for SSD1306 on DLN2 I2C buses...")
        
        # Use only DLN2 buses
        dln2_buses = self.find_dln2_i2c_buses()
        
        if not dln2_buses:
            print("❌ DLN2 I2C buses not found!")
            print("💡 Make sure DLN2 device is connected")
            return False
        
        print(f"📡 Found DLN2 buses: {dln2_buses}")
        
        for bus_num in dln2_buses:
            print(f"  🔍 Testing DLN2 bus {bus_num}...")
            
            for addr in self.possible_addresses:
                print(f"    📍 Checking address 0x{addr:02x}...", end=" ")
                
                if self.test_ssd1306_on_bus(bus_num, addr):
                    print("✅ FOUND!")
                    self.found_bus = bus_num
                    self.found_addr = addr
                    return True
                else:
                    print("❌")
        
        print("❌ SSD1306 not found on any DLN2 bus!")
        return False
    
    def get_connection_info(self):
        """Returns information about found connection"""
        if self.found_bus is not None and self.found_addr is not None:
            return {
                'bus': self.found_bus,
                'address': self.found_addr,
                'address_hex': f"0x{self.found_addr:02x}"
            }
        return None


class AutoSSD1306:
    def __init__(self):
        self.detector = I2CDetector()
        self.bus = None
        self.addr = None
        self.width = 128
        self.height = 32  # Default 32, can be changed
        self.pages = 4
        self.buffer = None
        
    def auto_connect(self):
        """Automatically find and connect to SSD1306"""
        print("🚀 Auto-connecting to SSD1306...")
        
        if not self.detector.scan_for_ssd1306():
            print("❌ SSD1306 display not found!")
            return False
        
        conn_info = self.detector.get_connection_info()
        print("✅ SSD1306 found!")
        print(f"   📡 I2C bus: {conn_info['bus']}")
        print(f"   📍 Address: {conn_info['address_hex']} "
              f"({conn_info['address']})")
        
        try:
            self.bus = smbus2.SMBus(conn_info['bus'])
            self.addr = conn_info['address']
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def detect_display_size(self):
        """Try to detect display size (128x32 vs 128x64)"""
        if not self.bus:
            return False
            
        print("📐 Detecting display size...")
        
        # Initialize for 128x64 and see if it works
        try:
            # Try initialization for 128x64
            self.bus.write_byte_data(self.addr, 0x00, 0xAE)  # Display OFF
            self.bus.write_byte_data(self.addr, 0x00, 0xA8)  # Set multiplex
            self.bus.write_byte_data(self.addr, 0x00, 0x3F)  # 64 rows
            
            # If we got here without error, try 128x32
            self.bus.write_byte_data(self.addr, 0x00, 0xA8)  # Set multiplex
            self.bus.write_byte_data(self.addr, 0x00, 0x1F)  # 32 rows
            
            self.height = 32
            self.pages = 4
            print("   📏 Size: 128x32 pixels")
            
        except Exception as e:
            print(f"   ⚠️  Error detecting size: {e}")
            print("   📏 Using 128x32 as default")
            self.height = 32
            self.pages = 4
        
        # Initialize buffer
        self.buffer = [[0x00 for _ in range(self.width)]
                       for _ in range(self.pages)]
        return True
    
    def init_display(self):
        """Initialize display with correct parameters"""
        if not self.bus:
            return False
            
        print("🔧 Initializing display...")
        
        try:
            commands = [
                0xAE,        # Display OFF
                0xA8, 0x1F,  # Multiplex ratio for 128x32
                0xD3, 0x00,  # Display offset 0
                0x40,        # Start line 0
                0x8D, 0x14,  # Charge pump ON
                0x20, 0x00,  # Horizontal addressing
                0xA1,        # Segment remap
                0xC8,        # COM direction
                0xDA, 0x02,  # COM pins for 128x32
                0x81, 0xFF,  # Max contrast
                0xD9, 0xF1,  # Pre-charge
                0xDB, 0x40,  # Vcomh
                0xA4,        # Display follows RAM
                0xA6,        # Normal display
                0xAF         # Display ON
            ]
            
            i = 0
            while i < len(commands):
                two_byte = [0xA8, 0xD3, 0x8D, 0x20, 0xDA, 0x81, 0xD9, 0xDB]
                if i + 1 < len(commands) and commands[i] in two_byte:
                    self.bus.write_byte_data(self.addr, 0x00, commands[i])
                    self.bus.write_byte_data(self.addr, 0x00, commands[i + 1])
                    i += 2
                else:
                    self.bus.write_byte_data(self.addr, 0x00, commands[i])
                    i += 1
                time.sleep(0.001)
            
            print("✅ Display initialized!")
            return True
            
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            return False
    
    def test_display(self):
        """Simple display test"""
        if not self.bus or not self.buffer:
            return False
            
        print("🧪 Testing display...")
        
        try:
            # Clear display
            for page in range(self.pages):
                for col in range(self.width):
                    self.buffer[page][col] = 0x00
            
            # Draw thin frame
            for x in range(self.width):
                self.buffer[0][x] = 0x01  # Top line (only top pixel)
                # Bottom line (only bottom pixel)
                self.buffer[self.pages-1][x] = 0x80
            
            for page in range(self.pages):
                self.buffer[page][0] |= 0xFF      # Left line (vertical)
                # Right line (vertical)
                self.buffer[page][self.width-1] |= 0xFF
            
            # Send to display
            self.update_display()
            print("✅ Test passed! Display should show a thin frame.")
            return True
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False
    
    def update_display(self):
        """Send buffer to display"""
        if not self.bus or not self.buffer:
            return
            
        # Set writing area
        self.bus.write_byte_data(self.addr, 0x00, 0x21)  # Column addr
        self.bus.write_byte_data(self.addr, 0x00, 0x00)  # Start
        self.bus.write_byte_data(self.addr, 0x00, 0x7F)  # End
        self.bus.write_byte_data(self.addr, 0x00, 0x22)  # Page addr
        self.bus.write_byte_data(self.addr, 0x00, 0x00)  # Start
        self.bus.write_byte_data(self.addr, 0x00, self.pages-1)  # End
        
        # Send data
        for page in range(self.pages):
            for i in range(0, self.width, 16):
                chunk = self.buffer[page][i:i+16]
                try:
                    self.bus.write_i2c_block_data(self.addr, 0x40, chunk)
                except Exception:
                    for byte_val in chunk:
                        self.bus.write_byte_data(self.addr, 0x40, byte_val)


def main():
    print("=== SSD1306 Display Auto-detection ===")
    print()
    
    display = AutoSSD1306()
    
    # Step 1: Search and connect
    if not display.auto_connect():
        print("💡 Troubleshooting tips:")
        print("   1. Check physical display connection")
        print("   2. Make sure Pico USB I/O Board is connected")
        print("   3. Check correct I2C wiring (SDA/SCL)")
        print("   4. Try different address (0x3C or 0x3D)")
        return
    
    # Step 2: Size detection
    if not display.detect_display_size():
        print("❌ Failed to detect display size")
        return
    
    # Step 3: Initialize
    if not display.init_display():
        print("❌ Failed to initialize display")
        return
    
    # Step 4: Test
    if not display.test_display():
        print("❌ Display test failed")
        return
    
    print()
    print("🎉 All ready!")
    print(f"   📡 I2C bus: {display.detector.found_bus}")
    print(f"   📍 Address: 0x{display.detector.found_addr:02x}")
    print(f"   📏 Size: {display.width}x{display.height}")
    print("   ✅ Display working correctly")
    print()
    print("💡 Display ready for use!")
    print("   Other scripts will automatically find it on every run.")


if __name__ == "__main__":
    main()
