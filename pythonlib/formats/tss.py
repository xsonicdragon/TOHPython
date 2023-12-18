from dataclasses import dataclass
import struct
from typing import Optional
from ..formats.FileIO import FileIO
import os
from pathlib import Path
import re
import io
import lxml.etree as etree
import string
import subprocess

@dataclass
class StructEntry:
    pointer_offset:int
    text_offset:int
    text:str

@dataclass
class StructNode:
    id:int
    unknown1:int
    unknown2:int
    pointer_offset:int
    text_offset:int
    speaker:StructEntry
    text:StructEntry

    def __init__(self, id:int, pointer_offset:int, text_offset:int):
        self.id=id
        self.pointer_offset = pointer_offset
        self.text_offset = text_offset

bytecode_list = [b'\x0E\x10\x00\x0C\x04', b'\x00\x10\x00\x0C\x04']


class Tss():
    def __init__(self, path:Path, bytes_to_text, text_to_bytes, list_status_insertion) -> None:
        self.align = False
        self.files = []

        self.struct_list = []
        self.id = 1
        self.struct_id = 1
        self.speaker_id = 1
        self.root = etree.Element('SceneText')
        self.bytes_to_text = bytes_to_text
        self.text_to_bytes = text_to_bytes
        self.list_status_insertion = list_status_insertion
        self.VALID_VOICEID = [r'(<VSM_\w+>)', r'(<VCT_\w+>)', r'(<S\d+>)', r'(<C\d+>)']
        self.COMMON_TAG = r"(<[\w/]+:?\w+>)"
        self.HEX_TAG = r"(\{[0-9A-F]{2}\})"
        self.PRINTABLE_CHARS = "".join(
            (string.digits, string.ascii_letters, string.punctuation, " ")
        )

        with FileIO(path) as tss:

            tss.read(12)
            self.strings_offset = struct.unpack('<I', tss.read(4))[0]
            tss.read(4)

            self.create_struct_nodes(tss)

    def extract_struct_pointers(self, f):

        text_offset = []
        pointer_offset = dict()
        i = 0
        for bytecode in bytecode_list:
            regex = re.compile(bytecode)
            f.seek(0,0)
            data = f.read()

            for match_obj in regex.finditer(data):
                offset = match_obj.start()
                f.seek(offset+len(bytecode),0)
                text_offset = struct.unpack('<H', f.read(2))[0] + self.strings_offset
                self.struct_list.append(StructNode(id=i,pointer_offset=f.tell()-2, text_offset=text_offset))
                i += 1


    def create_struct_nodes(self, tss:FileIO):

        #Create all the nodes
        speaker_node = etree.SubElement(self.root, 'Speakers')
        etree.SubElement(speaker_node, 'Section').text = "Speaker"
        strings_node = etree.SubElement(self.root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = "Story"

        self.extract_struct_pointers(tss)

        self.extract_struct_information(tss)

    def extract_struct_information(self, f):

        for struct_obj in self.struct_list:
            f.seek(struct_obj.text_offset, 0)

            # Extract all the information and create the entry
            struct_obj.unknown_pointer1 = struct.unpack('<I', f.read(4))[0]
            struct_obj.unknown_pointer2 = struct.unpack('<I', f.read(4))[0]
            speaker_pointer_offset = f.tell()
            speaker_text_offset = struct.unpack('<I', f.read(4))[0] + self.strings_offset
            text_offset = struct.unpack('<I', f.read(4))[0] + self.strings_offset
            speaker_text = self.bytes_to_text(f, speaker_text_offset)

            struct_speaker_id=-1
            if speaker_text is not None:
                struct_speaker_id = self.add_speaker_entry(self.root.find("Speakers"), speaker_pointer_offset, speaker_text)
                struct_obj.speaker = StructEntry(pointer_offset=speaker_pointer_offset, text_offset=speaker_text_offset,
                                             text=speaker_text)
            jap_text = self.bytes_to_text(f, text_offset)
            jap_split = jap_text.split("<Bubble>")
            #print(f'Text Offset: {hex(text_offset)} - {japText}')

            [self.create_entry(struct_obj.pointer_offset, jap_ele, "Struct", struct_speaker_id,
                               struct_obj.unknown_pointer1, struct_obj.unknown_pointer2) for jap_ele in jap_split]
            self.struct_id += 1

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

    def extract_to_xml(self, xml_path, file_name):

        # Write the XML file
        txt = etree.tostring(self.root, encoding="UTF-8", pretty_print=True)
        with open(xml_path / file_name, "wb") as xmlFile:
            xmlFile.write(txt)

    def create_entry(self, pointer_offset, text, entry_type, speaker_id, unknown_pointer1, unknown_pointer2):

        # Add it to the XML node
        strings_node = self.root.find("Strings")
        entry_node = etree.SubElement(strings_node, "Entry")
        etree.SubElement(entry_node, "PointerOffset").text = str(pointer_offset)
        text_split = re.split(self.COMMON_TAG, text)

        if len(text_split) > 1 and any(re.match(possible_value, text)  for possible_value in self.VALID_VOICEID):
            etree.SubElement(entry_node, "VoiceId").text = text_split[1].replace('<','').replace('>','')
            etree.SubElement(entry_node, "JapaneseText").text = ''.join(text_split[2:])
        else:
            etree.SubElement(entry_node, "JapaneseText").text = text

        eng_text = ''

        etree.SubElement(entry_node, "EnglishText")
        etree.SubElement(entry_node, "Notes")
        etree.SubElement(entry_node, "Id").text = str(self.id)
        status_text = "To Do"

        if entry_type == "Struct":
            etree.SubElement(entry_node, "StructId").text = str(self.struct_id)
            etree.SubElement(entry_node, "SpeakerId").text = str(speaker_id)
            etree.SubElement(entry_node, "UnknownPointer1").text = str(unknown_pointer1)
            etree.SubElement(entry_node, "UnknownPointer2").text = str(unknown_pointer2)

        etree.SubElement(entry_node, "Status").text = status_text
        self.id += 1


    def pack_tss_file(self, destination_path:Path, xml_path:Path):


        # Grab the Tss file inside the folder
        with FileIO(destination_path, 'rb') as original_tss:
            data = original_tss.read()
            tss = io.BytesIO(data)
            tss.seek(0,0)
            tss.read(12)
            base_offset = struct.unpack('<I', tss.read(4))[0]
            tree = etree.parse(xml_path)
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
                nb_entries = len(entries)
                for struct_node in entries:
                    bytes_text = self.get_node_bytes(struct_node)
                    tss.write(bytes_text)

                    if nb_entries >= 2:
                        tss.write(b'\x0C')

                #pad
                rest = 4 - tss.tell() % 4
                if rest > 0:
                    tss.write((b'\x00' * rest))

                # Construct Struct
                struct_dict[int(struct_node.find("PointerOffset").text)] = struct.pack("<I", tss.tell() - base_offset)
                tss.write(struct.pack("<I", int(struct_node.find("UnknownPointer1").text)))
                tss.write(struct.pack("<I", int(struct_node.find("UnknownPointer2").text)))  # UnknownPointer
                tss.write(speaker_dict[struct_node.find("SpeakerId").text])  # PersonPointer
                tss.write(struct.pack("<I", text_offset - base_offset))  # TextPointer
                tss.write(b'\x00')

            # Update Struct pointers
            for pointer_offset, value in struct_dict.items():
                tss.seek(pointer_offset)
                tss.write(value)

            #Update TSS
            with FileIO(destination_path, 'wb') as f:
               f.write(tss.getvalue())

    def insert_speaker(self, root, tss, base_offset):

        speaker_dict = dict()

        for speaker_node in root.findall("Speakers/Entry"):
            bytes_entry = self.get_node_bytes(speaker_node)
            speaker_id = speaker_node.find("Id").text
            speaker_dict[speaker_id] = struct.pack("<I", tss.tell() - base_offset)
            tss.write(bytes_entry)
            tss.write(b'\x00')
        return speaker_dict

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

    def get_starting_offset(self, root, tss, base_offset):

        return min([ele.speaker.text_offset for ele in self.struct_list])