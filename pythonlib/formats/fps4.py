from dataclasses import dataclass
import struct
from typing import Optional
from ..formats.FileIO import FileIO
import os
from pathlib import Path
import subprocess


@dataclass
class fps4_file():
    c_type:str
    data:bytes
    name:str
    size:int


class Fps4():

    def __init__(self, detail_path:Path, header_path:Path = None) -> None:
        self.type = -1
        self.align = False
        self.files = []
        self.header_path = header_path or detail_path
        self.detail_path = detail_path

        self.extract_information()

    @staticmethod
    def from_path(path:Path) -> 'Fps4':

        self = Fps4()
        self.detail_path = path
        self.header_path = self.look_for_header(path)

    def extract_information(self):
        with FileIO(self.header_path) as f:
            f.seek(4,0)
            file_amount = f.read_uint32()
            header_size = f.read_uint32()
            offset = f.read_uint32()
            block_size = f.read_uint16()

            self.files = []
            files_infos = []

            if offset == 0x0:
                f.seek(header_size, 0)

                if self.header_path != "":
                    self.header_name = os.path.basename(self.header_path)
                    with FileIO(self.detail_path) as det:
                        for _ in range(file_amount-1):
                            offset = f.read_uint32()
                            size = f.read_uint32()
                            f.read_uint32()
                            name = f.read(block_size - 0xC).decode("ASCII").strip('\x00')
                            files_infos.append( (offset, size, name))

                        for offset, size, name in files_infos:
                            det.seek(offset)
                            data = det.read(size)

                            c_type = 'None'
                            if data[0] == 0x10:
                                c_type = 'LZ10'
                            elif data[0] == 0x11:
                                c_type = 'LZ11'

                            self.files.append(fps4_file(c_type, data, name, size))

    def extract_files(self, destination_path, decompressed=False):

        destination_path.mkdir(parents=True, exist_ok=True)
        for file in self.files:
            with open(destination_path / file.name, 'wb') as f:
                f.write(file.data)

            #Decompress using LZ10 or LZ11
            if decompressed:
                if file.c_type == 'LZ10':
                    args = ['lzss', '-d', file.name]
                    subprocess.run(args, cwd=destination_path)

    def pack_file(self, updated_file_path:Path, destination_folder:Path):
        buffer = 0



        with FileIO(updated_file_path / os.path.basename(self.detail_path), "wb") as fps4_detail:

            #Writing new dat file and updating file attributes
            for file in self.files:
                # Compress using LZ10
                args = ['lzss', '-evn', file.name]
                subprocess.run(args, cwd= updated_file_path / 'tss')

                with FileIO(updated_file_path / file.name, 'rb') as sub_file:
                    file.data = sub_file.read()
                    file.size = len(file.data)
                    fps4_detail.write(file.data)

        with FileIO(updated_file_path / os.path.basename(self.header_path), "wb") as fps4_header:

            #Header of the file
            fps4_header.write(b'\x46\x50\x53\x34')  # FPS4
            fps4_header.write(struct.pack('<L', len(self.files) + 1))
            fps4_header.write(struct.pack('<L', 0x1C))
            fps4_header.write(b'\x00' * 4 + b'\x2C\x00\x0F\x00\x01\x01\x00\x00' + b'\x00' * 4)

            #Updating Offsets, File Size and File Name
            for file in self.files:
                fps4_header.write(struct.pack('<L', buffer))
                fps4_header.write(struct.pack('<L', file.size))
                fps4_header.write(struct.pack('<L', file.size - 8))
                fps4_header.write(file.name.encode())
                fps4_header.write(b'\x00' * (32 - (len(file.name) % 32)))
                buffer += file.size

            fps4_header.write(struct.pack('<L', buffer) + b'\x00' * 12)
            fps4_header.close()
    def look_for_header(self, path:Path):

        base_name = os.path.basename(path).split('.')[0]
        header_found = [ele for ele in os.listdir(path.parent) if ele.endswith('.b') and ele.split('.')[0] == base_name]

        if len(header_found) > 0:
            print(f'header was found: {header_found[0]}')
            return path.parent / header_found[0]
        else:
            return None


    #def get_fps4_type(self):
