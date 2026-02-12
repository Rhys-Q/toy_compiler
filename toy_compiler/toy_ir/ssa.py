from collections import defaultdict
from toy_compiler.toy_ir.non_ssa_ir import Assign, Function


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
