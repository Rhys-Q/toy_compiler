from dataclasses import dataclass, field
from abc import ABC, abstractmethod


class Instruction(ABC):
    def defs(self) -> list[str]:
        """
        返回该指令定义的变量名列表
        非 SSA 中通常是 0 或 1 个
        """
        raise NotImplementedError

    def uses(self) -> list[str]:
        """
        返回该指令使用的变量名列表
        """
        raise NotImplementedError

    def __str__(self) -> str:
        """
        IR 打印形式，用于 debug
        """
        raise NotImplementedError


class Assign(Instruction):
    def __init__(self, lhs: str, rhs: str | int):
        """
        lhs = rhs
        rhs 可以是变量名（str）或常量（int），因为是toy，所以只考虑这两种情况
        """
        self.lhs = lhs
        self.rhs = rhs

    def defs(self) -> list[str]:
        return [self.lhs]

    def uses(self) -> list[str]:
        # 常量不算 use
        if isinstance(self.rhs, str):
            return [self.rhs]
        return []

    def __str__(self) -> str:
        return f"{self.lhs} = {self.rhs}"


class BinaryOp(Instruction):
    def __init__(self, op: str, dst: str, src1: str | int, src2: str | int):
        """
        dst = src1 op src2
        src 可以是变量名（str）或常量（int），因为是toy，所以只考虑这两种情况
        """
        self.op = op
        self.dst = dst
        self.src1 = src1
        self.src2 = src2

    def defs(self) -> list[str]:
        return [self.dst]

    def uses(self) -> list[str]:
        # 常量不算 use
        outs = []
        if isinstance(self.src1, str):
            outs.append(self.src1)
        if isinstance(self.src2, str):
            outs.append(self.src2)
        return outs

    def __str__(self) -> str:
        return f"{self.dst} = {self.src1} {self.op} {self.src2}"


class Terminator(Instruction):
    pass


class Branch(Terminator):
    def __init__(self, cond: str, true_bb, false_bb):
        """
        br cond, true_bb, false_bb

        cond: 条件变量名（非 SSA）
        true_bb / false_bb: BasicBlock
        """
        self.cond = cond
        self.true_bb = true_bb
        self.false_bb = false_bb

    def defs(self) -> list[str]:
        # Branch 不定义任何变量
        return []

    def uses(self) -> list[str]:
        # 使用条件变量
        return [self.cond]

    def successors(self):
        """
        CFG 边的来源
        """
        return [self.true_bb, self.false_bb]

    def __str__(self) -> str:
        return f"br {self.cond}, {self.true_bb.name}, {self.false_bb.name}"


class Jump(Terminator):
    def __init__(self, bb):
        """
        jump bb

        bb: 跳转目标 BasicBlock
        """
        self.bb = bb

    def defs(self) -> list[str]:
        # Jump 不定义任何变量
        return []

    def uses(self) -> list[str]:
        # Jump 不使用任何变量
        return []

    def successors(self):
        """
        CFG 边的来源
        """
        return [self.bb]

    def __str__(self) -> str:
        return f"jump {self.bb.name}"


class Return(Terminator):
    def __init__(self, ret: str | int | None):
        """
        return ret

        ret: 返回值，变量名（str）或常量（int），或者 None 表示无返回值
        """
        self.ret = ret

    def defs(self) -> list[str]:
        # Return 定义返回值
        return []

    def uses(self) -> list[str]:
        # Return 不使用任何变量
        return [self.ret] if isinstance(self.ret, str) else []

    def successors(self):
        """
        CFG 边的来源
        """
        return []

    def __str__(self) -> str:
        return f"return {self.ret}"


@dataclass
class BasicBlock:
    name: str
    terminator: Terminator | None
    insts: list[Instruction]
    succs: list["BasicBlock"] = field(default_factory=list)
    preds: list["BasicBlock"] = field(default_factory=list)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, BasicBlock) and self.name == other.name


@dataclass
class Function:
    name: str
    blocks: list[BasicBlock] = field(default_factory=list)
    entry: BasicBlock | None = None

    def new_block(self, name: str) -> BasicBlock:
        bb = BasicBlock(name, None, [])
        self.blocks.append(bb)
        if self.entry is None:
            self.entry = bb
        return bb

    def build_cfg(self):
        # 清空原有链接（如果重新 build）
        for bb in self.blocks:
            bb.succs = []
            bb.preds = []

        for bb in self.blocks:
            term = bb.terminator
            if term is None:
                raise ValueError(f"BasicBlock {bb.name} must have a terminator")

            # 获取 successor list
            for succ in term.successors():
                bb.succs.append(succ)
                succ.preds.append(bb)


class IRBuilder:
    def __init__(self, function):
        self.func = function
        self.cur_bb = function.entry

    def set_block(self, bb):
        self.cur_bb = bb

    def emit(self, inst):
        self.cur_bb.insts.append(inst)

    def emit_terminator(self, term):
        self.cur_bb.terminator = term


def print_function(func):
    print(f"Function {func.name}:")
    for bb in func.blocks:
        print(f"  Block {bb.name}:")
        for inst in bb.insts:
            print(f"    {inst}")
        if bb.terminator:
            print(f"    {bb.terminator}")
        print(f"    succs: {[b.name for b in bb.succs]}")
        print(f"    preds: {[b.name for b in bb.preds]}")
