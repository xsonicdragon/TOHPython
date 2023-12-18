import os
import shutil

from .ToolsTales import ToolsTales
from pathlib import Path
import pyjson5 as json
import subprocess
import datetime
import lxml.etree as etree
from pythonlib.formats.FileIO import FileIO
from pythonlib.formats.fps4 import Fps4
from pythonlib.formats.tss import Tss
import re
import io
from tqdm import tqdm
import struct
class ToolsTOH(ToolsTales):

    def __init__(self, project_file: Path, insert_mask: list[str], changed_only: bool = False) -> None:
        os.environ["PATH"] += os.pathsep + os.path.join( os.getcwd(), 'pythonlib', 'utils')
        base_path = project_file.parent
        self.folder_name = 'TOH'
        self.jsonTblTags = {}
        self.ijsonTblTags = {}
        with open(project_file, encoding="utf-8") as f:
            json_raw = json.load(f)

        self.paths: dict[str, Path] = {k: base_path / v for k, v in json_raw["paths"].items()}
        self.main_exe_name = json_raw["main_exe_name"]
        self.asm_file = json_raw["asm_file"]

        # super().__init__("TOR", str(self.paths["encoding_table"]), "Tales-Of-Rebirth")

        with open(self.paths["encoding_table"], encoding="utf-8") as f:
            json_raw = json.load(f)

        for k, v in json_raw.items():
            self.jsonTblTags[k] = {int(k2, 16): v2 for k2, v2 in v.items()}


        for k, v in self.jsonTblTags.items():
            if k in ['TAGS', 'TBL']:
                self.ijsonTblTags[k] = {v2:k2 for k2, v2 in v.items()}
            else:
                self.ijsonTblTags[k] = {v2: hex(k2).replace('0x', '').upper() for k2, v2 in v.items()}
        self.iTags = {v2.upper(): k2 for k2, v2 in self.jsonTblTags['TAGS'].items()}
        self.id = 1

        # byteCode
        self.story_byte_code = b"\xF8"
        self.story_struct_byte_code = [b'\x0E\x10\x00\x0C\x04', b'\x00\x10\x00\x0C\x04']
        self.VALID_VOICEID = [r'(VSM_\w+)', r'(VCT_\w+)', r'(S\d+)', r'(C\d+)']
        self.list_status_insertion: list[str] = ['Done']
        self.list_status_insertion.extend(insert_mask)
        self.changed_only = changed_only
        self.repo_path = str(base_path)
        self.file_dict = {
            "skit": "data/fc",
            "story": "data/m"
        }

    def extract_Iso(self, game_iso: Path) -> None:

        #Extract all the files
        extract_to = self.paths["original_files"]
        #self.clean_folder(extract_to)

        path = self.folder_name / extract_to
        args = ['ndstool', '-x', os.path.basename(game_iso),
                '-9', path/'arm9.bin',
                '-7', path/'arm7.bin',
                '-y9', path/'y9.bin',
                '-y7', path/'y7.bin',
                '-d', path/'data',
                '-y', path/'overlay',
                '-t', path/'banner.bin',
                '-h', path/'header.bin']

        wrk_dir = os.path.normpath(os.getcwd() + os.sep + os.pardir)
        subprocess.run(args, cwd=wrk_dir)

        #Update crappy arm9.bin to tinke's version
        with open(self.folder_name / extract_to / 'arm9.bin', "rb+") as f:
            data = f.read()
            f.seek(len(data) - 12)
            f.truncate()

        #Copy to patched folder
        shutil.copytree(os.path.join('..', self.folder_name, self.paths["original_files"]), os.path.join('..', self.folder_name, self.paths["final_files"]), dirs_exist_ok=True)

    def make_iso(self, game_iso) -> None:
        #Clean old builds and create new one
        self.clean_builds(self.paths["game_builds"])

        # Set up new iso name and copy original iso in the folder
        n: datetime.datetime = datetime.datetime.now()
        new_iso = f"TalesofHearts_{n.year:02d}{n.month:02d}{n.day:02d}{n.hour:02d}{n.minute:02d}.nds"
        shutil.copy(game_iso, self.paths['game_builds'] / new_iso)

        path = self.folder_name / self.paths["final_files"]

        args = ['ndstool', '-c', new_iso,
                '-9', path / 'arm9.bin',
                '-7', path / 'arm7.bin',
                '-y9', path / 'y9.bin',
                '-y7', path / 'y7.bin',
                '-d', path / 'data',
                '-y', path / 'overlay',
                '-t', path / 'banner.bin',
                '-h', path / 'header.bin']

        subprocess.run(args, cwd=self.paths["game_builds"])


    def decompress_arm9(self):

        #Copy the original file in a ARM9 folder
        new_arm9 = self.paths['extracted_files'] / 'arm9' / 'arm9.bin'
        new_arm9.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.paths['original_files'] / 'arm9.bin', new_arm9)

        #Decompress the file using blz
        args = ['blz', '-d', 'arm9.bin']
        subprocess.run(args, cwd=new_arm9.parent)

    def compress_arm9(self):

        shutil.copy(self.paths['temp_files'] / 'arm9' / 'arm9.bin', self.paths['final_files'] / 'arm9.bin')

        #Copy the original file in a ARM9 folder

        #Decompress the file using blz
        args = ['blz', '-en9', 'arm9.bin']
        subprocess.run(args, cwd=self.paths['final_files'] )

        # Update crappy arm9.bin to tinke's version
        with open(self.paths['final_files'] / 'arm9.bin', "rb+") as f:
            data = f.read()
            f.seek(len(data) - 12)
            #f.truncate()
    def clean_folder(self, path: Path) -> None:
        target_files = list(path.iterdir())
        if len(target_files) != 0:
            print("Cleaning folder...")
            for file in target_files:
                if file.is_dir():
                    shutil.rmtree(file)
                elif file.name.lower() != ".gitignore":
                    file.unlink(missing_ok=False)


    def clean_builds(self, path: Path) -> None:
        target_files = sorted(list(path.glob("*.nds")), key=lambda x: x.name)[:-4]
        if len(target_files) != 0:
            print("Cleaning builds folder...")
            for file in target_files:
                print(f"deleting {str(file.name)}...")
                file.unlink()

    def get_style_pointers(self, file: FileIO, ptr_range: tuple[int, int], base_offset: int, style: str) -> tuple[
        list[int], list[int]]:

        file.seek(ptr_range[0])
        pointers_offset: list[int] = []
        pointers_value: list[int] = []
        split: list[str] = [ele for ele in re.split(r'([PT])|(\d+)', style) if ele]

        while file.tell() < ptr_range[1]:
            for step in split:
                if step == "P":
                    off = file.read_uint32()
                    if base_offset != 0 and off == 0: continue

                    if file.tell() - 4 < ptr_range[1]:
                        pointers_offset.append(file.tell() - 4)
                        pointers_value.append(off - base_offset)
                elif step == "T":
                    off = file.tell()
                    pointers_offset.append(off)
                    pointers_value.append(off)
                else:
                    file.read(int(step))

        return pointers_offset, pointers_value

    def create_Node_XML(self, root, list_informations, section, entry_type:str, max_len = 0, ) -> None:
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = section

        for text, pointer_offset, emb in list_informations:
            self.create_entry(strings_node, pointer_offset, text, entry_type, -1, "")
            #self.create_entry(strings_node, pointers_offset, text, emb, max_len)
    def extract_all_menu(self) -> None:
        print("Extracting Menu Files...")

        #xml_path = self.paths["menu_xml"]
        xml_path = self.paths["menu_original"]
        xml_path.mkdir(exist_ok=True)

        # Read json descriptor file
        print(f'opening menu_table: {self.paths["menu_table"]}')
        with open(self.paths["menu_table"], encoding="utf-8") as f:
            menu_json = json.load(f)

        for entry in tqdm(menu_json):

            if entry["file_path"] == "${main_exe}":
                file_path = self.paths["extracted_files"] / "arm9" / self.main_exe_name
            else:
                file_path = self.paths["extracted_files"] / entry["file_path"]

            print(f'file path: {file_path}')
            with FileIO(file_path, "rb") as f:
                xml_data = self.extract_menu_file(entry, f)

            with open(xml_path / (entry["friendly_name"] + ".xml"), "wb") as xmlFile:
                xmlFile.write(xml_data)

            self.id = 1
    def extract_menu_file(self, file_def, f: FileIO) -> bytes:

        base_offset = file_def["base_offset"]
        xml_root = etree.Element("MenuText")

        print(file_def['sections'])
        for section in file_def['sections']:
            max_len = 0
            pointers_start = int(section["pointers_start"])
            pointers_end = int(section["pointers_end"])

            # Extract Pointers list out of the file
            pointers_offset, pointers_value = self.get_style_pointers(f, (pointers_start, pointers_end), base_offset,
                                                                      section['style'])
            if 'pointers_alone' in section.keys():
                for ele in section['pointers_alone']:
                    f.seek(ele, 0)
                    pointers_offset.append(f.tell())
                    off = f.read_uint32() - base_offset
                    pointers_value.append(off)

            print([hex(pointer_off) for pointer_off in pointers_offset])
            # Make a list, we also merge the emb pointers with the
            # other kind in the case they point to the same text
            temp = dict()
            for off, val in zip(pointers_offset, pointers_value):

                #print(f'Pointer offset: {hex(off)}')
                text = self.bytes_to_text(f, val)
                temp.setdefault(text, dict()).setdefault("ptr", []).append(off)

            # Remove duplicates
            list_informations = [(k, str(v['ptr'])[1:-1], v.setdefault('emb', None)) for k, v in temp.items()]

            # Build the XML Structure with the information
            if section['style'][0] == "T": max_len = int(section['style'][1:])
            self.create_Node_XML(xml_root, list_informations, section['section'], "String", max_len)

        # Remove duplicates
        # list_informations = self.remove_duplicates(section_list, pointers_offset_list, texts)
        list_informations = [(k, str(v['ptr'])[1:-1], v.setdefault('emb', None)) for k, v in temp.items()]

        # Build the XML Structure with the information
        #if len(list_informations) != 0:
        #    self.create_Node_XML(xml_root, list_informations, "MIPS PTR TEXT")

        # Write to XML file
        return etree.tostring(xml_root, encoding="UTF-8", pretty_print=True)

    def unpack_menu_files(self):
        base_path = self.paths['extracted_files'] / 'data/menu'/ 'monsterbook'
        fps4 = Fps4(detail_path=self.paths['original_files'] / 'data/menu' / 'monsterbook' / 'EnemyIcon.dat',
                    header_path=self.paths['original_files'] / 'data/menu' / 'monsterbook' / 'EnemyIcon.b')
        fps4.extract_files(base_path, decompressed=False)

        for file in fps4.files:
            file_path = self.paths['extracted_files'] / 'data/menu/monsterbook/' / file.name
            enemy_fps4 = Fps4(header_path=file_path)
            print(file_path.with_suffix(''))
            enemy_fps4.extract_files(file_path.with_suffix(''), decompressed=True)

    def bytes_to_text(self, src: FileIO, offset: int = -1) -> str:
        finalText = ""
        tags = self.jsonTblTags['TAGS']
        chars = self.jsonTblTags['TBL']

        if (offset > 0):
            src.seek(offset, 0)

        while True:
            b = src.read(1)
            if b == b"\x00": break

            b = ord(b)

            #Button
            if b == 0x81:
                next_b = src.read(1)
                if ord(next_b) in self.jsonTblTags['BUTTON'].keys():
                    finalText += f"<{self.jsonTblTags['BUTTON'].get(ord(next_b))}>"
                    continue
                else:
                    src.seek(src.tell()-1,0)

            # Custom Encoded Text
            if (0x80 <= b <= 0x9F) or (0xE0 <= b <= 0xEA):
                c = (b << 8) | src.read_uint8()
                finalText += chars.get(c, "{%02X}{%02X}" % (c >> 8, c & 0xFF))
                continue

            if b == 0xA:
                finalText += ("\n")
                continue

            #Voice Id
            elif b in [0x9]:

                val = ""
                while src.read(1) != b"\x29":
                    src.seek(src.tell() - 1)
                    val += src.read(1).decode("cp932")
                val += ">"
                val = val.replace('(', '<')

                finalText += val
                continue

            # ASCII text
            if chr(b) in self.PRINTABLE_CHARS:
                finalText += chr(b)
                continue

            # cp932 text
            if 0xA0 < b < 0xE0:
                finalText += struct.pack("B", b).decode("cp932")
                continue



            if b in [0x3, 0x4, 0xB]:
                b_value = b''

                if ord(src.read(1))== 0x28:
                    tag_name = self.jsonTblTags['TAGS'].get(b)

                    b_v = b''
                    while b_v != b'\x29':
                        b_v = src.read(1)
                        b_value += b_v
                    b_value = b_value[:-1]

                    parameter = int.from_bytes(b_value, "big")
                    tag_param = self.jsonTblTags.get(tag_name.upper(), {}).get(parameter, None)

                    if tag_param is not None:
                        finalText += f"<{tag_param}>"
                    else:
                        finalText += f"<{tag_name}:{parameter}>"

                    continue

            if b == 0xC:

                finalText += "<Bubble>"
                continue
            # Simple Tags
            #if 0x3 <= b <= 0xF:
            #    parameter = src.read_uint32()

            #    tag_name = tags.get(b, f"{b:02X}")
            #    tag_param = self.jsonTblTags.get(tag_name.upper(), {}).get(parameter, None)

            #    if tag_param is not None:
            #        finalText += f"<{tag_param}>"
            #    else:
            #        finalText += f"<{tag_name}:{parameter:X}>"

            #    continue

            # None of the above
            finalText += "{%02X}" % b

        return finalText

    def pack_all_menu(self) -> None:
        print("Packing Menu Files...")

        xml_path = self.paths["menu_xml"]
        out_path = self.paths["temp_files"]

        # Read json descriptor file
        with open(self.paths["menu_table"], encoding="utf-8") as f:
            menu_json = json.load(f)

        for entry in tqdm(menu_json):


            if entry["friendly_name"] in ['Arm9', 'Consumables', 'Sorma Skill']:
                if entry["file_path"] == "${main_exe}":
                    file_path = self.paths["extracted_files"] / 'arm9' / self.main_exe_name
                    file_last = self.main_exe_name
                else:
                    file_path = self.paths["extracted_files"] / entry["file_path"]
                    file_last = entry["file_path"]

                # Copy original files
                orig = self.paths["extracted_files"] / entry["file_path"]
                dest = self.paths["temp_files"] / entry["file_path"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(orig, dest)

                base_offset = entry["base_offset"]
                pools: list[list[int]] = [[x[0], x[1] - x[0]] for x in entry["safe_areas"]]
                pools.sort(key=lambda x: x[1])

                with open(xml_path / (entry["friendly_name"] + ".xml"), "r", encoding='utf-8') as xmlFile:
                    root = etree.fromstring(xmlFile.read(), parser=etree.XMLParser(recover=True))

                with open(file_path, "rb") as f:
                    file_b = f.read()

                with FileIO(file_b, "wb") as f:
                    self.pack_menu_file(root, pools, base_offset, f,entry['pad'])

                    f.seek(0)
                    (out_path / file_last).parent.mkdir(parents=True, exist_ok=True)
                    with open(out_path / file_last, "wb") as g:
                        g.write(f.read())

                #Copy in the patched folder
                if entry['friendly_name'] != "Arm9":
                    shutil.copyfile(os.path.join(self.paths['temp_files'], entry['file_path']),
                                os.path.join(self.paths['final_files'], entry['file_path']))

    def pack_menu_file(self, root, pools: list[list[int]], base_offset: int, f: FileIO, pad=False) -> None:

        if root.find("Strings").find("Section").text == "Arm9":
            min_seq = 400
            entries = [ele for ele in root.iter("Entry") if
                       ele.find('PointerOffset').text not in ['732676', '732692', '732708']
                       and int(ele.find('Id').text) <= min_seq]
        else:
            entries = root.iter("Entry")

        for line in entries:
            hi = []
            lo = []
            flat_ptrs = []

            p = line.find("EmbedOffset")
            if p is not None:
                hi = [int(x) - base_offset for x in p.find("hi").text.split(",")]
                lo = [int(x) - base_offset for x in p.find("lo").text.split(",")]

            poff = line.find("PointerOffset")
            if poff.text is not None:
                flat_ptrs = [int(x) for x in poff.text.split(",")]

            mlen = line.find("MaxLength")
            if mlen is not None:
                max_len = int(mlen.text)
                f.seek(flat_ptrs[0])
                text_bytes = self.get_node_bytes(line,pad) + b"\x00"
                if len(text_bytes) > max_len:
                    tqdm.write(
                        f"Line id {line.find('Id').text} ({line.find('JapaneseText').text}) too long, truncating...")
                    f.write(text_bytes[:max_len - 1] + b"\x00")
                else:
                    f.write(text_bytes + (b"\x00" * (max_len - len(text_bytes))))
                continue

            print(line.find('JapaneseText').text)
            text_bytes = self.get_node_bytes(line,pad) + b"\x00"

            l = len(text_bytes)
            for pool in pools:

                if l <= pool[1]:
                    str_pos = pool[0]
                    print(f'offset in pool: {hex(pool[0])}')
                    pool[0] += l;
                    pool[1] -= l

                    break
            else:
                print("Ran out of space")
                raise ValueError("Ran out of space")

            f.seek(str_pos)
            f.write(text_bytes)
            virt_pos = str_pos + base_offset
            for off in flat_ptrs:
                f.write_uint32_at(off, virt_pos)

            for _h, _l in zip(hi, lo):
                val_hi = (virt_pos >> 0x10) & 0xFFFF
                val_lo = (virt_pos) & 0xFFFF

                # can't encode the lui+addiu directly
                if val_lo >= 0x8000: val_hi += 1

                f.write_uint16_at(_h, val_hi)
                f.write_uint16_at(_l, val_lo)

        print(hex(f.tell()))
    def get_node_bytes(self, entry_node, pad=False) -> bytes:

        # Grab the fields from the Entry in the XML
        #print(entry_node.find("JapaneseText").text)
        status = entry_node.find("Status").text
        japanese_text = entry_node.find("JapaneseText").text
        english_text = entry_node.find("EnglishText").text

        # Use the values only for Status = Done and use English if non empty
        final_text = ''
        if (status in self.list_status_insertion):
            final_text = english_text or ''
        else:
            final_text = japanese_text or ''

        voiceId_node = entry_node.find("VoiceId")
        if (voiceId_node != None):
            final_text = '<voice:{}>'.format(voiceId_node.text) + final_text

        # Convert the text values to bytes using TBL, TAGS, COLORS, ...
        bytes_entry = self.text_to_bytes(final_text)

        #Pad with 00
        if (pad):
            rest = 4 - len(bytes_entry) % 4 - 1
            bytes_entry += (b'\x00' * rest)

        return bytes_entry

    def extract_all_skits(self, extract_XML=False):
        folder = 'fc'
        base_path = self.paths['extracted_files'] / 'data' / folder

        fps4 = Fps4(detail_path=self.paths['original_files'] / 'data' / folder / 'fcscr.dat',
                    header_path=self.paths['original_files'] / 'data' / folder / 'fcscr.b')
        fps4.extract_files(base_path, decompressed=True)

        self.paths['skit_xml'].mkdir(parents=True, exist_ok=True)
        for tss_file in base_path.iterdir():
            tss_obj = Tss(tss_file, self.bytes_to_text)
            if len(tss_obj.struct_list) > 0:
                tss_obj.extract_to_xml(self.paths['skit_xml'], tss_file.with_suffix('.xml').name)

    def extract_all_story(self, extract_XML=False):
        folder = 'm'
        base_path = self.paths['extracted_files'] / 'data' / folder

        fps4 = Fps4(detail_path=self.paths['original_files'] / 'data' / folder / f'{folder}.dat',
                    header_path=self.paths['original_files'] / 'data' / folder / f'{folder}.b')
        fps4.extract_files(base_path)

        self.paths['story_xml'].mkdir(parents=True, exist_ok=True)
        for file in [file for file in base_path.iterdir() if file.suffix == '.MAPBIN']:


            file_header = file.with_suffix('.B')
            fps4_tss = Fps4(detail_path=file, header_path=file_header)
            folder_path = file.with_suffix('')
            folder_path.mkdir(parents=True, exist_ok=True)
            fps4_tss.extract_files(folder_path, decompressed=True)

            #Load the tss file
            for tss_file in folder_path.iterdir():
                tss_obj = Tss(tss_file, self.bytes_to_text)

                if len(tss_obj.struct_list) > 0:
                    tss_obj.extract_to_xml(self.paths['story_xml'], tss_file.with_suffix('.xml').name)
    def extract_from_struct(self, f, strings_offset, pointer_offset, struct_offset, root):

        # print("Offset: {}".format(hex(struct_offset)))
        f.seek(struct_offset, 0)

        # Extract all the information and create the entry
        f.read(4)
        unknown_pointer = struct.unpack('<I', f.read(4))[0]
        speaker_offset = struct.unpack('<I', f.read(4))[0] + strings_offset
        text_offset = struct.unpack('<I', f.read(4))[0] + strings_offset
        print(f'speaker offsetspeaker: {speaker_offset}')
        speaker_text = self.bytes_to_text(f, speaker_offset)

        if speaker_text != None:
            struct_speaker_id = self.add_speaker_entry(root.find("Speakers"), pointer_offset, speaker_text)
        japText = self.bytes_to_text(f, text_offset)
        print(f'Text Offset: {hex(text_offset)} - {japText}')
        jap_split_bubble = japText.split("<Bubble>")
        [self.create_entry(root.find("Strings"), pointer_offset, jap, "Struct", struct_speaker_id, unknown_pointer)
         for jap in jap_split_bubble]
        self.struct_id += 1

        return speaker_offset

    def add_speaker_entry(self, root, pointer_offset, japText):

        speaker_entries = [entry for entry in root.iter("Entry") if
                           entry != None and entry.find("JapaneseText").text == japText]
        struct_speaker_id = 0

        if len(speaker_entries) > 0:

            # Speaker already exist
            speaker_entries[0].find("PointerOffset").text = speaker_entries[0].find(
                "PointerOffset").text + ",{}".format(pointer_offset)
            struct_speaker_id = speaker_entries[0].find("Id").text

        else:

            # Need to create that new speaker
            entry_node = etree.SubElement(root, "Entry")
            etree.SubElement(entry_node, "PointerOffset").text = str(pointer_offset)
            etree.SubElement(entry_node, "JapaneseText").text = str(japText)
            etree.SubElement(entry_node, "EnglishText")
            etree.SubElement(entry_node, "Notes")
            etree.SubElement(entry_node, "Id").text = str(self.speaker_id)
            etree.SubElement(entry_node, "Status").text = "To Do"
            struct_speaker_id = self.speaker_id
            self.speaker_id += 1

        return struct_speaker_id

    def create_entry(self, strings_node, pointer_offset, text, entry_type, speaker_id, unknown_pointer):

        # Add it to the XML node
        entry_node = etree.SubElement(strings_node, "Entry")
        etree.SubElement(entry_node, "PointerOffset").text = str(pointer_offset)
        text_split = re.split(self.COMMON_TAG, text)

        if len(text_split) > 1 and any(possible_value in text for possible_value in self.VALID_VOICEID):
            etree.SubElement(entry_node, "VoiceId").text = text_split[1]
            etree.SubElement(entry_node, "JapaneseText").text = ''.join(text_split[2:])
        else:
            etree.SubElement(entry_node, "JapaneseText").text = text

        eng_text = ''

        etree.SubElement(entry_node, "EnglishText")
        etree.SubElement(entry_node, "Notes")
        etree.SubElement(entry_node, "Id").text = str(self.id)
        statusText = "To Do"

        if entry_type == "Struct":
            etree.SubElement(entry_node, "StructId").text = str(self.struct_id)
            etree.SubElement(entry_node, "SpeakerId").text = str(speaker_id)
            etree.SubElement(entry_node, "UnknownPointer").text = str(unknown_pointer)

        etree.SubElement(entry_node, "Status").text = statusText
        self.id += 1
    def extract_from_string(self, f, strings_offset, pointer_offset, text_offset, root):

        f.seek(text_offset, 0)
        japText = self.bytes_to_text(f, text_offset)
        self.create_entry(root, pointer_offset, japText, "Other Strings", -1, "")



    def pack_all_skits(self):
        #Copy original files TSS
        type = 'skit'
        dest = self.paths['temp_files'] / self.file_dict[type] / 'tss'
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.paths['extracted_files'] / self.file_dict[type], dest, dirs_exist_ok=True)

        #Compress using LZ10
        for file_path in (self.paths['temp_files'] / self.file_dict[type]).iterdir():
            print(file_path)


    def pack_tss_file(self, file_name:str, file_type:str):


        # Grab the Tss file inside the folder
        file_name = file_name.split('.')[0]
        base_path = self.paths['extracted_files'] / self.file_dict[file_type]
        with FileIO(base_path / f'{file_name}.FCBIN', 'rb') as original_tss:
            data = original_tss.read()
            tss = io.BytesIO(data)
            tss.seek(0,0)
            tss.read(12)
            base_offset = struct.unpack('<I', tss.read(4))[0]
            tree = etree.parse(self.paths[f'{file_type}_xml'])
            root = tree.getroot()

            # Move to the start of the text section
            start_offset = self.get_starting_offset(root, tss, base_offset)
            tss.seek(start_offset, 0)

            # Insert all Speaker Nodes from Struct
            speaker_dict = self.insert_speaker(root, tss, base_offset)

            # Do stuff for Struct
            struct_dict = dict()
            struct_entries = root.findall('Strings[Section="Story"]/Entry')

            struct_ids = list(set([int(entry.find("StructId").text) for entry in struct_entries]))
            for struct_id in struct_ids:

                entries = [entry for entry in struct_entries if int(entry.find("StructId").text) == struct_id]
                text_offset = tss.tell()

                bytes_text = b''
                for struct_node in entries:

                    voice_id = struct_node.find("VoiceId")
                    if voice_id != None:
                        voice_final = voice_id.text.replace('<', '(').replace('>', ')')
                        tss.write(b'\x09')
                        tss.write(self.text_to_bytes(voice_final))

                        bytes_text = self.get_node_bytes(struct_node)
                        tss.write(bytes_text)
                        tss.write(b'\x0C')

                tss.seek(tss.tell() - 1)
                tss.write(b'\x00\x00\x00')

                # Construct Struct
                struct_dict[int(struct_node.find("PointerOffset").text)] = struct.pack("<I", tss.tell() - base_offset)
                tss.write(struct.pack("<I", 1))
                tss.write(struct.pack("<I", int(struct_node.find("UnknownPointer").text)))  # UnknownPointer
                tss.write(speaker_dict[struct_node.find("SpeakerId").text])  # PersonPointer
                tss.write(struct.pack("<I", text_offset - base_offset))  # TextPointer
                tss.write(struct.pack("<I", text_offset + len(bytes_text) + 1 - base_offset))
                tss.write(struct.pack("<I", text_offset + len(bytes_text) + 2 - base_offset))
                tss.write(b'\x00')

            # Do Other Strings
            #string_dict = dict()
            #for string_node in root.findall('Strings[Section="Other Strings"]/Entry'):
            #    string_dict[int(string_node.find("PointerOffset").text)] = struct.pack("<I", tss.tell() - base_offset)
            #    bytes_text = self.get_node_bytes(string_node)
            #    tss.write(bytes_text)
            #    tss.write(b'\x00')

            # Update Struct pointers
            for pointer_offset, value in struct_dict.items():
                tss.seek(pointer_offset)
                tss.write(value)

            # Update String pointers
            #for pointer_offset, value in string_dict.items():
            #    tss.seek(pointer_offset)
            #    tss.write(value)

            #Update TSS
            #with open(file_tss, "wb") as f:
            #    f.write(tss.getvalue())


            return tss.getvalue()

    def get_starting_offset(self, root, tss, base_offset):

        # String Pointers
        strings_pointers = [int(ele.find("PointerOffset").text) for ele in
                            root.findall('Strings[Section="Other Strings"]/Entry')]
        strings_offset = []
        structs_offset = []

        for pointer_offset in strings_pointers:
            tss.seek(pointer_offset)
            strings_offset.append(struct.unpack("<I", tss.read(4))[0] + base_offset)

        # Struct Pointers
        struct_pointers = [int(ele.find("PointerOffset").text) for ele in
                           root.findall('Strings[Section="Story"]/Entry')]
        for pointer_offset in struct_pointers:
            tss.seek(pointer_offset)
            struct_offset = struct.unpack("<I", tss.read(4))[0] + base_offset
            tss.seek(struct_offset)
            tss.read(8)
            struct_offset = struct.unpack("<I", tss.read(4))[0] + base_offset
            structs_offset.append(struct_offset)

        struct_count = len(structs_offset)
        strings_count = len(strings_offset)

        if struct_count == 0:
            return min(strings_offset)
        elif strings_count == 0:
            return min(structs_offset)
        else:
            return min(min(structs_offset), min(strings_offset))

    def insert_speaker(self, root, tss, base_offset):

        speaker_dict = dict()

        for speaker_node in root.findall("Speakers/Entry"):
            bytes_entry = self.get_node_bytes(speaker_node)
            speaker_id = speaker_node.find("Id").text
            speaker_dict[speaker_id] = struct.pack("<I", tss.tell() - base_offset)
            tss.write(bytes_entry)
            tss.write(b'\x00')
        return speaker_dict

    def text_to_bytes(self, text):
        multi_regex = (self.HEX_TAG + "|" + self.COMMON_TAG + r"|(\n)")
        tokens = [sh for sh in re.split(multi_regex, text) if sh]

        output = b''
        for t in tokens:
            # Hex literals
            if re.match(self.HEX_TAG, t):
                output += struct.pack("B", int(t[1:3], 16))

            # Tags
            elif re.match(self.COMMON_TAG, t):
                tag, param, *_ = t[1:-1].split(":") + [None]

                if tag == "icon":
                    output += struct.pack("B", self.ijsonTblTags["TAGS"].get(tag))
                    output += b'\x28' + struct.pack('B', int(param)) + b'\x29'

                elif any(re.match(possible_value, tag)  for possible_value in self.VALID_VOICEID):
                    output += b'\x09\x28' + tag.encode("cp932") + b'\x29'
                elif tag == "Bubble":
                    output += b'\x0C'
                else:
                    if tag in self.ijsonTblTags["TAGS"]:
                        output += struct.pack("B", self.ijsonTblTags["TAGS"][tag])
                        continue

                    for k, v in self.ijsonTblTags.items():
                        if tag in v:
                            if k in ['NAME', 'COLOR']:
                                output += struct.pack('B',self.iTags[k]) + b'\x28' + bytes.fromhex(v[tag]) + b'\x29'
                                break
                            else:
                                output += b'\x81' + bytes.fromhex(v[tag])

            # Actual text
            elif t == "\n":
                output += b"\x0A"
            else:
                for c in t:
                    if c in self.PRINTABLE_CHARS or c == "\u3000":
                        output += c.encode("cp932")
                    else:
                        output += struct.pack(">H",
                            self.ijsonTblTags["TBL"].get(c, int.from_bytes(c.encode("cp932"), "big")))

        return output