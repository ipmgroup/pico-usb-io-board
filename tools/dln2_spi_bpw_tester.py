#!/usr/bin/env python3
"""
DLN2 SPI BPW tester
Cycles bits-per-word (4..16), sets frame size on device and sends random data every second.
Depends on tools/dln2_spi_client.py (pyusb).
"""

import sys
from pathlib import Path
import time
import struct
import random

# Ensure repo root is on sys.path so `import tools.*` works when running script directly
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.dln2_spi_client import find_device, Dln2Usb, DLN2_SPI_SET_FRAME_SIZE

WORDS = 1  # number of words per transfer (send exactly one word)
DELAY = 1.0  # seconds between transfers
USE_HARDWARE_CS = True  # if True, do not hold SS low (let adapter toggle CS)


def pack_words(words, bpw):
    """Pack list of integer words into bytes according to bpw.
    For bpw <= 8: one byte per word (LSB in byte).
    For bpw > 8: two bytes little-endian per word.
    """
    if bpw <= 8:
        return bytes([w & 0xff for w in words])
    else:
        out = bytearray()
        for w in words:
            out += struct.pack('<H', w & 0xffff)
        return bytes(out)


def gen_words(count, bpw):
    maxv = (1 << bpw) - 1
    return [random.randint(0, maxv) for _ in range(count)]


def main():
    dev = find_device()
    client = Dln2Usb(dev)
    try:
        print('Enabling SPI...')
        print(client.spi_enable())
        time.sleep(0.05)

        # set a sane frequency and mode for oscilloscope checks
        print('Setting SPI frequency to 1 MHz and mode 0')
        print(client.spi_set_frequency(1000000))
        print(client.spi_set_mode(0))
        print('Sending one transfer for each BPW 4..16, then exit.')

        for bpw in range(4, 17):
            # set frame size: payload struct { uint8_t port; uint8_t bpw; }
            payload = struct.pack('<BB', 0, bpw)
            resp = client.send_cmd(DLN2_SPI_SET_FRAME_SIZE, payload)
            print(f'BPW set to {bpw}: result={resp["result"]}')

            # Use a deterministic pattern to make oscilloscope checks easier
            if bpw <= 8:
                pattern = 0xAA & ((1 << bpw) - 1)
            else:
                # for >8 bits use 0xAAAA truncated to bpw
                pattern = 0xAAAA & ((1 << bpw) - 1)
            words = [pattern]
            tx = pack_words(words, bpw)

            try:
                # leave_ss_low = False => adapter/firmware will toggle CS per transfer
                leave_ss = not USE_HARDWARE_CS
                rx = client.spi_read_write(tx, leave_ss_low=leave_ss)
                print(f'sent words (bpw={bpw}):', words)
                print(f'tx bytes: {len(tx)} rx bytes: {len(rx)}')
                print('rx (hex):', rx.hex())
            except Exception as e:
                print('transfer failed:', e)

            time.sleep(DELAY)

        print('Done: sent one transfer per BPW')

    except KeyboardInterrupt:
        print('\nInterrupted by user')

    finally:
        print('Disabling SPI...')
        try:
            print(client.spi_disable())
        except Exception as e:
            print('Disable failed:', e)
        client.close()


if __name__ == '__main__':
    main()
