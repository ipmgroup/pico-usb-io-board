#!/usr/bin/env python3
"""
spidev-compatible wrapper backed by DLN2 USB client
(tools.dln2_spi_client.Dln2Usb).

This provides a minimal subset of the popular `spidev` Python API so existing
scripts can call `import spidev` and use `SpiDev` with similar semantics.

Limitations / notes:
- This is a thin adapter over the DLN2 client; it talks to a single SPI port
  (port 0) on the DLN device.
- bits_per_word can be set; the wrapper will call the DLN2 SET_FRAME_SIZE
  command before transfers.
- xfer2 sends a single transfer and returns the received bytes.
"""

from typing import List
import struct
import sys
from pathlib import Path

# Support running this module both as a package (import tools.spidev)
# and directly (python tools/spidev.py). Try relative import first,
# fall back to adding repository root to sys.path and importing absolutely.
try:
    from .dln2_spi_client import find_device, Dln2Usb, DLN2_SPI_SET_FRAME_SIZE
except Exception:
    # adjust path to repo root and import
    REPO_ROOT = Path(__file__).resolve().parents[1]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from tools.dln2_spi_client import (
        find_device,
        Dln2Usb,
        DLN2_SPI_SET_FRAME_SIZE,
    )


class SpiDev:
    """Minimal SpiDev-compatible object backed by DLN2 USB SPI.

    Implements a subset of py-spidev API: open/close, xfer/xfer2, writebytes,
    readbytes, properties (mode, max_speed_hz, bits_per_word), cshigh, lsbfirst
    and context-manager support.
    """

    def __init__(self):
        self._client = None
        # internal state backing properties
        self._max_speed_hz = 1000000
        self._mode = 0
        self._bits_per_word = 8
        # flags present in py-spidev API (not all map to DLN features)
        self.cshigh = False
        self.lsbfirst = False
        # Control whether wrapper holds CS low across transfers.
        # If True, wrapper will request DLN2 to leave SS low (host-held CS).
        # Some DLN firmwares bundle clocks per byte when adapter toggles CS;
        # set this to True to force host-held CS behavior.
        self.host_hold_cs = False

    def open(self, bus: int, device: int):
        # bus/device are ignored for DLN device binding; kept for compatibility
        dev = find_device()
        self._client = Dln2Usb(dev)
        # enable SPI on the adapter
        self._client.spi_enable()
        # apply initial settings
        self._client.spi_set_frequency(self._max_speed_hz)
        self._client.spi_set_mode(self._mode)
        self._set_frame_size(self._bits_per_word)

    def close(self):
        if self._client:
            try:
                self._client.spi_disable()
            except Exception:
                pass
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def _set_frame_size(self, bpw: int):
        # call DLN2 SPI_SET_FRAME_SIZE
        payload = struct.pack('<BB', 0, int(bpw) & 0xff)
        self._client.send_cmd(DLN2_SPI_SET_FRAME_SIZE, payload)

    def xfer2(self, data: List[int]) -> List[int]:
        """Send data (list of bytes or ints) and return list of received bytes.

        The wrapper sends the bytes as-is. For bits_per_word != 8, the wrapper
        will pack words according to bits_per_word (1 or 2 bytes per word).
        """
        if not self._client:
            raise RuntimeError('SpiDev not open')

        # ensure parameters are applied
        self._client.spi_set_frequency(int(self._max_speed_hz))
        self._client.spi_set_mode(int(self._mode))
        if int(self._bits_per_word) != 8:
            self._set_frame_size(int(self._bits_per_word))

        # pack data according to bits_per_word
        bpw = int(self._bits_per_word)
        if bpw <= 8:
            tx_bytes = bytes([int(b) & 0xff for b in data])
        else:
            # pack sequential values into little-endian 16-bit words
            out = bytearray()
            for w in data:
                out += struct.pack('<H', int(w) & 0xffff)
            tx_bytes = bytes(out)

        leave_ss = self.host_hold_cs
        rx = self._client.spi_read_write(tx_bytes, leave_ss_low=leave_ss)

        # return rx as list of ints (byte values)
        return list(rx)

    # Convenience aliases to match common spidev API
    def writebytes(self, data: List[int]):
        self.xfer2(data)

    def readbytes(self, length: int) -> List[int]:
        # read by sending zeros
        return self.xfer2([0] * int(length))

    # py-spidev compatible methods
    def xfer(self, data: List[int]) -> List[int]:
        """Alias for xfer2 for compatibility with py-spidev."""
        return self.xfer2(data)

    # Properties to mimic py-spidev
    @property
    def max_speed_hz(self) -> int:
        return int(self._max_speed_hz)

    @max_speed_hz.setter
    def max_speed_hz(self, v: int):
        self._max_speed_hz = int(v)
        if self._client:
            self._client.spi_set_frequency(self._max_speed_hz)

    @property
    def mode(self) -> int:
        return int(self._mode)

    @mode.setter
    def mode(self, v: int):
        self._mode = int(v) & 0x3
        if self._client:
            self._client.spi_set_mode(self._mode)

    @property
    def bits_per_word(self) -> int:
        return int(self._bits_per_word)

    @bits_per_word.setter
    def bits_per_word(self, v: int):
        self._bits_per_word = int(v)
        if self._client:
            self._set_frame_size(self._bits_per_word)

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.close()
        except Exception:
            pass


def test_import():
    # simple smoke test: importable without errors
    SpiDev()
    return True


if __name__ == '__main__':
    print('spidev wrapper test:', test_import())
