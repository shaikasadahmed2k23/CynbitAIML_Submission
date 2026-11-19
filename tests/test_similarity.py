from app.core.similarity import find_similar, normalize_code

ORIGINAL = '''
class LRUCache:
    # least recently used
    def __init__(self, capacity):
        self.capacity = capacity
        self.data = OrderedDict()
    def get(self, key):
        if key not in self.data:
            return None
        self.data.move_to_end(key)
        return self.data[key]
    def put(self, key, value):
        self.data[key] = value
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)
'''
RENAMED = (ORIGINAL.replace("LRUCache", "Cache").replace("capacity", "size").replace("data", "items")
           .replace("key", "k").replace("value", "v").replace("least recently used", "my own cache"))
DIFFERENT = '''
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True
'''


def test_normalize_ignores_names_and_comments():
    assert normalize_code(ORIGINAL) == normalize_code(RENAMED)


def test_renamed_copy_flagged():
    m = find_similar(RENAMED, {"orig": ORIGINAL, "other": DIFFERENT}, threshold=0.85)
    assert [x.other_id for x in m] == ["orig"] and m[0].score > 0.95


def test_unrelated_not_flagged_and_edge_cases():
    assert find_similar(DIFFERENT, {"orig": ORIGINAL}, threshold=0.85) == []
    assert find_similar("x=1", {"orig": ORIGINAL}) == []   # too short
    assert find_similar(ORIGINAL, {}) == []                # empty store
