set converter=%~dp0%converter.py
forfiles /p %1 /m *.amap /c "cmd /c python %converter% @file %2\/@fname\/@fname"