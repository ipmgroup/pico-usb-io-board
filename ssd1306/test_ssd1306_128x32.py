#!/usr/bin/env python3
"""
Advanced SSD1306 128x32 OLED display test with DLN2 auto-detection
Text and graphics drawing with demonstration elements
"""
import sys
import time
import smbus2
from auto_detect_ssd1306 import I2CDetector


def auto_detect_dln2_display(verbose=False):
    """Automatically find SSD1306 on DLN2 buses"""
    if verbose:
        print("🔍 Searching for SSD1306 on DLN2 buses...")
    
    detector = I2CDetector()
    
    def quiet_find_dln2():
        buses = detector.find_i2c_buses()
        dln2_buses = []
        
        if verbose:
            print("🔍 Searching for DLN2 I2C buses...")
        
        for bus_num in buses:
            if detector.is_dln2_i2c_bus(bus_num):
                if verbose:
                    print(f"  ✅ DLN2 bus found: i2c-{bus_num}")
                dln2_buses.append(bus_num)
            elif verbose:
                print(f"  ⏭️  Skipping system bus: i2c-{bus_num}")
                
        return dln2_buses
    
    def quiet_scan():
        if verbose:
            print("🔍 Searching for SSD1306 on DLN2 I2C buses...")
        
        dln2_buses = quiet_find_dln2()
        
        if not dln2_buses:
            print("❌ DLN2 I2C buses not found!")
            print("💡 Make sure DLN2 device is connected")
            return False
        
        if verbose:
            print(f"📡 Found DLN2 buses: {dln2_buses}")
        
        for bus_num in dln2_buses:
            if verbose:
                print(f"  🔍 Testing DLN2 bus {bus_num}...")
            
            for addr in detector.possible_addresses:
                if verbose:
                    print(f"    📍 Checking address 0x{addr:02x}...", end=" ")
                
                if detector.test_ssd1306_on_bus(bus_num, addr):
                    if verbose:
                        print("✅ FOUND!")
                    detector.found_bus = bus_num
                    detector.found_addr = addr
                    return True
                elif verbose:
                    print("❌")
        
        return False
    
    if not quiet_scan():
        print("❌ SSD1306 not found on DLN2 buses!")
        print("💡 Make sure that:")
        print("   • DLN2 device is connected")
        print("   • SSD1306 is properly connected to DLN2")
        print("   • I2C wiring is correct (SDA/SCL)")
        sys.exit(1)
    
    conn_info = detector.get_connection_info()
    if verbose:
        print(f"✅ SSD1306 found: bus {conn_info['bus']}, "
              f"address {conn_info['address_hex']}")
    
    return conn_info['bus'], conn_info['address']

class SSD1306_128x32:
    def __init__(self, verbose=False):
        # Use auto-detection instead of fixed parameters
        i2c_bus, address = auto_detect_dln2_display(verbose)
        
        self.bus = smbus2.SMBus(i2c_bus)
        self.addr = address
        self.width = 128
        self.height = 32
        self.pages = self.height // 8
        
        # Create display buffer (128 x 4 pages)
        self.buffer = [[0x00 for _ in range(self.width)] 
                       for _ in range(self.pages)]
        
    def command(self, cmd):
        """Send command to display"""
        self.bus.write_byte_data(self.addr, 0x00, cmd)
        
    def init_display(self):
        """Initialize display"""
        commands = [
            0xAE,        # Display OFF
            0xD5, 0x80,  # Set display clock divide ratio
            0xA8, 0x1F,  # Set multiplex ratio (31 for 32 rows)
            0xD3, 0x00,  # Set display offset
            0x40,        # Set start line address
            0x8D, 0x14,  # Charge pump setting
            0x20, 0x00,  # Memory addressing mode (horizontal)
            0xA1,        # Set segment re-map (0xA1 for correct orientation)
            0xC8,        # Set COM output scan direction
            0xDA, 0x02,  # Set COM pins hardware config (0x02 for 128x32)
            0x81, 0xCF,  # Set contrast control
            0xD9, 0xF1,  # Set pre-charge period
            0xDB, 0x40,  # Set vcomh detect
            0xA4,        # Entire display ON (follow RAM content)
            0xA6,        # Set normal display (not inverted)
            0xAF         # Display ON
        ]
        
        i = 0
        while i < len(commands):
            if i + 1 < len(commands) and commands[i] in [0xD5, 0xA8, 0xD3, 0x8D, 0x20, 0xDA, 0x81, 0xD9, 0xDB]:
                self.command(commands[i])
                self.command(commands[i + 1])
                i += 2
            else:
                self.command(commands[i])
                i += 1
            time.sleep(0.001)
    
    def clear_buffer(self):
        """Clear buffer"""
        for page in range(self.pages):
            for col in range(self.width):
                self.buffer[page][col] = 0x00
    
    def set_pixel(self, x, y, color=1):
        """Set pixel in buffer"""
        if 0 <= x < self.width and 0 <= y < self.height:
            page = y // 8
            bit = y % 8
            if color:
                self.buffer[page][x] |= (1 << bit)
            else:
                self.buffer[page][x] &= ~(1 << bit)
    
    def draw_char(self, x, y, char, font_5x7=None):
        """Draw 6x8 pixel character"""
        # Simple 6x8 font for basic characters - optimized for SSD1306
        font = {
            'A': [0x00, 0x7C, 0x12, 0x11, 0x12, 0x7C],
            'B': [0x00, 0x7F, 0x49, 0x49, 0x49, 0x36],
            'C': [0x00, 0x3E, 0x41, 0x41, 0x41, 0x22],
            'D': [0x00, 0x7F, 0x41, 0x41, 0x22, 0x1C],
            'E': [0x00, 0x7F, 0x49, 0x49, 0x49, 0x41],
            'F': [0x00, 0x7F, 0x09, 0x09, 0x09, 0x01],
            'G': [0x00, 0x3E, 0x41, 0x49, 0x49, 0x7A],
            'H': [0x00, 0x7F, 0x08, 0x08, 0x08, 0x7F],
            'I': [0x00, 0x00, 0x41, 0x7F, 0x41, 0x00],
            'J': [0x00, 0x20, 0x40, 0x41, 0x3F, 0x01],
            'K': [0x00, 0x7F, 0x08, 0x14, 0x22, 0x41],
            'L': [0x00, 0x7F, 0x40, 0x40, 0x40, 0x40],
            'M': [0x00, 0x7F, 0x02, 0x04, 0x02, 0x7F],
            'N': [0x00, 0x7F, 0x04, 0x08, 0x10, 0x7F],
            'O': [0x00, 0x3E, 0x41, 0x41, 0x41, 0x3E],
            'P': [0x00, 0x7F, 0x09, 0x09, 0x09, 0x06],
            'Q': [0x00, 0x3E, 0x41, 0x51, 0x21, 0x5E],
            'R': [0x00, 0x7F, 0x09, 0x19, 0x29, 0x46],
            'S': [0x00, 0x46, 0x49, 0x49, 0x49, 0x31],
            'T': [0x00, 0x01, 0x01, 0x7F, 0x01, 0x01],
            'U': [0x00, 0x3F, 0x40, 0x40, 0x40, 0x3F],
            'V': [0x00, 0x1F, 0x20, 0x40, 0x20, 0x1F],
            'W': [0x00, 0x3F, 0x40, 0x30, 0x40, 0x3F],
            'X': [0x00, 0x63, 0x14, 0x08, 0x14, 0x63],
            'Y': [0x00, 0x07, 0x08, 0x70, 0x08, 0x07],
            'Z': [0x00, 0x61, 0x51, 0x49, 0x45, 0x43],
            ' ': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            '!': [0x00, 0x00, 0x00, 0x5F, 0x00, 0x00],
            '?': [0x00, 0x02, 0x01, 0x51, 0x09, 0x06],
            ':': [0x00, 0x00, 0x36, 0x36, 0x00, 0x00],
            '0': [0x00, 0x3E, 0x51, 0x49, 0x45, 0x3E],
            '1': [0x00, 0x00, 0x42, 0x7F, 0x40, 0x00],
            '2': [0x00, 0x42, 0x61, 0x51, 0x49, 0x46],
            '3': [0x00, 0x21, 0x41, 0x45, 0x4B, 0x31],
            '4': [0x00, 0x18, 0x14, 0x12, 0x7F, 0x10],
            '5': [0x00, 0x27, 0x45, 0x45, 0x45, 0x39],
            '6': [0x00, 0x3C, 0x4A, 0x49, 0x49, 0x30],
            '7': [0x00, 0x01, 0x71, 0x09, 0x05, 0x03],
            '8': [0x00, 0x36, 0x49, 0x49, 0x49, 0x36],
            '9': [0x00, 0x06, 0x49, 0x49, 0x29, 0x1E],
        }
        
        if char in font:
            # Draw character bitwise to the correct page
            page = y // 8
            for i, col_data in enumerate(font[char]):
                if x + i < self.width and page < self.pages:
                    self.buffer[page][x + i] = col_data
    
    def draw_string(self, x, y, text):
        """Draw text string"""
        for i, char in enumerate(text.upper()):
            self.draw_char(x + i * 7, y, char)  # 6 pixels char + 1 pixel space
    
    def draw_rect(self, x, y, w, h, fill=False):
        """Draw rectangle"""
        if fill:
            for dy in range(h):
                for dx in range(w):
                    self.set_pixel(x + dx, y + dy, 1)
        else:
            # Borders
            for dx in range(w):
                self.set_pixel(x + dx, y, 1)      # top
                self.set_pixel(x + dx, y + h - 1, 1)  # bottom
            for dy in range(h):
                self.set_pixel(x, y + dy, 1)      # left
                self.set_pixel(x + w - 1, y + dy, 1)  # right
    
    def draw_line(self, x0, y0, x1, y1):
        """Draw line (Bresenham algorithm)"""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        while True:
            self.set_pixel(x0, y0, 1)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
    
    def update_display(self):
        """Send buffer to display"""
        # Set addressing
        self.command(0x21)  # Column addr
        self.command(0x00)  # Column start
        self.command(0x7F)  # Column end (127)
        
        self.command(0x22)  # Page addr
        self.command(0x00)  # Page start
        self.command(0x03)  # Page end (3 pages for 32 rows)
        
        # Send buffer in 16-byte blocks
        for page in range(self.pages):
            for block_start in range(0, self.width, 16):
                block_end = min(block_start + 16, self.width)
                data = [0x40] + self.buffer[page][block_start:block_end]
                try:
                    self.bus.write_i2c_block_data(self.addr, data[0], data[1:])
                except:
                    # Send byte by byte if block doesn't work
                    for i in range(block_start, block_end):
                        self.bus.write_byte_data(self.addr, 0x40, self.buffer[page][i])

def demo_display(verbose=False):
    """Demonstration program"""
    print("🔌 Initializing 128x32 display...")
    display = SSD1306_128x32(verbose)
    display.init_display()
    
    demos = [
        ("Clearing display", lambda d: d.clear_buffer()),
        
        ("Display frame", lambda d: d.draw_rect(0, 0, 128, 32)),
        
        ("Title", lambda d: [
            d.clear_buffer(),
            d.draw_string(25, 2, "SSD1306 TEST"),
            d.draw_string(35, 12, "128 x 32"),
            d.draw_rect(20, 0, 88, 22)
        ]),
        
        ("Various shapes", lambda d: [
            d.clear_buffer(),
            d.draw_rect(10, 2, 20, 12),            # empty rectangle
            d.draw_rect(40, 2, 20, 12, fill=True), # filled
            d.draw_line(70, 2, 90, 14),            # diagonal line
            d.draw_line(70, 14, 90, 2),            # cross line
            d.draw_string(10, 20, "SHAPES DEMO"),
        ]),
        
        ("System information", lambda d: [
            d.clear_buffer(),
            d.draw_string(5, 2, "DLN2 I2C TEST"),
            d.draw_string(5, 10, f"BUS: AUTO"),
            d.draw_string(5, 18, f"ADDR: AUTO"),
            d.draw_string(70, 18, "128x32"),
            d.draw_rect(0, 0, 128, 32)
        ]),
        
        ("Pixel test", lambda d: [
            d.clear_buffer(),
            *[d.set_pixel(x, 16 + int(10 * (((x-64)**2)/1000)), 1) 
              for x in range(128)],
            d.draw_string(40, 2, "PIXELS"),
        ]),
    ]
    
    for name, demo_func in demos:
        print(f"  📺 {name}...")
        if callable(demo_func):
            result = demo_func(display)
            if isinstance(result, list):
                pass  # list of commands already executed
        display.update_display()
        time.sleep(3)
    
    # Final cleanup
    print("  🧹 Final cleanup...")
    display.clear_buffer()
    display.update_display()

def main():
    # Check for verbose flag
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    print("=== SSD1306 128x32 OLED Display Test ===")
    if verbose:
        print("🔍 Mode: Verbose output enabled")
    print()
    
    try:
        demo_display(verbose)
        print("✅ Demo completed successfully!")
        
    except PermissionError:
        print("❌ Permission error. Run with sudo:")
        print("   sudo python test_ssd1306_128x32.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
