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

    # TODO: 0xa9 (copyright) is not the only character used in the metadata text
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

    # example: GAX Sound Engine 3.03A-NJ (Mar  5 2003)
    # from Crash Bandicoot - Purple Ripto's Rampage

    version = {"text": rom[offset + 17:end_offset].decode()}
    m = re.fullmatch(r"v?(\d)\.(\d{1,3})([A-Za-z\-]*)", version["text"])
    if m:
        version["major_version"] = int(m.group(1))
        version["minor_version"] = int(m.group(2))
        version["revision"] = m.group(3)
    return version


def parse_gax_music_v2(rom, offset):
    if offset + 4 >= len(rom):
        return None

    num_handlers = struct.unpack_from("<L", rom, offset)[0]
    if num_handlers < 3 or num_handlers > 255:
        return None
    if offset + 4 + num_handlers * 4 >= len(rom):
        return None

    handlers = struct.unpack_from("<" + "L" * num_handlers, rom, offset + 4)
    for handler_address in handlers:
        if not is_rom_address(handler_address) or handler_address % 4 != 0:
            return None

        handler_offset = to_offset(handler_address)
        if handler_offset + 4 >= len(rom):
            return None

        if struct.unpack_from("<L", rom, handler_offset)[0] == 0:
            continue

        handler_fields = struct.unpack_from("<LLLLLLL", rom, handler_offset)
        if not is_rom_address(handler_fields[0]) or not is_rom_address(handler_fields[1]) or not is_rom_address(handler_fields[2]): # mandatory function pointers
            return None
        num_linked_handlers = handler_fields[3]
        if num_linked_handlers > 255:
            return None

    song_header_handler_address = handlers[1]
    song_header_handler_offset = to_offset(song_header_handler_address)
    song_header_handler_fields = struct.unpack_from("<LLLLLLL", rom, song_header_handler_offset)
    song_header_address = song_header_handler_fields[6]
    if not is_rom_address(song_header_address) or song_header_address % 4 != 0:
        return None
    song_header_offset = to_offset(song_header_address)
    if song_header_offset + 0x20 >= len(rom):
        return None

    fields = struct.unpack_from("<HHHHHHLLLHBBL", rom, offset)
    num_channels = fields[0]
    max_channels = 32  # according to the official GAX page
    if num_channels == 0 or num_channels > max_channels:
        return None

    header = {
        "num_handlers": num_handlers,
        "num_channels": num_channels,
        "pattern_length": fields[1],
        "num_patterns": fields[2],
        "master_volume": fields[4],
        "seq_address": fields[6],
        "instr_address": fields[7],
        "sample_address": fields[8],
    }

    if not is_rom_address(header["seq_address"]) or to_offset(header["seq_address"]) > len(rom) or header["seq_address"] % 4 != 0:
        return None
    if not is_rom_address(header["instr_address"]) or to_offset(header["instr_address"]) > len(rom) or header["instr_address"] % 4 != 0:
        return None
    if not is_rom_address(header["sample_address"]) or to_offset(header["sample_address"]) > len(rom) or header["sample_address"] % 4 != 0:
        return None

    top_channel_handler = sorted(handlers[3:])[0]
    top_channel_handler_offset = to_offset(top_channel_handler)
    if top_channel_handler_offset + 0x1c >= len(rom):
        return None

    info_end_address = struct.unpack_from("<L", rom, top_channel_handler_offset + 0x18)[0]
    if not is_rom_address(info_end_address):
        return None
    header["info"] = parse_song_info(rom, to_offset(info_end_address))

    return header


def parse_gax_music_v3(rom, offset):
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
                gax = {"version": version, "music": {}, "function": {}}
                break

        if not gax:
            return None

        if "major_version" not in version:
            return gax

        if version["major_version"] == 3:
            for offset in range(0, len(rom), 4):
                song_header = parse_gax_music_v3(rom, offset)
                if song_header:
                    gax["music"][to_address(offset)] = song_header

            gax2_estimate_offset = rom.find(b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x82\xb0\x07\x1c\x00\x24\x00\x20\x00\x90')
            if gax2_estimate_offset != -1:
                gax["function"]["gax2_estimate"] = {"address": to_address(gax2_estimate_offset)}

            gax2_new_offset = rom.find(b'\xf0\xb5\x47\x46\x80\xb4\x81\xb0\x06\x1c\x00\x2e')
            if gax2_new_offset != -1:
                gax["function"]["gax2_new"] = {"address": to_address(gax2_new_offset)}

            gax2_init_offset = rom.find(b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x81\xb0\x07\x1c\x00\x26\x0e\x48\x39\x68\x01\x60')
            if gax2_init_offset == -1:
                gax2_init_offset = rom.find(b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x81\xb0\x07\x1c\x00\x22\x0e\x48\x39\x68') # 3.05-ND
            if gax2_init_offset != -1:
                gax["function"]["gax2_init"] = {"address": to_address(gax2_init_offset)}

            gax2_jingle_offset = rom.find(b'\xf0\xb5\x47\x46\x80\xb4\x81\xb0\x80\x46\x0d\x48\x01\x68\x08\x1c\x80\x30\x8c\x6f\x04\x60\x04\x30\xcb\x6f\x03\x60\x4a\x68\xd1\x89')
            if gax2_jingle_offset != -1:
                gax["function"]["gax2_jingle"] = {"address": to_address(gax2_jingle_offset)}

            gax_irq_offset = rom.find(b'\xf0\xb5\x3b\x48\x02\x68\x11\x68\x3a\x48\x81\x42\x6d\xd1\x50\x6d\x00\x28\x6a\xd0\x50\x6d\x01\x28\x1a\xd1\x02\x20\x50\x65\x36\x49')
            if gax_irq_offset == -1:
                gax_irq_offset = rom.find(b'\xf0\xb5\x33\x48\x03\x68\x1a\x68\x32\x49\x07\x1c\x8a\x42\x5b\xd1\x58\x6d\x00\x28\x58\xd0\x58\x6d\x01\x28\x1a\xd1\x02\x20\x58\x65') # 3.05-ND
            if gax_irq_offset != -1:
                gax["function"]["gax_irq"] = {"address": to_address(gax_irq_offset)}

            gax_play_offset = rom.find(b'\x70\xb5\x81\xb0\x47\x48\x01\x68\x48\x6d\x00\x28\x00\xd1')
            if gax_play_offset != -1:
                gax["function"]["gax_play"] = {"address": to_address(gax_play_offset)}

            gax_fx_offset = rom.find(b'\xf0\xb5\x07\x1c\x00\x25\x1c\x4c\xff\x2f\x39\xd8\x00\x22\x1b\x48\x01\x68\x0b\x69\x06\x1c\x9d\x42\x09\xd2\xc8\x68\x01\x6c\xa1\x42')
            if gax_fx_offset != -1:
                gax["function"]["gax_fx"] = {"address": to_address(gax_fx_offset)}

            gax2_fx_offset = rom.find(b'\xf0\xb5\x04\x1c\x00\x2c\x09\xd1\x02\x48\x03\x49')
            if gax2_fx_offset == -1:
                gax2_fx_offset = rom.find(b'\xf0\xb5\x01\x1c\x00\x29\x35\xd0\x0f\x88\x48\x88\x16\x4a\x01\x23\x5b\x42\x9c\x46\x90\x42\x00\xd0\x84\x46\x48\x68\x01\x25\x6d\x42') # 3.05-ND
            if gax2_fx_offset != -1:
                gax["function"]["gax2_fx"] = {"address": to_address(gax2_fx_offset)}

            gax2_new_fx_offset = rom.find(b'\x00\xb5\x01\x1c\x00\x29\x09\xd1\x02\x48\x03\x49')
            if gax2_new_fx_offset == -1:
                gax2_new_fx_offset = rom.find(b'\x01\x1c\x00\x29\x07\xd0\x04\x48\x08\x80\x01\x20\x40\x42\x48\x80\x48\x60\x88\x60\x88\x81\x70\x47\xff\xff\x00\x00') # 3.05-ND
            if gax2_new_fx_offset != -1:
                gax["function"]["gax2_new_fx"] = {"address": to_address(gax2_new_fx_offset)}
        else: # GAX V2
            for offset in range(0, len(rom), 4):
                song_header = parse_gax_music_v2(rom, offset)
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

        if gax["function"]:
            print()
            for name, fn in gax["function"].items():
                print("%-15s %08X" % (name, fn["address"]))


main()
