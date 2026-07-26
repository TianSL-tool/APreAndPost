from aprepost2.app import main


if __name__ == "__main__":
    raise SystemExit(main())
# cd .\APrePost2
# pyinstaller APrePost2.spec
# python -m PyInstaller --noconfirm --onefile --windowed --name APrePost2 --collect-all scipy --collect-all h5py run.py