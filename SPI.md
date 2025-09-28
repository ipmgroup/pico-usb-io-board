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

Further work
------------
- Add more examples and unit tests showing read/write sequences for common
  peripherals (EEPROM, flash, sensors).
- Optionally extend the adapter firmware to support arbitrary bit-length
  transfers if needed.

