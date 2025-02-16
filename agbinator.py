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


def decode_country_code(code):
    regions = {
        "C": "CHN",  # China
        "D": "DEU",  # German
        "E": "USA",  # USA
        "F": "FRA",  # ?
        "H": "HOL",  # France
        "I": "ITA",  # Italy
        "J": "JPN",  # Japan
        "K": "KOR",  # Korea
        "P": "EUR",  # Europe
        "Q": "DEN",  # ?
        "S": "ESP",  # Spain
        "U": "AUS",  # ?
        "X": "EUU",  # ?
        "Y": "EUU",  # ?
        "Z": "EUU"  # ?
    }
    return regions.get(code, "XXX")


def make_full_product_id(product_id):
    if product_id[0] == "\0":
        return ""
    else:
        return "AGB-{0:<4}-{1}".format(product_id.split("\0")[0], decode_country_code(product_id[3]))


def agbinator_scan_mp2k(rom):
    m4a_functions = {}

    song_start_patterns = [
        b"\x00\xb5\x00\x04\x07\x4b\x08\x49\x40\x0b\x40\x18\x82\x88\x51\x00\x89\x18\x89\x00\xc9\x18\x0a\x68\x01\x68\x10\x1c",
        b"\x00\xb5\x00\x04\x07\x4a\x08\x49\x40\x0b\x40\x18\x83\x88\x59\x00\xc9\x18\x89\x00\x89\x18\x0a\x68\x01\x68\x10\x1c"]
    for pattern in song_start_patterns:
        offset = rom.find(pattern)
        if offset != -1:
            m4a_functions["m4aSongNumStart"] = offset
            break

    sound_init_patterns = [
        b"\xf0\xb5\x47\x46\x80\xb4\x18\x48\x02\x21\x49\x42\x08\x40\x17\x49\x17\x4a",
        b"\x70\xb5\x14\x48\x02\x21\x49\x42\x08\x40\x13\x49\x13\x4a"]
    for pattern in sound_init_patterns:
        offset = rom.find(pattern)
        if offset != -1:
            m4a_functions["m4aSoundInit"] = offset
            break

    sound_sync_patterns = [
        b'\x00\xb5\x18\x48\x02\x68\x10\x68\x17\x49\x40\x18\x01\x28\x26\xd8\x10\x79\x01\x38\x11\x79\x10\x71\x10\x79\x00\x06\x00\x28\x1e\xdc',
        b'\xa4\x48\x00\x68\xa4\x4a\x03\x68\x9b\x1a\x01\x2b\x11\xd8\x01\x79\x01\x39\x01\x71\x0d\xdc\xc1\x7a\x01\x71\x06\x4a\x91\x68\xc9\x01',
        b'\xa6\x48\x00\x68\xa6\x4a\x03\x68\x9b\x1a\x01\x2b\x0e\xd8\x01\x79\x01\x39\x01\x71\x0a\xdc\xc1\x7a\x01\x71\x00\x20\xb6\x21\x09\x02',
        b'\xa6\x48\x00\x68\xa6\x4a\x03\x68\x9b\x1a\x01\x2b\x11\xd8\x01\x79\x01\x39\x01\x71\x0d\xdc\xc1\x7a\x01\x71\x06\x4a\x91\x68\xc9\x01',
        b'\xa8\x48\x00\x68\xa8\x4a\x03\x68\x9b\x1a\x01\x2b\x18\xd8\x01\x79\x01\x39\x01\x71\x14\xdc\xc1\x7a\x01\x71\x0a\x4a\x91\x68\xc9\x01',
        b'\xaa\x48\x00\x68\xaa\x4a\x03\x68\x9b\x1a\x01\x2b\x18\xd8\x01\x79\x01\x39\x01\x71\x14\xdc\xc1\x7a\x01\x71\x0a\x4a\x91\x68\xc9\x01',
        b'\xe6\x48\x00\x68\xe6\x4a\x03\x68\x9a\x42\x0e\xd1\x01\x79\x01\x39\x01\x71\x0a\xdc\xc1\x7a\x01\x71\x00\x20\xb6\x21\x09\x02\x03\x4a']
    for pattern in sound_sync_patterns:
        offset = rom.find(pattern)
        if offset != -1:
            m4a_functions["m4aSoundSync"] = offset
            break

    if not m4a_functions:
        return None

    if len(m4a_functions) == 3:
        return {
            "driver_name": "MusicPlayer2000",
            "driver_version": ""
        }
    else:
        return {
            "driver_name": "MusicPlayer2000/?",
            "driver_version": ""
        }


def agbinator_scan_gax(rom):
    gax_signature_pattern = re.compile(br"GAX Sound Engine v?(\d)\.(\d{1,3})([A-Za-z\-]*)")
    match_result = gax_signature_pattern.search(rom)
    if not match_result:
        return None

    return {
        "driver_name": "GAX Sound Engine",
        "driver_version": match_result.group().decode("iso-8859-1")
    }


def agbinator_scan_musyx(rom):
    musyx = {"function": {}}
    # TODO: MusyX - improve speed

    snd_init_offset = rom.find(
        b'\x70\xb5\x05\x1c\x0e\x1c\x30\x68\x03\x21\x08\x40\x00\x28\x00\xd0\xb4\xe0\x70\x68\x08\x40\x00\x28\x00\xd0\xaf\xe0\xb0\x68\x08\x40')
    if snd_init_offset == -1:
        snd_init_offset = rom.find(
            b'\xf0\xb5\x47\x46\x80\xb4\x05\x1c\x0e\x1c\x90\x46\x1f\x1c\x00\x2a\x00\xd1\xc1\xe0\x00\x2f\x00\xd1\xbe\xe0\x30\x68\x03\x21\x08\x40')
    if snd_init_offset != -1:
        musyx["function"]["snd_Init"] = {"address": to_address(snd_init_offset)}

    snd_handle_intermediate_offset = rom.find(
        b'\x00\x20\x81\x46\x00\x24\x2a\x48\x03\x68\x4a\x46\x91\x00\x18\x1c\x18\x30\x42\x18\x11\x68\x40\x20\x08\x40\x00\x28\x19\xd0\x41\x20')
    snd_handle_offset = snd_handle_intermediate_offset - 0x2c if snd_handle_intermediate_offset >= 0x2c else -1
    if snd_handle_offset != -1:
        musyx["function"]["snd_Handle"] = {"address": to_address(snd_handle_offset)}

    snd_do_sample_offset = rom.find(
        b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x85\xb0\x31\x4e\x35\x68\x28\x78\x00\x28\x00\xd1\xaa\xe0\x2f\x1c\xd0\x37\x38\x68\x00\x90')
    if snd_do_sample_offset == -1:
        snd_do_sample_offset = rom.find(
            b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x85\xb0\x36\x4d\x2c\x68\x20\x7a\x00\x28\x00\xd1\xb4\xe0\x27\x1c\xd8\x37\x38\x68\x00\x90')
    if snd_do_sample_offset != -1:
        musyx["function"]["snd_DoSample"] = {"address": to_address(snd_do_sample_offset)}

    snd_start_song_offset = rom.find(
        b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x05\x1c\x39\x4a\x13\x68\x88\x21\x49\x00\x58\x18\x00\x68\x81\x69\x40\x18\x00\x68\xa8\x42')
    if snd_start_song_offset == -1:
        snd_start_song_offset = rom.find(
            b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x04\x1c\x3a\x4a\x13\x68\x8c\x21\x49\x00\x58\x18\x00\x68\x81\x69\x40\x18\x00\x68\xa0\x42')
    if snd_start_song_offset != -1:
        musyx["function"]["snd_StartSong"] = {"address": to_address(snd_start_song_offset)}

    snd_resume_song_offset = rom.find(
        b'\x06\x48\x00\x68\x8c\x21\x49\x00\x40\x18\x00\x68\x39\x31\x42\x18\x11\x78\x01\x29\x04\xd0\x00\x20\x06\xe0\x00\x00')
    if snd_resume_song_offset == -1:
        snd_resume_song_offset = rom.find(
            b'\x06\x48\x00\x68\x90\x21\x49\x00\x40\x18\x00\x68\x31\x31\x42\x18\x11\x78\x01\x29\x04\xd0\x00\x20\x06\xe0\x00\x00')
    if snd_resume_song_offset != -1:
        musyx["function"]["snd_ResumeSong"] = {"address": to_address(snd_resume_song_offset)}

    snd_get_sample_working_set_size_offset = rom.find(
        b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x82\xb0\x04\x1c\x0e\x1c\x00\x2e\x01\xd1\x00\x20\xdc\xe0\xa2\x78\x10\x01\x80\x18\x80\x00')
    if snd_get_sample_working_set_size_offset != -1:
        musyx["function"]["snd_GetSampleWorkingSetSize"] = {
            "address": to_address(snd_get_sample_working_set_size_offset)}

    return {
        "driver_name": "MusyX Audio Tools",
        "driver_version": ""
    } if musyx["function"] else None


def agbinator_scan_krawall(rom):
    krawall_rcs_pattern = re.compile(b"\\$Id: Krawall.*?\x00")
    match_result = krawall_rcs_pattern.search(rom)
    if not match_result:
        return None

    return {
        "driver_name": "Krawall",
        "driver_version": match_result.group().split(b"\x00")[0].decode("iso-8859-1")
    }


def agbinator_scan_gbamodplay(rom):
    gbamod_signature_offset = rom.find(b'Logik State')
    if gbamod_signature_offset == -1:
        return None

    return {
        "driver_name": "GBAModPlay/LS_Play",
        "driver_version": ""
    }


def agbinator_scan_kcej(rom):
    offset = rom.find(b'\x50\x18\x01\x88\x80\x20\x80\x01\x08\x40\x00\x04\x05\x0c\x00\x2d')
    if offset != -1 and offset >= 12:
        return {
            "driver_name": "Konami(KCEJ)/GUN",
            "driver_version": "Late"  # Yu-Gi-Oh! World Championship Tournament 2004 etc.
        }

    offset = rom.find(b'\xf0\x7b\x48\x43\x04\x13\x30\x88\x00\x19\x38\x80\x70\x88\x78\x80\xb0\x78\xf8\x80')
    if offset != -1 and offset >= 0x498:
        return {
            "driver_name": "Konami(KCEJ)/GUN",
            "driver_version": "Middle"  # Yu-Gi-Oh! Worldwide Edition: Stairway to the Destined Duel etc.
        }

    offset = rom.find(b'\x08\x0d\x98\x80\x1d\x60\x60\x42\x30\x80\x80\x20\xc0\x01\x02\x40\x00\x2a')
    if offset != -1 and offset >= 0x64:
        return {
            "driver_name": "Konami(KCEJ)/GUN",
            "driver_version": "Early"  # Get Backers - Jigoku no Scaramouche
        }

    return None


def agbinator_scan_natsume(rom):
    offset = rom.find(b'\x42\x18\x11\x88\x0a\x48\x81\x42\x01\xd8\x48\x1c\x10\x80\x18\x1c')
    if offset == -1:
        offset = rom.find(b'\x42\x18\x11\x88\x0b\x48\x81\x42\x01\xd8\x48\x1c\x10\x80\x18\x1c')
        if offset == -1:
            offset = rom.find(b'\x42\x18\x11\x88\x0c\x48\x81\x42\x01\xd8\x48\x1c\x10\x80\x18\x1c')
    if offset == -1 or offset < 10:
        return None

    return {
        "driver_name": "Natsume",
        "driver_version": ""
    }


def agbinator_scan_quintet(rom):
    offset = rom.find(b'\xf0\xb5\x4f\x46\x46\x46\xc0\xb4\x00\x20\x80\x46\x1e\x4e\x20\x21\x89\x19\x89\x46\x00\x27\x30\x1c\x1c\x30\x3d\x18\x29\x68\x01\x20')
    if offset == -1:
        return None

    return {
        "driver_name": "Quintet",
        "driver_version": ""
    }


def agbinator_scan_gstyle(rom):
    offset = rom.find(b'\x00\xb5\x01\x1c\x05\x48\x89\x00\x00\x68\x40\x18\x01\x68\x40\x18\x04\x30\x00\x21')
    if offset == -1:
        return None

    return {
        "driver_name": "G-Style",
        "driver_version": ""
    }


def agbinator_scan_mobius(rom):
    offset = rom.find(b'\x00\xb5\x05\x4b\x1b\x6c\x80\x00\xc0\x18\x42\x68\x9b\x18\x18\x1c')
    if offset == -1:
        return None

    return {
        "driver_name": "Mobius Entertainment",
        "driver_version": ""
    }


def agbinator_scan_webfoot(rom):
    offset = rom.find(b'\x70\xb5\x01\x25\x85\x70\x05\x70\x00\x22\x42\x70\xc1\x60\x04\x1c\x48\x7c\xe0\x70\xd0\x43\x20\x61\x00\x20\x43\x00\x1b\x18\x5b\x01')
    if offset == -1:
        offset = rom.find(
            b'\x70\xb5\x10\x4c\x01\x26\xa6\x70\x05\x1c\x00\x20\xe6\x70\x60\x70\xe5\x60\x68\x7a\x20\x71\x70\x42\xe0\x80') # Legacy of Goku
    if offset == -1:
        return None

    return {
        "driver_name": "Webfoot Technologies",
        "driver_version": ""
    }


def agbinator_scan_rare(rom):
    offset = rom.find(b'\xf0\xb5\x43\x46\x4c\x46\x55\x46\x5e\x46\x67\x46\xf8\xb4')
    if offset == -1:
        return None

    offset_temp = rom.find(b'\x49\x08\x60\xf8\xbc\x98\x46\xa1\x46\xaa\x46\xb3\x46\xbc\x46\xf0\xbc', offset + 14)
    if offset_temp == -1:
        return None

    return {
        "driver_name": "Rare",
        "driver_version": ""
    }


def agbinator_scan_scm3lt(rom):
    # Not very appropriate. The following scan detects patterns outside of the driver's code.
    signature_pattern = re.compile(b"SCM3LT Ver.*?\x00")
    match_result = signature_pattern.search(rom)
    if match_result:
        return {
            "driver_name": "SCM3LT",
            "driver_version": match_result.group().split(b"\x00")[0].decode("iso-8859-1")
        }
    else:
        offset = rom.find(b'\x82\x72\x82\x62\x82\x6c\x82\x52\x82\x6b\x82\x73') # Shift_JIS full-width "SCM3LT"
        if offset == -1:
            return None

    return {
        "driver_name": "SCM3LT",
        "driver_version": ""
    }


def agbinator_scan_torus(rom):
    offset = rom.find(b'\x0b\x1c\x18\x78\xc1\x08\x24\xd3\x04\x22\x12\x06\xbc\x32\x98\x69\x40\x08')
    if offset == -1:
        return None

    return {
        "driver_name": "Torus Games",
        "driver_version": ""
    }

def agbinator_scan_brownie_brown(rom):
    # Scan for SoundMain fragments written in ARM
    offset = rom.find(b'\x02\x00\x51\xe1\x00\x10\xa0\x43\x02\x10\x41\x50\x00\x10\xc0\xe5\xa1\x22\xa0\xe1\x02\x32\xa0\xe1\x02\x20\x83\xe0')
    if offset == -1:
        return None

    return {
        "driver_name": "Brownie Brown",
        "driver_version": ""
    }

def agbinator_scan_alphadream(rom):
    offset = rom.find(b'\x78\x01\x20\10\x43\x08\x70\x31\x68\xc9\x18\x??\x19\x0a\x78\xfd\x20\x10\x40\x08\x70\x0e\x48')
    if offset == -1:
        return None

    return {
        "driver_name": "AlphaDream",
        "driver_version": ""
    }
    
def agbinator_scan_quickthunder(rom):
    offset = rom.find(b'\x80\x00\x37\x49\x09\x18\x37\x4a\x4c\x78\x01\x34\xd3\x7f\x9c\x42')
    if offset == -1:
        return None

    return {
        "driver_name": "QuickThunder",
        "driver_version": ""
    }

def agbinator_scan_engine_software(rom):
    offset = rom.find(b'\x1c\x35\x22\x35\x29\x35\x2f\x35\x35\x35\x3b\x35\x41\x35\x47\x35\x4d\x35\x54')
    if offset == -1:
        return None

    return {
        "driver_name": "Engine Software",
        "driver_version": ""
    }

def agbinator_scan_gbass(rom):
    offset = rom.find(b'\x04\xcc\x00\x00\x04\x0a\x4b\x0b\x49\x0b\x4c\x0c\x4d\x68\x78\x0c\x4b\x00\x28\x00\xd0')
    if offset == -1:
        return None

    return {
        "driver_name": "GBASS/Paragon 5",
        "driver_version": ""
    }

def agbinator_scan_sonix(rom):
    offset = rom.find(b'\x10\x21\x82\x78\x0a\x43\x82\x70\x??\xe7')
    if offset == -1:
        return None

    return {
        "driver_name": "Sonix Audio Tools",
        "driver_version": ""
    }

def agbinator_scan_apex(rom):
    offset = rom.find(b'\xb2\x42\x00\xdb\x1f\x22\x5d\x01\x4b\x19\x91\x02\x5d\x18\x??\x46\x15\x80\x02')
    if offset == -1:
        return None

    offset_temp = rom.find(b'\xb2\x42\x09\xdA\x8b\x68\x44\x46\x1b\x1b\x1b\x12')
    if offset_temp == -1:
        return None

    return {
        "driver_name": "Apex",
        "driver_version": ""
    }

def agbinator_scan_bit_managers(rom):
    offset = rom.find(b'\xc9\x0e\x2b\x0f\x8d\x0f\xee\x0f\x4f\x10')
    if offset == -1:
        return None

    return {
        "driver_name": "Bit Managers",
        "driver_version": ""
    }

def agbinator_scan_paul_tonge(rom):
    offset = rom.find(b'\x09\x01\xc8\x18\x84\x46\x64\x46\x24\x34')
    if offset == -1:
        return None

    return {
        "driver_name": "Paul Tonge",
        "driver_version": ""
    }

def agbinator_scan_mark_cooksey(rom):
    offset = rom.find(b'\x9d\x07\x6b\xca\x23\x78\xc7\x12\x59\x9c\xdb\x17\x4f\x84\xb6\xe5\x12\x3c\x64')
    if offset == -1:
        return None

    return {
        "driver_name": "Mark Cooksey",
        "driver_version": ""
    }

def agbinator_scan_ugba_player(rom):
    offset = rom.find(b'\x30\x80\xbd\x18\x72\xfd\xff\xeb\x83\xfd\xff\xeb\x30\x40\xbd\xe8\xb2\xfc\xff\xea\x70\x40\x2d\xe9\c42\xf3\xff\xeb\x3d\xf8')
    if offset == -1:
        return None

    return {
        "driver_name": "UGBA Player",
        "driver_version": ""
    }

def agbinator_scan_ubisoft_milan(rom):
    offset = rom.find(b'\x02\xf0\xb5\x4f\x46\x46\x46\xc0\xb4\x83\xb0\x81\x46\x0e\x1c\x77\x1c\x71\x78\x78\x78\x00\x02\x01\x43')
    if offset == -1:
        return None

    return {
        "driver_name": "Ubisoft Milan",
        "driver_version": ""
    }
    
def agbinator(filename):
    size = os.path.getsize(filename)
    if size < 0xc0 or size > 0x2000000:
        raise ValueError("Input too small/large")

    with open(filename, "rb") as f:
        rom = f.read()

        internal_name = rom[0xa0:0xac].split(b'\x00', 1)[0].decode()
        product_id = rom[0xac:0xb0].decode()
        full_product_id = make_full_product_id(product_id)
        result = {
            "filename": os.path.basename(filename),
            "internal_name": internal_name,
            "product_id": product_id,
            "full_product_id": full_product_id
        }

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

        match_result = agbinator_scan_krawall(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_gbamodplay(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_kcej(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_natsume(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_quintet(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_gstyle(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_mobius(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_webfoot(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_rare(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_scm3lt(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_torus(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_brownie_brown(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_alphadream(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_quickthunder(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_engine_software(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_gbass(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_sonix(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_apex(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_bit_managers(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_paul_tonge(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_mark_cooksey(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_ugba_player(rom)
        if match_result:
            result |= match_result
            return result

        match_result = agbinator_scan_ubisoft_milan(rom)
        if match_result:
            result |= match_result
            return result

        return result


def main():
    parser = argparse.ArgumentParser(description="Identify the sound driver from Game Boy Advance ROM.")
    parser.add_argument('filenames', nargs='+', help='GBA ROM to be parsed')
    args = parser.parse_args()

    for filename in itertools.chain.from_iterable(glob.iglob(pattern) for pattern in args.filenames):
        result = agbinator(filename)
        print("{0}\t{1}\t{2}\t{3}\t{4}"
              .format(result.get("internal_name"),
                      result.get("full_product_id"),
                      result.get("driver_name", ""),
                      result.get("driver_version", ""),
                      result.get("filename")))


main()
