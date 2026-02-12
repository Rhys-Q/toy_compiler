from collections import defaultdict
from toy_compiler.toy_ir.non_ssa_ir import Assign, Function, Instruction, BasicBlock
from collections import defaultdict


def compute_dominator_sets(func: Function):
    """
    返回:
        dom: dict[BasicBlock, set[BasicBlock]]
    """
    blocks = func.blocks
    entry = func.entry

    # 初始化
    dom = {}
    for b in blocks:
        if b is entry:
            dom[b] = {b}
        else:
            dom[b] = set(blocks)

    changed = True
    while changed:
        changed = False
        for b in blocks:
            if b is entry:
                continue

            if not b.preds:
                new_dom = {b}
            else:
                # 交集所有前驱的 dom
                new_dom = set(dom[b.preds[0]])
                for p in b.preds[1:]:
                    new_dom &= dom[p]
                new_dom.add(b)

            if new_dom != dom[b]:
                dom[b] = new_dom
                changed = True

    return dom


def print_dominators(dom):
    for b, ds in dom.items():
        names = sorted(bb.name for bb in ds)
        print(f"dom({b.name}) = {names}")


def compute_idom(func: Function, dom: dict):
    """
    输入:
        dom: dict[BasicBlock, set[BasicBlock]]
    返回:
        idom: dict[BasicBlock, BasicBlock | None]
    """
    idom = {}
    entry = func.entry

    idom[entry] = None

    for b in func.blocks:
        if b is entry:
            continue

        candidates = dom[b] - {b}
        assert candidates, f"Block {b.name} has no dominators?"

        # 找那个“不被其他候选支配”的
        for d in candidates:
            is_idom = True
            for other in candidates:
                if other is d:
                    continue
                # 如果 other 支配 d，那么 d 不是最近的
                if d in dom[other]:
                    is_idom = False
                    break
            if is_idom:
                idom[b] = d
                break

        assert b in idom, f"idom not found for {b.name}"

    return idom


def print_idom(idom):
    for b, d in idom.items():
        if d is None:
            print(f"idom({b.name}) = None")
        else:
            print(f"idom({b.name}) = {d.name}")


def build_dominator_tree(func: Function, idom: dict):
    """
    返回:
        dom_tree: dict[BasicBlock, list[BasicBlock]]
    """
    dom_tree = defaultdict(list)

    for b, parent in idom.items():
        if parent is not None:
            dom_tree[parent].append(b)

    return dom_tree


def print_dom_tree(dom_tree, root, indent=0):
    print("  " * indent + root.name)
    for child in dom_tree.get(root, []):
        print_dom_tree(dom_tree, child, indent + 1)


def build_dominance_frontier(func: Function, idom: dict):
    # Cytron 算法
    df = {}
    # init
    for b in func.blocks:
        df[b] = set()

    for b in func.blocks:
        for p in b.preds:
            runner = p

            while runner != idom[b]:
                df[runner].add(b)
                runner = idom[runner]
    return df


def print_dominance_frontier(df):
    for b, ds in df.items():
        if ds:
            print(f"df({b.name}) = {[d.name for d in ds]}")
        else:
            print(f"df({b.name}) = None")


class Phi(Instruction):
    def __init__(self, dst: str, incomings: dict["BasicBlock", str]):
        """
        dst = φ(...)
        incomings: {pred_bb: var_name}
        """
        self.dst = dst
        self.incomings = incomings

    def defs(self):
        return [self.dst]

    def uses(self):
        return list(self.incomings.values())

    def __str__(self):
        args = ", ".join(f"{bb.name}: {v}" for bb, v in self.incomings.items())
        return f"{self.dst} = phi({args})"


def insert_phi(func: Function, df: dict):
    # 1. 收集def blocks
    def_blocks = {}
    for bb in func.blocks:
        for inst in bb.insts:
            for v in inst.defs():
                def_blocks.setdefault(v, set()).add(bb)

    # 2. 对每个变量做phi 插入
    for var, blocks in def_blocks.items():
        worklist = list(blocks)
        has_phi = set()

        while worklist:
            b = worklist.pop()

            for y in df.get(b, []):
                if y not in has_phi:
                    # 在y的开头插入PHI
                    incomings = {pred: var for pred in y.preds}
                    phi = Phi(var, incomings)
                    y.insts.insert(0, phi)
                    has_phi.add(y)
                    # phi 本身也是def
                    if y not in blocks:
                        blocks.add(y)
                        worklist.append(y)
