# AGBinator: Draft Edition

import argparse
import glob
import itertools
import os
import re


def is_rom_address(address):
    return 0x8000000 <= address <= 0x9ffffff


def to_address(offset):
    return 0x8000000 + offset


def to_offset(address):
    return address - 0x8000000


def agbinator_scan_mp2k(rom):
    return None


def agbinator_scan_gax(rom):
    gax_signature_pattern = re.compile(br"GAX Sound Engine v?(\d)\.(\d{1,3})([A-Za-z\-]*)")
    match_result = gax_signature_pattern.search(rom)
    if not match_result:
        return None

    return {
        "driver_name": "GAX",
        "driver_version": match_result.group().decode("iso-8859-1")
    }


def agbinator_scan_musyx(rom):
    return None


def agbinator_scan_gbamodplay(rom):
    return None


def agbinator(filename):
    size = os.path.getsize(filename)
    if size < 0xc0 or size > 0x2000000:
        raise ValueError("Input too small/large")

    result = {"filename": os.path.basename(filename)}
    with open(filename, "rb") as f:
        rom = f.read()

        match_result = agbinator_scan_mp2k(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_gax(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_musyx(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_gbamodplay(rom)
        if match_result:
            result |= match_result
            return result

    return None


def main():
    parser = argparse.ArgumentParser(description="Identify the sound driver from Game Boy Advance ROM.")
    parser.add_argument('filenames', nargs='+', help='GBA ROM to be parsed')
    args = parser.parse_args()

    for filename in itertools.chain.from_iterable(glob.iglob(pattern) for pattern in args.filenames):
        result = agbinator(filename)
        if result:
            print(result)


main()
