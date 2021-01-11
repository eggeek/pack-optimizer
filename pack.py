#!/usr/bin/python
from copy import deepcopy
from queue import Queue

class Item:
    idx: int   # item id
    cid: int   # category
    num: int   # number of this item
    w: float  # weight
    p  : float # price

    def __init__(self, d: dict):
        self.idx = d['id']
        self.cid = d['cid']
        self.num = d['num']
        self.w   = d['w']
        self.p   = d['p']

    def __hash__(self):
        return hash((self.cid, self.num))

class Vert:
    v: dict[int, int]

    def __init__(self, other: dict):
        self.v = deepcopy(other)

    def __hash__(self):
        return hash(frozenset(self.v.items()))

    def __eq__(self, rhs):
        for k in self.v.keys():
            assert(rhs.v[k] is not None)
            if self.v[k] != rhs.v[k]:
                return False
        return True

    def __ne__(self, rhs):
        return not(self.__eq__(rhs))

    def __lt__(self, rhs):
        for k in self.v.keys():
            assert(rhs.v[k] is not None)
            if self.v[k] < rhs.v[k]:
                return True
        return False

    def __str__(self):
        return str(self.v)

    def feasible(self, m) -> bool:
        for k, num in m.v.items():
            if self.v.get(k) is None: return False
            if self.v[k] < num: return False
        return True

    def move(self, m):
        res = Vert({})
        for k, num in m.v.items():
            res.v[k] = self.v[k] - num
        return res

class InEqualtion:
    """
    e.g.
    3*c0 + 2*c1 <= 4
    <=> 
    coefficient[0] = 3, coefficient[1] = 2, rhs = 4
    """
    coefficient: dict[int, float]
    rhs: float

    def __init__(self):
        self.coefficient = {}
        self.rhs = None

    def is_satisfied(self, v: Vert) -> bool:
        tot = 0
        for k, it in v.v.items():
            if self.coefficient.get(k) is None: 
                continue
            tot += self.coefficient[k] * it
            if (tot > self.rhs):
                return False
        return True

class PackRule:
    """
    cids: pack rule is applied on set of categories
    weight constraints: tot <= 4.5 kg
    price constraints:  tot <= 150
    number constraints: total <= 6 and food <=3
    """
    cids : set[int]
    Ws   : list[tuple[set[int], float]] # weight constraints
    Ps   : list[tuple[set[int], float]] # price constraints
    Ns   : list[tuple[set[int], float]] # number constraints
    ineqs: list[InEqualtion]  # corresponding inequaltions
    g    : set[Vert]                    # corresponding graph

    def __init__(self, d: dict):
        self.cids = set(d['cids'])
        self.Ws = [(set(it['subcids']), it['W']) for it in d['Ws']]
        self.Ps = [(set(it['subcids']), it['P']) for it in d['Ps']]
        self.Ns = [(set(it['subcids']), it['N']) for it in d['Ns']]
        self.ineqs = []
        self.g = set()

    def gen_inequals(self, items: list[Item]):
        # generate general constraints 
        # e.g. it0 <= 3, it1 <= 4
        for it in items:
            if it.cid not in self.cids: continue
            ineq = InEqualtion()
            ineq.coefficient[it.idx] = 1
            ineq.rhs = it.num
            self.ineqs.append(ineq)

        # generate weight constraints
        # e.g. it0 * w0 + it1 * w1 ... <= W
        for c in self.Ws:
            subcids = c[0]
            ineq = InEqualtion()
            for it in items:
                if it.cid not in subcids: continue
                ineq.coefficient[it.idx] = it.w
            ineq.rhs = c[1]
            self.ineqs.append(ineq)

        # generate price constraints
        # e.g. it0 * p0 + it1 * p1 ... <= P
        for c in self.Ps:
            subcids = c[0]
            ineq = InEqualtion()
            for it in items:
                if it.cid not in subcids: continue
                ineq.coefficient[it.idx] = it.p
            ineq.rhs = c[1]
            self.ineqs.append(ineq)

        # generate num constraints
        # e.g. it0 + it1 + ... <= N
        for c in self.Ns:
            subcids = c[0]
            ineq = InEqualtion()
            for it in items:
                if it.cid not in subcids: continue
                ineq.coefficient[it.idx] = 1
            ineq.rhs = c[1]
            self.ineqs.append(ineq)

    def is_satisfied(self, v: Vert) -> bool:
        for ineq in self.ineqs:
            if not ineq.is_satisfied(v): return False
        return True

    def is_valid(self, v: Vert) -> bool:
        if (not self.is_satisfied(v)): return False
        for k in v.v.keys():
            v.v[k] += 1
            if (self.is_satisfied(v)):
                v.v[k] -= 1
                return False
            v.v[k] -= 1
        return True

    def search(self, items: list[Item], vec: Vert, ith: int):
        if (ith == len(items)):
            if (not self.is_valid(vec)):
                return
            e = Vert(vec.v)
            print("Add edge: ", e)
            self.g.add(e)
            return

        for i in range(items[ith].num, -1, -1):
            vec.v[items[ith].idx] = i
            self.search(items, vec, ith + 1)
            vec.v[items[ith].idx] = 0

    def gen_edges(self, items: list[Item]):
        subitems: list[Item] = []
        for it in items:
            if it.idx in self.cids:
                subitems.append(it)
        self.g.clear()
        vec = Vert({it.idx: 0 for it in items})
        self.search(items, vec, 0)

def sol(items: list[Item], pack_rules: list[PackRule]):
    mem: dict[Vert, int] = {}
    pre: dict[Vert, tuple[Vert, Vert]] = {}
    que: Queue[Vert] = Queue()
    edges: set[Vert] = set()

    for i in range(len(pack_rules)):
        pack_rules[i].gen_inequals(items)
        pack_rules[i].gen_edges(items)
        edges = edges.union(pack_rules[i].g)

    source = Vert({it.idx: it.num for it in items})
    target = Vert({it.idx: 0 for it in items})

    mem[source] = 0
    que.put(source)

    while not que.empty():
        c: Vert = que.get()

        print("Reach status: ", c)
        if (c == target):
            while (c != source):
                c, e = pre[c]
                print("Pack: ", e)
            break
        for edge in edges:
            if not c.feasible(edge): continue
            suc = c.move(edge)
            if mem.get(suc) is None or mem[suc] > mem[c] + 1:
                mem[suc] = mem[c] + 1
                pre[suc] = (c, edge)
                que.put(suc)

def test(data):
    items = [Item(it) for it in data['items']]
    pack_rules = [PackRule(it) for it in data['pack-rules']]
    sol(items, pack_rules)

if __name__ == "__main__":
    import json
    data = json.load(open("test.json", "r"))
    test(data)
