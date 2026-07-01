import sys
from cx_Freeze import setup, Executable

try:
    # ADD FILES
    files = ['polkadot_dot_crypto_icon_264383.ico']

    # TARGET
    target = Executable(
        script="APyPreAndPost.py",
        base="Console",
        icon="polkadot_dot_crypto_icon_264383.ico"
    )

    if len(sys.argv) == 1:
        sys.argv.append("build")  # 默认执行build命令

    # SETUP CX FREEZE
    setup(
        name="GeoTool",
        version="1.0",
        description="Pre- and post-processing for geodyna",
        author="Tian",
        options={
            'build_exe': {
                'include_files': files
            }
        },
        executables=[target]
    )
except Exception as e:
    print(f"打包过程中出现错误: {e}")
