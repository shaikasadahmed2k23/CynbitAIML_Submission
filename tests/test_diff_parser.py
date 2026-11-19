from app.core.diff_parser import parse_diff

DIFF = """diff --git a/app/a.py b/app/a.py
index 111..222 100644
--- a/app/a.py
+++ b/app/a.py
@@ -1,3 +1,4 @@
 import os
-x = 1
+x = 2
+y = 3
 print(x)
diff --git a/web/b.js b/web/b.js
new file mode 100644
--- /dev/null
+++ b/web/b.js
@@ -0,0 +1,2 @@
+const a = 1;
+console.log(a);
"""


def test_files_and_languages():
    p = parse_diff(DIFF)
    assert [f.path for f in p.files] == ["app/a.py", "web/b.js"]
    assert p.languages == ["JavaScript", "Python"]
    assert p.files[1].is_new


def test_counts_and_line_numbers():
    p = parse_diff(DIFF)
    assert p.added_lines == 4 and p.removed_lines == 1
    added = p.files[0].added
    assert [(l.text, l.new_no) for l in added] == [("x = 2", 2), ("y = 3", 3)]
    assert 4 in p.valid_lines()["app/a.py"]  # trailing context line
    assert 5 not in p.valid_lines()["app/a.py"]


def test_added_code_and_empty():
    assert "console.log(a);" in parse_diff(DIFF).added_code()
    assert parse_diff("").files == []
    assert parse_diff("garbage text\nnot a diff").files == []
