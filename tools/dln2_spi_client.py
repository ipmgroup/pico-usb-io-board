#!/usr/bin/env python3
"""
Minimal DLN2 SPI client using libusb (pyusb).
Requires: pip install pyusb

This script opens the DLN device (VID=0x1d50, PID=0x6170), finds bulk IN/OUT endpoints,
and implements a few SPI commands (enable, set_frequency, read_write).

Note: run as regular user if udev rules grant access, or with sudo.
"""

import usb.core
import usb.util
import struct
import sys
import time

VID = 0x1d50
PID = 0x6170

# DLN2 constants (from dln2.h / dln2-spi.c)
DLN2_MODULE_SPI = 0x02
DLN2_HANDLE_SPI = 4

def DLN2_CMD(cmd, module):
    return (cmd & 0xff) | ((module & 0xff) << 8)

DLN2_SPI_ENABLE = DLN2_CMD(0x11, DLN2_MODULE_SPI)
DLN2_SPI_DISABLE = DLN2_CMD(0x12, DLN2_MODULE_SPI)
DLN2_SPI_SET_MODE = DLN2_CMD(0x14, DLN2_MODULE_SPI)
DLN2_SPI_SET_FRAME_SIZE = DLN2_CMD(0x16, DLN2_MODULE_SPI)
DLN2_SPI_SET_FREQUENCY = DLN2_CMD(0x18, DLN2_MODULE_SPI)
DLN2_SPI_READ_WRITE = DLN2_CMD(0x1A, DLN2_MODULE_SPI)
DLN2_SPI_READ = DLN2_CMD(0x1B, DLN2_MODULE_SPI)
DLN2_SPI_WRITE = DLN2_CMD(0x1C, DLN2_MODULE_SPI)

# Helpers
def find_device():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        raise ValueError('DLN2 device not found (VID:PID 1d50:6170)')
    return dev

class Dln2Usb:
    def __init__(self, dev, debug=False):
        self.dev = dev
        self.debug = bool(debug)
        self._setup()
        self.echo = 1

    def _setup(self):
        # Set active configuration
        try:
            self.dev.set_configuration()
        except Exception:
            # might already be configured
            pass

        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]

        # Find bulk endpoints
        ep_out = None
        ep_in = None
        for ep in intf.endpoints():
            if (
                usb.util.endpoint_direction(ep.bEndpointAddress)
                == usb.util.ENDPOINT_OUT
                and usb.util.endpoint_type(ep.bmAttributes)
                == usb.util.ENDPOINT_TYPE_BULK
            ):
                ep_out = ep
            if (
                usb.util.endpoint_direction(ep.bEndpointAddress)
                == usb.util.ENDPOINT_IN
                and usb.util.endpoint_type(ep.bmAttributes)
                == usb.util.ENDPOINT_TYPE_BULK
            ):
                ep_in = ep

        if not ep_in or not ep_out:
            raise RuntimeError(
                'Could not find bulk IN/OUT endpoints on DLN2 interface'
            )

        self.ep_out = ep_out.bEndpointAddress
        self.ep_in = ep_in.bEndpointAddress
        # claim interface
        self.interface = intf.bInterfaceNumber
        if self.dev.is_kernel_driver_active(self.interface):
            try:
                self.dev.detach_kernel_driver(self.interface)
            except Exception:
                pass
        usb.util.claim_interface(self.dev, self.interface)

    def close(self):
        try:
            usb.util.release_interface(self.dev, self.interface)
        except Exception:
            pass
        try:
            self.dev.attach_kernel_driver(self.interface)
        except Exception:
            pass

    def _send_raw(self, data: bytes):
        # write as a single bulk transfer
        self.dev.write(self.ep_out, data, timeout=2000)

    def _read_raw(self, size=512):
        return bytes(self.dev.read(self.ep_in, size, timeout=2000))

    def _build_hdr(self, cmd_id, payload=b'', handle=DLN2_HANDLE_SPI):
        # dln2_header: uint16_t size; uint16_t id; uint16_t echo;
        # uint16_t handle; little-endian
        size = 8 + len(payload)  # header size (8) + payload
        hdr = struct.pack(
            '<HHHH', size, cmd_id, self.echo & 0xffff, handle & 0xffff
        )
        self.echo = (self.echo + 1) & 0xffff
        return hdr + payload

    def send_cmd(self, cmd_id, payload=b''):
        pkt = self._build_hdr(cmd_id, payload)
        # The device expects full packet possibly split into USB packets
        # up to endpoint size
        if self.debug:
            try:
                print(
                    "[DLN.debug] OUT cmd=0x%04x len=%d pkt=%s"
                    % (cmd_id, len(payload), pkt.hex())
                )
            except Exception:
                pass
        self._send_raw(pkt)
        # read response: first read header+result (5*2 =10 bytes)
        # read a chunk; subsequent code will parse result and remaining data
        raw = self._read_raw(1024)
        if self.debug:
            try:
                print("[DLN.debug] IN raw=%s" % (raw.hex(),))
            except Exception:
                pass
        if len(raw) < 10:
            raise RuntimeError('Short response from device')
        # parse response: 5 little-endian uint16: size, id, echo, handle, result
        size, rid, echo, handle, result = struct.unpack('<HHHHH', raw[:10])
        payload = raw[10: size]
        resp = {
            'size': size,
            'id': rid,
            'echo': echo,
            'handle': handle,
            'result': result,
            'data': payload,
        }
        if self.debug:
            try:
                print(
                    "[DLN.debug] RESP size=%d id=0x%04x echo=%d handle=%d result=%d"
                    " data=%s"
                    % (size, rid, echo, handle, result, payload.hex())
                )
            except Exception:
                pass
        return resp

    # High-level SPI operations
    def spi_enable(self):
        payload = struct.pack('<B', 0)  # port = 0
        return self.send_cmd(DLN2_SPI_ENABLE, payload)

    def spi_disable(self):
        # disable expects 2-byte payload in firmware (port + ?). dln2-spi.c used size 2 on disable
        payload = struct.pack('<BB', 0, 0)
        return self.send_cmd(DLN2_SPI_DISABLE, payload)

    def spi_set_frequency(self, hz):
        # struct { uint8_t port; uint32_t speed; }
        payload = struct.pack('<BI', 0, int(hz))
        return self.send_cmd(DLN2_SPI_SET_FREQUENCY, payload)

    def spi_set_mode(self, mode):
        # struct { uint8_t port; uint8_t mode; }
        payload = struct.pack('<BB', 0, mode & 0xff)
        return self.send_cmd(DLN2_SPI_SET_MODE, payload)

    def spi_read_write(self, tx_bytes: bytes, leave_ss_low=False):
        # struct { uint8_t port; uint16_t size; uint8_t attr; uint8_t buf[] }
        attr = 1 if leave_ss_low else 0
        size = len(tx_bytes)
        payload = struct.pack('<BHB', 0, size & 0xffff, attr & 0xff) + tx_bytes
        resp = self.send_cmd(DLN2_SPI_READ_WRITE, payload)
        # response data layout: uint16_t size (le) followed by size bytes
        if resp['result'] != 0:
            raise RuntimeError(f'SPI transfer failed: result={resp["result"]}')
        if len(resp['data']) < 2:
            raise RuntimeError('SPI response too short')
        rx_len = struct.unpack('<H', resp['data'][:2])[0]
        rx = resp['data'][2:2+rx_len]
        return rx


def main():
    dev = find_device()
    client = Dln2Usb(dev)
    try:
        print('Enabling SPI...')
        print(client.spi_enable())
        time.sleep(0.05)
        print('Set frequency 1 MHz...')
        print(client.spi_set_frequency(1000000))
        print('Set mode 0...')
        print(client.spi_set_mode(0))
        time.sleep(0.05)

        # Example: send JEDEC ID (0x9F) and read 3 bytes
        tx = bytes([0x9F])
        print('Sending JEDEC 0x9F...')
        rx = client.spi_read_write(tx)
        print('RX:', rx.hex())

    finally:
        print('Disabling SPI...')
        try:
            print(client.spi_disable())
        except Exception as e:
            print('Disable failed:', e)
        client.close()

if __name__ == '__main__':
    main()
