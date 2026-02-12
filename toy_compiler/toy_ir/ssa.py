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
