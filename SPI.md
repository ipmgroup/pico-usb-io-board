SPI usage with DLN2 adapter
==========================

Overview
--------
This repository includes a lightweight user-space SPI client and a small
py-spidev-compatible wrapper that allows switching between a DLN2 USB
adapter on desktop machines and the native Linux `spidev` interface (commonly
used on Raspberry Pi).

Adapter limitations
-------------------
- The DLN2 firmware supports frame sizes of either 8 bits or 16 bits only.
  The adapter cannot stream transfers with arbitrary bit lengths other than
  8 or 16. When configured for a frame size greater than 8, words are sent
  as little-endian 16-bit values.
- CS handling: the adapter can toggle CS itself, but in some firmware
  versions it groups clocks into byte/word boundaries (observed grouping of
  8 or 16 clocks). For per-transfer bit-accurate timing you can request the
  adapter to "leave SS/CS low" so the host holds CS low for the duration of
  the transfer. Use the wrapper tests option `--host-cs` to enable host-held
  CS.

- Important: when using the DLN2/DLN backend with hardware-controlled CS, a
  single USB transfer (the buffer sent from the host to the adapter) is
  presented to the SPI peripheral as one transaction — the adapter will
  therefore assert the hardware CS for the whole buffer. In other words,
  if the host sends N bytes in one USB packet, hardware CS will normally be
  active for all N bytes. To toggle CS between individual bytes, perform
  per-byte transfers from the host (see example below) or use software CS.

Provided tools
--------------
- `tools/dln2_spi_client.py`
  - Minimal DLN2-over-USB client using pyusb. Implements commands used by
    the test tools: enable/disable SPI, set frequency/mode/frame size and
    read/write transfers.
- `tools/dln2_spi_bpw_tester.py`
  - Cycles bits-per-word values, sets frame size on the device and sends
    deterministic patterns for oscilloscope verification. Use this when you
    need to verify how the adapter emits SCK pulses for different frame sizes.
- `tools/spidev.py`
  - A thin, py-spidev-compatible wrapper that exposes a `SpiDev` class with
    `open()`, `close()`, `xfer2()`, `xfer()`, `writebytes()`, `readbytes()`
    and the common properties `mode`, `max_speed_hz`, `bits_per_word`.
  - This wrapper talks to the DLN2 adapter (DLN backend) and is intended to
    let code written for the `spidev` API to operate with the DLN2 device.
- `tools/spidev_test_send.py`
  - Small test program that exercises the wrapper. It has a `--backend`
    option (auto/dln/native) and a `--host-cs` flag when using the DLN backend.

Usage examples
--------------
- Read JEDEC ID via DLN wrapper (default auto-detection falls back to DLN on
  desktop):

```bash
python3 tools/spidev_test_send.py
```

- Force DLN backend and request host-held CS:

```bash
python3 tools/spidev_test_send.py --backend dln --host-cs
```

- On Raspberry Pi, use the native spidev interface:

```bash
python3 tools/spidev_test_send.py --backend native
```

Notes and troubleshooting
-------------------------
- If you receive empty responses or zeroes on MISO while the device is
  expected to reply, check:
  - Physical connections (MISO/MOSI/SCK/CS power and ground).
  - CS polarity and whether the adapter is toggling CS or the host should
    hold it low (use `--host-cs` to force the latter).
  - The device's required SPI mode (CPOL/CPHA) and clock rate.
- The wrapper is intentionally thin and focuses on compatibility. For
  advanced timing or non-8/16-bit transfers, firmware changes in the adapter
  would be required.

Example: per-byte transfers (toggle CS per byte)
-----------------------------------------------
If you need the adapter to toggle CS between individual bytes, run the
test tool in per-byte mode. This sends one USB transfer per SPI byte and
makes the adapter emit CS for each byte separately. Example:

```bash
python3 tools/spidev_test_send.py \
  --backend dln --per-byte --verbose --inter-byte-delay 0.001
```

Notes:
- `--per-byte` sends bytes individually so hardware CS will be asserted per
  byte (instead of across the whole buffer).
- `--inter-byte-delay` is the delay between bytes in milliseconds; `0.001`
  equals 1 µs here (the script accepts fractional milliseconds).
- `--verbose` enables DLN/SPI debug output which is useful when inspecting
  transfer timing and responses.

Further work
------------
- Add more examples and unit tests showing read/write sequences for common
  peripherals (EEPROM, flash, sensors).
- Optionally extend the adapter firmware to support arbitrary bit-length
  transfers if needed.

Loopback test (MOSI <-> MISO)
-----------------------------
A simple way to verify that your SPI wiring and transfers work is to wire
MOSI to MISO (physically loop the pins) and perform a loopback transfer.
The host sends data on MOSI and expects to receive the same bytes on MISO.

Basic steps:

1. Physically connect the MOSI pin to the MISO pin on the target connector.
2. Make sure CS is handled correctly: for precise per-byte verification use
   `--per-byte` (see above) or enable software CS so you can assert CS
   per byte from the host.
3. Run the test tool. Example (DLN backend, per-byte mode with tiny delay):

```bash
/usr/bin/env python3 tools/spidev_test_send.py \
  --backend dln --per-byte --verbose --inter-byte-delay 0.001
```

4. The tool sends a JEDEC ID sequence by default (0x9F 0x00 0x00 0x00).
   In loopback this should be echoed back. A successful run prints the RX
   bytes and their hex representation.

Minimal Python check (concept):

```python
tx = [0x9F, 0x00, 0x00, 0x00]
rx = dev.xfer_per_byte(tx, inter_byte_delay_ms=0.001)
if rx == tx:
    print('Loopback OK')
else:
    print('Mismatch', rx)
```

Caveats:
- If hardware CS is used and you send the whole buffer in one USB transfer,
  the adapter will assert CS for the entire buffer; the received bytes may
  therefore reflect a single contiguous transaction (this is normal).
- USB/driver buffering and small inter-byte delays may still introduce
  timing differences; if timing is critical, prefer software CS or run the
  verification at a lower SPI clock rate.
- If you get shifted or repeated bytes, double-check frame size (8 vs 16
  bits) and CPOL/CPHA settings.

