from collections import defaultdict
from toy_compiler.toy_ir.non_ssa_ir import Function, BasicBlock, Phi
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


def rename_ssa(func: Function, dom_tree: dict):
    version = defaultdict(int)
    stack = defaultdict(list)

    def new_name(var):
        i = version[var]
        version[var] += 1
        name = f"{var}_{i}"
        stack[var].append(name)
        return name

    def cur_name(var):
        return stack[var][-1]

    def rename_block(bb: BasicBlock):
        pushed = []  # 记录block新定义了哪些变量，用于回溯
        # 1. phi的defs
        for inst in bb.insts:
            if isinstance(inst, Phi):
                new = new_name(inst.dst)
                pushed.append(inst.dst)
                inst.dst = new

        # 2. 普通指令
        for inst in bb.insts:
            if isinstance(inst, Phi):
                continue

            # rename uses
            for i, v in enumerate(inst.uses()):
                inst.rename_use(v, cur_name(v))
            # rename defs
            for v in inst.defs():
                new = new_name(v)
                pushed.append(v)
                inst.rename_def(v, new)

        # 3. terminator
        if bb.terminator:
            for i, v in enumerate(bb.terminator.uses()):
                bb.terminator.rename_use(v, cur_name(v))

        # 3. 处理succs中phi的incomings
        for succ in bb.succs:
            for inst in succ.insts:
                if isinstance(inst, Phi):
                    orig = inst.incomings[bb]
                    inst.incomings[bb] = cur_name(orig)

        # 4. DFS dominator tree
        for child in dom_tree.get(bb, []):
            rename_block(child)
        # 5. 回溯
        for v in reversed(pushed):
            stack[v].pop()

    rename_block(func.entry)
