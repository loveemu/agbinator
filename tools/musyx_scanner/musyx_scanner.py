import argparse
import os


def is_rom_address(address):
    return 0x8000000 <= address <= 0x9ffffff


def to_address(offset):
    return 0x8000000 + offset


def to_offset(address):
    return address - 0x8000000


def musyx_scan(filename):
    size = os.path.getsize(filename)
    if size < 0xc0 or size > 0x2000000:
        raise ValueError("Input too small/large")

    musyx = {"function": {}}
    with open(filename, "rb") as f:
        rom = f.read()

        # Library version detection may improve scanning speed, but is not planned for now.

        snd_init_offset = rom.find(b'\x70\xb5\x05\x1c\x0e\x1c\x30\x68\x03\x21\x08\x40\x00\x28\x00\xd0\xb4\xe0\x70\x68\x08\x40\x00\x28\x00\xd0\xaf\xe0\xb0\x68\x08\x40')
        if snd_init_offset == -1:
            snd_init_offset = rom.find(b'\xf0\xb5\x47\x46\x80\xb4\x05\x1c\x0e\x1c\x90\x46\x1f\x1c\x00\x2a\x00\xd1\xc1\xe0\x00\x2f\x00\xd1\xbe\xe0\x30\x68\x03\x21\x08\x40')
        if snd_init_offset != -1:
            musyx["function"]["snd_Init"] = {"address": to_address(snd_init_offset)}

        snd_handle_intermediate_offset = rom.find(b'\x00\x20\x81\x46\x00\x24\x2a\x48\x03\x68\x4a\x46\x91\x00\x18\x1c\x18\x30\x42\x18\x11\x68\x40\x20\x08\x40\x00\x28\x19\xd0\x41\x20')
        if snd_handle_intermediate_offset == -1:
            snd_handle_intermediate_offset = rom.find(b'\x00\x20\x81\x46\x00\x24\x2A\x48\x03\x68\x4A\x46\x91\x00\x18\x1C\x10\x30\x42\x18\x11\x68\x40\x20\x08\x40\x00\x28\x18\xD0\x41\x20')
        snd_handle_offset = snd_handle_intermediate_offset - 0x2c if snd_handle_intermediate_offset >= 0x2c else -1
        if snd_handle_offset != -1:
            musyx["function"]["snd_Handle"] = {"address": to_address(snd_handle_offset)}

        snd_do_sample_offset = rom.find(b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x85\xb0\x31\x4e\x35\x68\x28\x78\x00\x28\x00\xd1\xaa\xe0\x2f\x1c\xd0\x37\x38\x68\x00\x90')
        if snd_do_sample_offset == -1:
            snd_do_sample_offset = rom.find(b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x85\xb0\x36\x4d\x2c\x68\x20\x78\x00\x28\x00\xd1\xb4\xe0\x27\x1c\xd0\x37\x38\x68\x00\x90')
            if snd_do_sample_offset == -1:
                snd_do_sample_offset = rom.find(b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x85\xb0\x36\x4d\x2c\x68\x20\x7a\x00\x28\x00\xd1\xb4\xe0\x27\x1c\xd8\x37\x38\x68\x00\x90')
        if snd_do_sample_offset != -1:
            musyx["function"]["snd_DoSample"] = {"address": to_address(snd_do_sample_offset)}

        snd_start_song_offset = rom.find(b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x05\x1c\x39\x4a\x13\x68\x88\x21\x49\x00\x58\x18\x00\x68\x81\x69\x40\x18\x00\x68\xa8\x42')
        if snd_start_song_offset == -1:
            snd_start_song_offset = rom.find(b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x04\x1c\x3a\x4a\x13\x68\x8c\x21\x49\x00\x58\x18\x00\x68\x81\x69\x40\x18\x00\x68\xa0\x42')
        if snd_start_song_offset != -1:
            musyx["function"]["snd_StartSong"] = {"address": to_address(snd_start_song_offset)}

        snd_resume_song_offset = rom.find(b'\x06\x48\x00\x68\x8c\x21\x49\x00\x40\x18\x00\x68\x39\x31\x42\x18\x11\x78\x01\x29\x04\xd0\x00\x20\x06\xe0\x00\x00')
        if snd_resume_song_offset == -1:
            snd_resume_song_offset = rom.find(b'\x06\x48\x00\x68\x90\x21\x49\x00\x40\x18\x00\x68\x31\x31\x42\x18\x11\x78\x01\x29\x04\xd0\x00\x20\x06\xe0\x00\x00')
            if snd_resume_song_offset == -1:
                snd_resume_song_offset = rom.find(b'\x00\xb5\x06\x48\x00\x68\x90\x21\x49\x00\x40\x18\x00\x68\x31\x31\x42\x18\x11\x78\x01\x29\x03\xd0\x00\x20\x05\xe0')
        if snd_resume_song_offset != -1:
            musyx["function"]["snd_ResumeSong"] = {"address": to_address(snd_resume_song_offset)}

        snd_get_sample_working_set_size_offset = rom.find(b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x82\xb0\x04\x1c\x0e\x1c\x00\x2e\x01\xd1\x00\x20\xdc\xe0\xa2\x78\x10\x01\x80\x18\x80\x00')
        if snd_get_sample_working_set_size_offset != -1:
            musyx["function"]["snd_GetSampleWorkingSetSize"] = {"address": to_address(snd_get_sample_working_set_size_offset)}

    return musyx if musyx["function"] else None


def main():
    parser = argparse.ArgumentParser(description="Scanner for Factor 5 MusyX Engine (GBA)")
    parser.add_argument('filename', help='GBA ROM to be parsed')
    args = parser.parse_args()

    musyx = musyx_scan(args.filename)
    if musyx:
        print("MusyX for GBA")

        if musyx["function"]:
            print()
            for name, fn in musyx["function"].items():
                print("%-15s %08X" % (name, fn["address"]))


main()
