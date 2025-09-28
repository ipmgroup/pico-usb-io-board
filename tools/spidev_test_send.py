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
                __import__('spidev')
                return True
            except Exception:
                return False
        return False

    if args.backend == 'native':
        try:
            import spidev as native_spidev
        except Exception as e:
            print('Native spidev not available:', e)
            sys.exit(1)

        dev = native_spidev.SpiDev()
        try:
            print('Opening native spidev...')
            dev.open(0, 0)
            try:
                dev.max_speed_hz = 1000000
            except Exception:
                pass
            try:
                dev.mode = 0
            except Exception:
                pass
            try:
                dev.bits_per_word = 8
            except Exception:
                pass
            tx = [0x9F, 0x00, 0x00, 0x00]
            print('Sending JEDEC (0x9F) via native spidev...')
            rx = dev.xfer2(tx)
            print('RX bytes:', rx)
            print('RX hex :', ''.join(f'{b:02x}' for b in rx))
        finally:
            try:
                dev.close()
            except Exception:
                pass

    else:  # dln or auto
        try:
            from tools.spidev import SpiDev
        except Exception as e:
            print('Failed to import wrapper:', e)
            sys.exit(1)

        # decide which backend to use when auto selected
        use_native = False
        if args.backend == 'native':
            use_native = True
        elif args.backend == 'auto':
            use_native = _is_raspberry_pi()

        if use_native:
            # delegate to system spidev
            try:
                import spidev as native_spidev
            except Exception as e:
                print('Native spidev requested but not available:', e)
                print('Falling back to DLN backend')
                use_native = False

        if use_native:
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
                rx = dev_native.xfer2(tx)
                print('RX bytes:', rx)
                print('RX hex :', ''.join(f'{b:02x}' for b in rx))
            finally:
                try:
                    dev_native.close()
                except Exception:
                    pass
            return

        # use DLN wrapper
        dev = SpiDev()
        dev.host_hold_cs = bool(args.host_cs)
        try:
            print('Opening SpiDev (DLN backend)...')
            dev.open(0, 0)
            dev.max_speed_hz = 1000000
            dev.mode = 0
            dev.bits_per_word = 8
            tx = [0x9F, 0x00, 0x00, 0x00]
            print(
                'Sending JEDEC (0x9F) via DLN wrapper... host_hold_cs=',
                dev.host_hold_cs,
            )
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
