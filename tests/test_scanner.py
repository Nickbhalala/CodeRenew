from coderenew.scanner import scan_path, scan_source, strip_comments_and_strings
from tests.conftest import EXAMPLE


def rules(src: str) -> list[str]:
    return [f.rule for f in scan_source(src)]


def test_detects_each_rule():
    src = """
#define LIMIT 10
typedef int Id;
class A {
    A(const A&);
};
void f() throw() {}
void g() {
    void* raw = (void*)p;
    int* p = new int(3);
    delete p;
    char* s = (char*)malloc(10);
    strcpy(s, "x");
    std::auto_ptr<int> a;
    if (p == NULL) {}
    for (int i = 0; i < n; i++) {}
}
"""
    assert set(rules(src)) == {
        "define-constant",
        "typedef",
        "private-copy-ctor",
        "throw-spec",
        "raw-new",
        "raw-delete",
        "c-style-cast",
        "malloc-free",
        "unsafe-c-string",
        "auto-ptr",
        "null-macro",
        "index-loop",
    }


def test_ignores_comments_and_strings():
    src = '// NULL here\n/* new Foo */\nconst char* s = "delete x; NULL";\nint x = 0;\n'
    assert rules(src) == []


def test_stripping_preserves_line_numbers():
    src = "/* a\nb */ int* p = NULL;\n"
    assert strip_comments_and_strings(src).count("\n") == src.count("\n")
    [f] = scan_source(src)
    assert f.line == 2 and f.snippet == "b */ int* p = NULL;"


def test_modern_code_is_clean():
    src = """
constexpr int kLimit = 10;
using Id = int;
class A { A(const A&) = delete; };
void f() noexcept {}
void g(const std::vector<int>& v) {
    auto p = std::make_unique<int>(3);
    for (int x : v) { (void)x; }
    if (p == nullptr) {}
    double d = static_cast<double>(v.size());
}
"""
    assert rules(src) == []


def test_example_project_findings():
    counts = {p.name: len(f) for p, f in scan_path(EXAMPLE).items()}
    assert counts["inventory.h"] == 4
    assert counts["inventory.cpp"] > 15
