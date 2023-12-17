import argparse
from pathlib import Path

from pythonlib.games import ToolsNDX, ToolsTOR, ToolsTOH

SCRIPT_VERSION = "0.0.3"


def get_arguments(argv=None):
    # Init argument parser
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-g",
        "--game",
        choices=["TOR", "NDX", "TOH"],
        required=True,
        metavar="game",
        help="Options: TOR, NDX, TOH",
    )

    parser.add_argument(
        "-p",
        "--project",
        required=True,
        type=Path,
        metavar="project",
        help="project.json file path",
    )

    sp = parser.add_subparsers(title="Available actions", required=False, dest="action")

    # Extract commands
    sp_extract = sp.add_parser(
        "extract",
        description="Extract the content of the files",
        help="Extract the content of the files",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    sp_extract.add_argument(
        "-ft",
        "--file_type",
        choices=["Iso", "Main", "Menu", "Story", "Skits"],
        required=True,
        metavar="file_type",
        help="(Required) - Options: Iso, Init, Main, Menu, Story, Skits",
    )

    sp_extract.add_argument(
        "-i",
        "--iso",
        required=False,
        default="../b-topndxj.iso",
        metavar="iso",
        help="(Optional) - Only for extract Iso command",
    )

    sp_extract.add_argument(
        "-r",
        "--replace",
        required=False,
        metavar="replace",
        default=False,
        help="(Optional) - Boolean to uses translations from the Repo to overwrite the one in the Data folder",
    )

    sp_extract.add_argument(
        "--only-changed",
        required=False,
        action="store_true",
        help="(Optional) - Insert only changed files not yet commited",
    )

    sp_insert = sp.add_parser(
        "insert",
        help="Take the new texts and recreate the files",
    )

    sp_insert.add_argument(
        "-ft",
        "--file_type",
        choices=["Iso", "Main", "Menu", "Story", "Skits", "All", "Asm"],
        required=True,
        metavar="file_type",
        help="(Required) - Options: Iso, Init, Main, Elf, Story, Skits, All, Asm",
    )

    sp_insert.add_argument(
        "-i",
        "--iso",
        required=False,
        default="",
        metavar="iso",
        help="(Deprecated) - No longer in use for insertion",
    )

    sp_insert.add_argument(
        "--with-proofreading",
        required=False,
        action="store_const",
        const="Proofreading",
        default="",
        help="(Optional) - Insert lines in 'Proofreading' status",
    )

    sp_insert.add_argument(
        "--with-editing",
        required=False,
        action="store_const",
        const="Editing",
        default="",
        help="(Optional) - Insert lines in 'Editing' status",
    )

    sp_insert.add_argument(
        "--with-problematic",
        required=False,
        action="store_const",
        const="Problematic",
        default="",
        help="(Optional) - Insert lines in 'Problematic' status",
    )

    sp_insert.add_argument(
        "--only-changed",
        required=False,
        action="store_true",
        help="(Optional) - Insert only changed files not yet commited",
    )

    args = parser.parse_args()

    return args


def getTalesInstance(args, game_name):

    if game_name == "TOR":
        if args.action == "insert":
            insert_mask = [
                args.with_proofreading,
                args.with_editing,
                args.with_problematic,
            ]
        else:
            insert_mask = []
        talesInstance = ToolsTOR.ToolsTOR(
            args.project.resolve(), insert_mask, args.only_changed
        )
    elif game_name == "NDX":
        talesInstance = ToolsNDX.ToolsNDX("TBL_All.json")

    elif game_name == "TOH":
        if args.action == "insert":
            insert_mask = [
                args.with_proofreading,
                args.with_editing,
                args.with_problematic,
            ]
        else:
            insert_mask = []

        talesInstance = ToolsTOH.ToolsTOH(
            args.project.resolve(), insert_mask, args.only_changed
        )
    else:
        raise ValueError("Unkown game name")

    return talesInstance


if __name__ == "__main__":

    args = get_arguments()
    game_name = args.game
    tales_instance = getTalesInstance(args, game_name)

    if args.action == "insert":

        if game_name == "TOH":

            if args.file_type == "Menu":
                #tales_instance.decompress_arm9()
                tales_instance.pack_all_menu()
                #tales_instance.compress_arm9()
                tales_instance.make_iso(Path(args.iso))

            if args.file_type == "Iso":
                tales_instance.compress_arm9()
                tales_instance.make_iso(Path(args.iso))

            elif args.file_type == "Skits":
                tales_instance.pack_all_skits()

            elif args.file_type == "Skits":
                tales_instance.pack_all_story()

        elif args.file_type == "Main":
            tales_instance.pack_main_archive()

        elif args.file_type == "Story":
            tales_instance.pack_all_story()

        elif args.file_type == "Skits":
            tales_instance.pack_all_skits()

        elif args.file_type == "Menu":
            tales_instance.pack_all_menu()

        elif args.file_type == "Asm":
            tales_instance.patch_binaries()

        elif args.file_type == "All":
            tales_instance.pack_all_story()
            tales_instance.pack_all_skits()
            tales_instance.pack_all_menu()
            tales_instance.patch_binaries()
            tales_instance.make_iso()

    if args.action == "extract":

        if game_name == "TOH":

            if args.file_type == "Menu":
                tales_instance.extract_all_menu()

            if args.file_type == "Iso":
                tales_instance.extract_Iso(Path(args.iso))
                tales_instance.decompress_arm9()

            if args.file_type == "Skits":
                tales_instance.extract_all_skits(args.replace)

            elif args.file_type == "Story":
                tales_instance.extract_all_story(args.replace)
        else:
            if args.file_type == "Iso":
                tales_instance.extract_Iso(Path(args.iso))
                tales_instance.extract_main_archive()

            if args.file_type == "Main":
                tales_instance.extract_main_archive()

            if args.file_type == "Menu":
                tales_instance.extract_all_menu()

            if args.file_type == "Story":
                tales_instance.extract_all_story()

            if args.file_type == "Skits":
                tales_instance.extract_all_skits(args.replace)
