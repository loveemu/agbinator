import argparse
import os
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

    return rom[start_offset:end_offset].decode("iso-8859-1")


def parse_gax_music_header(rom, offset):
    # Only GAX ENGINE V3 is supported
    if offset + 200 > len(rom):
        return None

    num_tracks = struct.unpack_from("<H", rom, offset)[0]
    max_tracks = 32  # the number is randomly determined
    if num_tracks == 0 or num_tracks > max_tracks:
        return None

    header = {
        "num_tracks": num_tracks,
        "pattern_length": struct.unpack_from("<H", rom, offset + 2)[0],
        "num_patterns": struct.unpack_from("<H", rom, offset + 4)[0],
        "seq_address": struct.unpack_from("<L", rom, offset + 0xc)[0],
        "instr_address": struct.unpack_from("<L", rom, offset + 0x10)[0],
        "sample_address": struct.unpack_from("<L", rom, offset + 0x14)[0],
    }

    if not is_rom_address(header["seq_address"]) or to_offset(header["seq_address"]) > len(rom):
        return None
    if not is_rom_address(header["instr_address"]) or to_offset(header["instr_address"]) > len(rom):
        return None
    if not is_rom_address(header["sample_address"]) or to_offset(header["sample_address"]) > len(rom):
        return None

    header["tracks"] = []
    for addr in struct.unpack_from("<" + "L" * num_tracks, rom, offset + 0x20):
        if not is_rom_address(addr):
            return None
        header["tracks"].append({"address": addr})

    for addr in struct.unpack_from("<" + "L" * (max_tracks - num_tracks), rom, offset + 0x20 + num_tracks * 4):
        if addr != 0:
            return None

    header["info"] = parse_song_info(rom, to_offset(header["tracks"][0]["address"]))
    return header


def gax_scan(filename):
    size = os.path.getsize(filename)
    if size < 0xc0 or size > 0x2000000:
        raise ValueError("Input too small/large")

    gax = {"music": {}}
    with open(filename, "rb") as f:
        rom = f.read()

        for offset in range(0, len(rom), 4):
            song_header = parse_gax_music_header(rom, offset)
            if song_header:
                gax["music"][to_address(offset)] = song_header

    return gax if len(gax["music"]) > 0 else None


def main():
    parser = argparse.ArgumentParser(description="Data Scanner for Shin'en GAX Sound Engine")
    parser.add_argument('filename', help='GBA ROM to be parsed')
    args = parser.parse_args()

    gax = gax_scan(args.filename)
    if gax:
        print("%d songs" % len(gax["music"]))
        for address, header in gax["music"].items():
            print("%08X %s" % (address, header["info"]))


main()
