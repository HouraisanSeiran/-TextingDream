"""测试包标记文件。

作用是让 `python -m unittest discover -s tests -t .` 能把 tests 当作包导入；
没有它时标准库 unittest 会直接报 `Start directory is not importable`。
"""
