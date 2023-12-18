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
            "skit": "data/fc/fcscr",
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

        # Use the values only for Status = Done and use English if non-empty
        final_text = ''
        if (status in self.list_status_insertion):
            final_text = english_text or ''
        else:
            final_text = japanese_text or ''

        voiceid_node = entry_node.find("VoiceId")

        if voiceid_node is not None:
            final_text = f'<{voiceid_node.text}>' + final_text

        # Convert the text values to bytes using TBL, TAGS, COLORS, ...
        bytes_entry = self.text_to_bytes(final_text)

        #Pad with 00
        if pad:
            rest = 4 - len(bytes_entry) % 4 - 1
            bytes_entry += (b'\x00' * rest)

        return bytes_entry

    def extract_all_skits(self, extract_XML=False):
        type = 'skit'
        base_path = self.paths['extracted_files'] / self.file_dict[type]
        base_path.mkdir(parents=True, exist_ok=True)
        fps4 = Fps4(detail_path=self.paths['original_files'] / 'data' / 'fc' / 'fcscr.dat',
                    header_path=self.paths['original_files'] / 'data' / 'fc' / 'fcscr.b')
        fps4.extract_files(base_path, decompressed=True)

        self.paths['skit_xml'].mkdir(parents=True, exist_ok=True)
        for tss_file in base_path.iterdir():
            tss_obj = Tss(tss_file, bytes_to_text=self.bytes_to_text, text_to_bytes=self.text_to_bytes, list_status_insertion=self.list_status_insertion)
            if len(tss_obj.struct_list) > 0:
                tss_obj.extract_to_xml(self.paths['skit_xml'], tss_file.with_suffix('.xml').name)

    def pack_tss(self, destination_path:Path, xml_path:Path):
        tss = Tss(path=destination_path, bytes_to_text=self.bytes_to_text, text_to_bytes=self.text_to_bytes,
                  list_status_insertion=self.list_status_insertion)
        tss.pack_tss_file(destination_path=destination_path,
                          xml_path=xml_path)

    def pack_all_skits(self):
        type = 'skit'
        #Copy original TSS files in the "updated" folder
        dest = self.paths['temp_files'] / self.file_dict[type]
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.paths['extracted_files'] / self.file_dict[type], dest, dirs_exist_ok=True)

        fps4 = Fps4(detail_path=self.paths['original_files'] / 'data' / 'fc' / 'fcscr.dat',
                    header_path=self.paths['original_files'] / 'data' / 'fc' / 'fcscr.b')

        #Repack TSS files
        for file in fps4.files:
            self.pack_tss(destination_path=dest / file.name,
                           xml_path=self.paths['skit_xml'] / file.name.replace('.FCBIN', '.xml'))


        #Repack FPS4 archive
        fps4.pack_file(updated_file_path=dest, destination_folder=self.paths['final_files'] / 'data' / 'fc')

    def pack_mapbin_story(self, file_name, type):
        mapbin_folder = self.paths['temp_files'] / self.file_dict[type] / file_name

        # Look on each SCP file
        for scp_path in mapbin_folder.iterdir():

            if scp_path.suffix == ".SCP":
                xml_path = self.paths['story_xml'] / scp_path.with_suffix('.xml').name

                if os.path.exists(xml_path):
                    self.pack_tss(destination_path=scp_path,
                                  xml_path=xml_path)

            args = ['lzss', '-evn', scp_path]
            subprocess.run(args)


        fps4_mapbin = Fps4(detail_path=self.paths['temp_files'] / self.file_dict[type] / f'{file_name}.MAPBIN',
                           header_path=self.paths['temp_files'] / self.file_dict[type] / f'{file_name}.B')

        fps4_mapbin.pack_fps4_type1(updated_file_path=mapbin_folder,
                                    destination_folder=self.paths['temp_files'] / self.file_dict[type])
    def pack_all_story(self):
        type = 'story'
        # Copy original TSS files in the "updated" folder
        dest = self.paths['temp_files'] / self.file_dict[type]
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.paths['extracted_files'] / self.file_dict[type], dest, dirs_exist_ok=True)

        #Repack each of the MAPBIN FPS4
        folder = 'm'
        base_path = self.paths['extracted_files'] / 'data' / folder
        fps4_m = Fps4(detail_path=self.paths['original_files'] / 'data' / folder / f'{folder}.dat',
                    header_path=self.paths['original_files'] / 'data' / folder / f'{folder}.b')

        for file in [f for f in fps4_m.files if f.name.endswith('.B')]:

            if file.name == "FSHT00.B":
                self.pack_mapbin_story(file.name.split('.')[0], type)

        fps4_m.pack_fps4_type1(self.paths['temp_files'] / self.file_dict[type], self.paths['final_files'] / self.file_dict[type])
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
                tss_obj = Tss(path=tss_file, bytes_to_text=self.bytes_to_text,
                              text_to_bytes=self.text_to_bytes, list_status_insertion=self.list_status_insertion)

                if len(tss_obj.struct_list) > 0:
                    tss_obj.extract_to_xml(self.paths['story_xml'], tss_file.with_suffix('.xml').name)

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

                        if c in self.ijsonTblTags["TBL"].keys():
                            b = self.ijsonTblTags["TBL"][c].to_bytes(2, 'big')
                            output += b
                        else:
                            output += c.encode("cp932")



        return output