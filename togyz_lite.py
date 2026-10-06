#!/usr/bin/env python3
"""托古孜库马拉克 (Togyz Kumalak) 极简版。

2x9 坑播棋：播种、3 子吃子、tuz 认领、比 kazan（得分坑）种子数。
纯标准库。
"""

import argparse
import copy
import random
import sys

PITS = 9            # 每方坑数
START_BALLS = 9     # 每坑开局种子数
TOTAL = 2 * PITS * START_BALLS  # 162


class Togyz:
    def __init__(self):
        self.board = [START_BALLS] * (2 * PITS)
        self.kazan = [0, 0]        # 双方得分坑
        self.tuz = [None, None]    # 双方认领的 tuz 坑位（在对方一侧）
        self.turn = 0
        self.over = False
        self.winner = None  # 0 / 1 / -1(和棋)

    # ---- 基础 ----
    @staticmethod
    def side(pit):
        return 0 if pit < PITS else 1

    def is_tuz(self, pit):
        return pit == self.tuz[0] or pit == self.tuz[1]

    def legal_moves(self, player):
        base = 0 if player == 0 else PITS
        return [base + i for i in range(PITS) if self.board[base + i] > 0]

    # ---- 走子 ----
    def apply_move(self, player, pit):
        if self.over:
            raise ValueError("对局已结束")
        if player != self.turn:
            raise ValueError("还没轮到你")
        base = 0 if player == 0 else PITS
        if not (base <= pit < base + PITS):
            raise ValueError("只能走自己一侧的坑")
        n = self.board[pit]
        if n <= 0:
            raise ValueError("空坑不能走")

        self.board[pit] = 0
        pos = pit
        for _ in range(n):
            pos = (pos + 1) % (2 * PITS)
            if pos == pit:  # 绕满一圈时跳过起点坑
                pos = (pos + 1) % (2 * PITS)
            if self.is_tuz(pos):
                owner = 0 if self.tuz[0] == pos else 1
                self.kazan[owner] += 1
            else:
                self.board[pos] += 1

        # 落子吃子 / 认领 tuz
        if not self.is_tuz(pos) and self.side(pos) != player \
                and self.board[pos] == 3:
            opp_last = (1 - player) * PITS + (PITS - 1)  # 对方第 9 坑不能做 tuz
            self.kazan[player] += 3  # 触发 tuz/吃子的 3 子都归走子方
            if self.tuz[player] is None and pos != opp_last:
                self.tuz[player] = pos
            self.board[pos] = 0

        nxt = 1 - player
        if not self.legal_moves(nxt):
            self._finish()
        else:
            self.turn = nxt

    def _finish(self):
        for pl in (0, 1):
            base = 0 if pl == 0 else PITS
            for i in range(PITS):
                self.kazan[pl] += self.board[base + i]
                self.board[base + i] = 0
        self.over = True
        if self.kazan[0] > self.kazan[1]:
            self.winner = 0
        elif self.kazan[1] > self.kazan[0]:
            self.winner = 1
        else:
            self.winner = -1

    # ---- 渲染 ----
    def render(self):
        def pit_str(i):
            mark = "*" if self.is_tuz(i) else " "
            return f"{self.board[i]:3d}{mark}"
        top = " ".join(pit_str(PITS + i) for i in range(PITS - 1, -1, -1))
        bot = " ".join(pit_str(i) for i in range(PITS))
        return (
            f"乙 kazan: {self.kazan[1]:3d}\n"
            f"  {top}\n"
            f"  {bot}\n"
            f"甲 kazan: {self.kazan[0]:3d}   (*=tuz)\n"
        )


# ---- AI ----
def ai_choose(game, player, rng):
    moves = game.legal_moves(player)
    best, best_score = None, None
    for mv in moves:
        g2 = copy.deepcopy(game)
        tuz_before = g2.tuz[player]
        kazan_before = g2.kazan[player]
        g2.apply_move(player, mv)
        score = (g2.kazan[player] - kazan_before) * 10
        if g2.tuz[player] is not None and tuz_before is None:
            score += 25  # 认领 tuz 长期收益大
        # 己方残子多一点点好（局面活性）
        base = 0 if player == 0 else PITS
        score += sum(g2.board[base:base + PITS]) * 0.01
        score += rng.random() * 0.001
        if best_score is None or score > best_score:
            best, best_score = mv, score
    return best


def play_auto(games, seed, verbose):
    rng = random.Random(seed)
    wins = [0, 0, 0]  # 甲胜, 乙胜, 和棋
    for gi in range(games):
        g = Togyz()
        g.turn = gi % 2  # 轮流先手
        while not g.over:
            mv = ai_choose(g, g.turn, rng)
            g.apply_move(g.turn, mv)
        if g.winner == -1:
            wins[2] += 1
            res = "和棋"
        else:
            wins[g.winner] += 1
            res = f"{'甲' if g.winner == 0 else '乙'}胜"
        if verbose:
            print(f"第 {gi + 1}/{games} 局：{res}（{g.kazan[0]}:{g.kazan[1]}）")
    print(f"总计：甲胜 {wins[0]}，乙胜 {wins[1]}，和棋 {wins[2]}")
    return wins


def play_interactive():
    if not sys.stdin.isatty():
        print("交互模式需要终端；无头演示请用 --auto", file=sys.stderr)
        sys.exit(2)
    g = Togyz()
    names = ["甲", "乙"]
    while not g.over:
        print(g.render())
        base = 0 if g.turn == 0 else PITS
        print(f"{names[g.turn]}走（输入 1-9 选自己一侧第 n 个坑，q 退出）：")
        try:
            s = input("> ").strip()
        except EOFError:
            break
        if s.lower() == "q":
            break
        try:
            n = int(s)
            if not 1 <= n <= PITS:
                raise ValueError
            g.apply_move(g.turn, base + n - 1)
        except (ValueError, IndexError) as e:
            print(f"非法走法：{e}")
    print(g.render())
    if g.winner == -1:
        print(f"和棋！{g.kazan[0]}:{g.kazan[1]}")
    else:
        print(f"{names[g.winner]}胜！{g.kazan[0]}:{g.kazan[1]}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="托古孜库马拉克 (Togyz Kumalak) 极简版")
    ap.add_argument("--auto", action="store_true", help="AI 对 AI 自动演示")
    ap.add_argument("--games", type=int, default=10, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--verbose", action="store_true", help="自动演示打印每局")
    args = ap.parse_args(argv)
    if args.auto:
        play_auto(args.games, args.seed, args.verbose)
    else:
        play_interactive()


if __name__ == "__main__":
    main()
