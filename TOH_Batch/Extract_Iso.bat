pushd ".."
::python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR extract -i "../Tales of Rebirth (Japan)_Original.iso" -ft Iso 
python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR extract -ft Story
python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR extract -ft Skits
python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR extract -ft Menu

popd
pause