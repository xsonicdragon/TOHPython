import os
import shutil

from .ToolsTales import ToolsTales
from pathlib import Path
import json
import subprocess
import datetime

class ToolsTOH(ToolsTales):

    def __init__(self, project_file: Path, insert_mask: list[str], changed_only: bool = False) -> None:

        base_path = project_file.parent
        self.folder_name = 'TOR'
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
            self.ijsonTblTags[k] = {v2: k2 for k2, v2 in v.items()}
        self.id = 1

        # byteCode
        self.story_byte_code = b"\xF8"
        self.list_status_insertion: list[str] = ['Done']
        self.list_status_insertion.extend(insert_mask)
        self.changed_only = changed_only
        self.repo_path = str(base_path)

    def extract_Iso(self, game_iso: Path) -> None:

        #Extract all the files
        extract_to = self.paths["original_files"]
        self.clean_folder(extract_to)

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

        #Copy to patched folder
        shutil.copytree(os.path.join('..', self.folder_name, self.paths["original_files"]), os.path.join('..', self.folder_name, self.paths["final_files"]), dirs_exist_ok=True)

    def make_iso(self, game_iso) -> None:
        #Clean old builds and create new one
        self.clean_builds(self.paths["game_builds"])

        # Set up new iso name
        n: datetime.datetime = datetime.datetime.now()
        new_iso = self.paths["game_builds"]
        new_iso /= f"TalesofHearts_{n.year:02d}{n.month:02d}{n.day:02d}{n.hour:02d}{n.minute:02d}.nds"
        path = self.folder_name / self.paths["final_files"]

        nds_base_name = os.path.basename(game_iso)
        args = ['ndstool', '-x', nds_base_name,
                '-9', path / 'arm9.bin',
                '-7', path / 'arm7.bin',
                '-y9', path / 'y9.bin',
                '-y7', path / 'y7.bin',
                '-d', path / 'data',
                '-y', path / 'overlay',
                '-t', path / 'banner.bin',
                '-h', path / 'header.bin']

        wrk_dir = os.path.normpath(os.getcwd() + os.sep + os.pardir)
        subprocess.run(args, cwd=wrk_dir)


        os.rename(self.folder_name / self.paths["game_builds"] / nds_base_name, new_iso )
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