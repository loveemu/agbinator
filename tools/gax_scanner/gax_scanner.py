import argparse
import os
import re
import struct


def is_rom_address(address):
    return 0x8000000 <= address <= 0x9ffffff


def to_address(offset):
    return 0x8000000 + offset


def to_offset(address):
    return address - 0x8000000


def parse_song_info(rom, end_offset):
    # adjust alignment
    for i in range(4):
        if end_offset == 0:
            return ""
        if rom[end_offset - 1] != 0:
            break
        end_offset -= 1

    start_offset = end_offset
    while 0x20 <= rom[start_offset - 1] <= 0x7e or rom[start_offset - 1] == 0xa9:
        start_offset -= 1

    while rom[start_offset] != ord('"'):
        start_offset += 1
    while rom[start_offset + 1] == ord('"'):
        start_offset += 1

    return rom[start_offset:end_offset].decode("iso-8859-1")


def parse_gax_version(rom, offset):
    if offset + 17 >= len(rom):
        return None
    if rom[offset:offset + 17] != b'GAX Sound Engine ':
        return None

    end_offset = offset + 17
    while rom[end_offset:end_offset + 1] != b' ':
        end_offset += 1
        if end_offset >= len(rom):
            return None

    version = {"text": rom[offset + 17:end_offset].decode()}
    m = re.fullmatch(r"(\d)\.(\d{1,3})([A-Za-z]?)", version["text"])
    if m:
        version["major_version"] = int(m.group(1))
        version["minor_version"] = int(m.group(2))
        version["revision"] = m.group(3)
    return version


def parse_gax_music_header_v3(rom, offset):
    if offset + 0x20 >= len(rom):
        return None

    fields = struct.unpack_from("<HHHHHHLLLHHHH", rom, offset)
    num_channels = fields[0]
    max_channels = 32  # according to the official GAX page
    if num_channels == 0 or num_channels > max_channels:
        return None

    header = {
        "num_channels": num_channels,
        "pattern_length": fields[1],
        "num_patterns": fields[2],
        "master_volume": fields[4],
        "seq_address": fields[6],
        "instr_address": fields[7],
        "sample_address": fields[8],
    }

    if fields[12] != 0:
        return None

    if not is_rom_address(header["seq_address"]) or to_offset(header["seq_address"]) > len(rom) or header["seq_address"] % 4 != 0:
        return None
    if not is_rom_address(header["instr_address"]) or to_offset(header["instr_address"]) > len(rom) or header["instr_address"] % 4 != 0:
        return None
    if not is_rom_address(header["sample_address"]) or to_offset(header["sample_address"]) > len(rom) or header["sample_address"] % 4 != 0:
        return None

    if offset + 0x20 + (num_channels * 4) >= len(rom):
        return None

    channel_addresses = []
    for addr in struct.unpack_from("<" + "L" * num_channels, rom, offset + 0x20):
        if not is_rom_address(addr) or addr % 4 != 0:
            return None
        channel_addresses.append(addr)

    header["channels"] = []
    for addr in channel_addresses:
        header["channels"].append({"address": addr})

    # channel address list is not sorted sometimes (test case: Finding Nemo)
    header["info"] = parse_song_info(rom, to_offset(sorted(channel_addresses)[0]))
    return header


def gax_scan(filename):
    size = os.path.getsize(filename)
    if size < 0xc0 or size > 0x2000000:
        raise ValueError("Input too small/large")

    gax = None
    with open(filename, "rb") as f:
        rom = f.read()

        for offset in range(0, len(rom), 4):
            version = parse_gax_version(rom, offset)
            if version:
                gax = {"version": version, "music": {}}
                break

        if not gax:
            return None

        if version["major_version"] != 3:
            return gax

        for offset in range(0, len(rom), 4):
            song_header = parse_gax_music_header_v3(rom, offset)
            if song_header:
                gax["music"][to_address(offset)] = song_header

    return gax


def main():
    parser = argparse.ArgumentParser(description="Data Scanner for Shin'en GAX Sound Engine")
    parser.add_argument('filename', help='GBA ROM to be parsed')
    args = parser.parse_args()

    gax = gax_scan(args.filename)
    if gax:
        print("GAX Sound Engine " + gax["version"]["text"])
        print("%d songs" % len(gax["music"]))
        for address, header in gax["music"].items():
            print("%08X %s" % (address, header["info"]))


main()
