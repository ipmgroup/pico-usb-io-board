#!/usr/bin/env python3
"""Simple test: use tools.spidev.SpiDev to send JEDEC ID and print response.

Usage: python tools/spidev_test_send.py
"""
import sys
from pathlib import Path
import argparse

# add repo root to sys.path so `import tools.*` works when run directly
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def main():
    p = argparse.ArgumentParser(description='spidev wrapper send test')
    p.add_argument(
        '--backend', choices=['auto', 'dln', 'native'], default='auto',
        help='which backend to use: auto (default), dln or native spidev'
    )
    p.add_argument(
        '--host-cs', action='store_true', help='request host-held CS for DLN'
    )
    p.add_argument(
        '--verbose', action='store_true', help='show verbose DLN/spi debug'
    )
    p.add_argument(
        '--per-byte', action='store_true',
        help='send bytes one-by-one (toggle CS per byte)'
    )
    p.add_argument(
        '--inter-byte-delay', type=float, default=5.0,
        help=(
            'inter-byte delay in milliseconds when using --per-byte '
            '(default 5 ms). fractional ms allowed, e.g. 0.2 for 200us; '
            'minimum 0.001 ms (1 µs)'
        ),
    )
    args = p.parse_args()

    def _is_raspberry_pi() -> bool:
        try:
            model_path = Path('/proc/device-tree/model')
            if model_path.exists():
                txt = model_path.read_text(errors='ignore')
                if 'Raspberry' in txt or 'raspberry' in txt:
                    return True
        except Exception:
            pass
        try:
            cpu = Path('/proc/cpuinfo')
            if cpu.exists():
                txt = cpu.read_text(errors='ignore')
                if 'BCM' in txt or 'Raspberry' in txt:
                    return True
        except Exception:
            pass
        import platform
        m = platform.machine().lower()
        if 'arm' in m or 'aarch64' in m:
            # presence of spidev module is a good hint
            try:
                # do not bind the module name here; just check importability
                __import__('spidev')
                return True
            except Exception:
                return False
        return False

    def detect_backend_auto(prefer_native=False):
        """Return 'native' or 'dln' depending on what is available.

        Detection strategy:
        - if prefer_native True, try native first
        - check for /dev/spidev* devices; if present, try importing spidev
        - otherwise try importing DLN wrapper (tools.spidev)
        - return None when neither is available
        """
        # quick check for spidev devices
        try:
            spidev_paths = list(Path('/dev').glob('spidev*'))
        except Exception:
            spidev_paths = []

        # prefer native when requested
        if prefer_native and spidev_paths:
            try:
                __import__('spidev')
                return 'native'
            except Exception:
                pass

        # if there is a spidev device node, prefer native backend; we will
        # attempt to import the Python module later when actually using it.
        if spidev_paths:
            return 'native'

        # try DLN wrapper (deferred import)
        try:
            # only import the wrapper module, don't instantiate hardware
            __import__('tools.spidev')
            return 'dln'
        except Exception as e:
            dln_err = e

        # neither backend available
        print('No usable SPI backend found.')
        if dln_err:
            print('DLN wrapper import failed:', dln_err)
            print('If you want DLN backend, install pyusb: pip3 install pyusb')
        return None

    # Decide backend
    if args.backend == 'native':
        chosen = 'native'
    elif args.backend == 'dln':
        chosen = 'dln'
    else:
        chosen = detect_backend_auto()

    if chosen is None:
        sys.exit(1)

    if chosen == 'native':
        try:
            import spidev as native_spidev
        except Exception as e:
            print('Native spidev requested but import failed:', e)
            print('Install system package: sudo apt install python3-spidev')
            print('or pip3 install spidev')
            sys.exit(1)

        dev_native = native_spidev.SpiDev()
        try:
            print('Opening native spidev...')
            dev_native.open(0, 0)
            try:
                dev_native.max_speed_hz = 1000000
            except Exception:
                pass
            try:
                dev_native.mode = 0
            except Exception:
                pass
            try:
                dev_native.bits_per_word = 8
            except Exception:
                pass
            tx = [0x9F, 0x00, 0x00, 0x00]
            print('Sending JEDEC (0x9F) via native spidev...')
            if args.per_byte:
                rx = []
                for b in tx:
                    rx += dev_native.xfer2([b])
            else:
                rx = dev_native.xfer2(tx)
            print('RX bytes:', rx)
            print('RX hex :', ''.join(f'{b:02x}' for b in rx))
        finally:
            try:
                dev_native.close()
            except Exception:
                pass
        return

    # chosen == 'dln'
    try:
        from tools.spidev import SpiDev
    except Exception as e:
        print('Failed to import DLN wrapper (tools.spidev):', e)
        print('If you want DLN backend, install pyusb: pip3 install pyusb')
        sys.exit(1)

    dev = SpiDev()
    dev.host_hold_cs = bool(args.host_cs)
    dev.debug = bool(args.verbose)
    try:
        print('Opening SpiDev (DLN backend)...')
        dev.open(0, 0)
        dev.max_speed_hz = 10000000
        dev.mode = 0
        dev.bits_per_word = 8
        tx = [0x9F, 0x00, 0x00, 0x00]
        print(
            'Sending JEDEC (0x9F) via DLN wrapper... host_hold_cs=',
            dev.host_hold_cs,
        )
        if args.per_byte:
            rx = dev.xfer_per_byte(
                tx, inter_byte_delay_ms=args.inter_byte_delay
            )
        else:
            rx = dev.xfer2(tx)
        print('RX bytes:', rx)
        print('RX hex :', ''.join(f'{b:02x}' for b in rx))
    except Exception as e:
        print('Test failed:', e)
    finally:
        try:
            dev.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
