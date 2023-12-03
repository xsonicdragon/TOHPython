pushd ".."
python Tales_Exe.py -p "../TOH/project.json" -g TOR extract -i "../TOH_Original.nds" -ft Iso 
::python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR extract -ft Story
::python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR extract -ft Skits
::python Tales_Exe.py -p "../Tales-of-Rebirth/project.json" -g TOR extract -ft Menu

popd
pause