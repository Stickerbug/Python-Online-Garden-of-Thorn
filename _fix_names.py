import re

with open('game_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

patterns = [
    (r'f"玩家\{player_id \+ 1\}"', r'f"{self.pn(player_id)}"'),
    (r"f'玩家\{player_id \+ 1\}'", r"f'{self.pn(player_id)}'"),
    (r'f"玩家\{pid \+ 1\}"', r'f"{self.pn(pid)}"'),
    (r"f'玩家\{pid \+ 1\}'", r"f'{self.pn(pid)}'"),
    (r'f"玩家\{owner_id \+ 1\}"', r'f"{self.pn(owner_id)}"'),
    (r'f"玩家\{attacker_id \+ 1\}"', r'f"{self.pn(attacker_id)}"'),
    (r'f"玩家\{target_id \+ 1\}"', r'f"{self.pn(target_id)}"'),
    (r'f"玩家\{opp_id \+ 1\}"', r'f"{self.pn(opp_id)}"'),
    (r'f"玩家\{winner \+ 1\}"', r'f"{self.pn(winner)}"'),
    (r'f"玩家\{pidx \+ 1\}"', r'f"{self.pn(pidx)}"'),
    (r'f"玩家\{attacker \+ 1\}"', r'f"{self.pn(attacker)}"'),
    (r'f"玩家\{i \+ 1\}"', r'f"{self.pn(i)}"'),
    (r'f"玩家\{current_player \+ 1\}"', r'f"{self.pn(current_player)}"'),
]

for pat, repl in patterns:
    content = re.sub(pat, repl, content)

remaining = len(re.findall(r'玩家\{.*?\+ ?1\}', content))
print(f'Remaining 玩家{{x+1}} patterns: {remaining}')

with open('game_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
