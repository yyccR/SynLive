#!/usr/bin/env bash
# 幂等地给 musereal.py / nerfreal.py 的 tts 分支注入 --tts azure → AzureTTS。
#
# 为什么需要：codewithgpu 镜像 vjo1Y6NJ3N 的 ttsreal.py 无 azure 插件，tts 分支只有
# edgetts/gpt-sovits/xtts。我们挂载了 ttsreal_azure.py（AzureTTS 类），还要在 avatar
# 实现里给它一个分支，否则 self.tts 永远不初始化、/human 崩。
#
# metahuman-stream 按 --model ���载对应文件（musetalk→musereal.py，ernerf→nerfreal.py，
# wav2lip→lipreal.py），所以两个主流文件都要 patch，切模型时 --tts azure 都能接线。
# （lipreal.py 结构相同，按需可追加。）
#
# 用 Python heredoc 改文件（而非 sed），避免在 deploy 脚本的 bash -c 里层层转义。
# 幂等：已含 azure 分支则跳过。两个文件的 needle 相同：'self.tts = XTTS(opt,self)'，
# 缩进也一致（8 空格 elif）。
set -euo pipefail
cd /root/metahuman-stream

inject_one() {
  local p="$1"
  if [ ! -f "$p" ]; then
    echo "[patch-tts-azure] $p 不存在，跳过"
    return 0
  fi
  if grep -q 'opt.tts == "azure"' "$p"; then
    echo "[patch-tts-azure] $p 已含 azure 分支，跳过"
    return 0
  fi
  python - "$p" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
needle = 'self.tts = XTTS(opt,self)'
inject = (
    needle + '\n'
    '        elif opt.tts == "azure":\n'
    '            from ttsreal_azure import AzureTTS\n'
    '            self.tts = AzureTTS(opt,self)'
)
if needle not in s:
    raise SystemExit(f'[patch-tts-azure] {p} 未找到 XTTS 接线点，结构可能变了，请人工核对')
open(p, 'w', encoding='utf-8').write(s.replace(needle, inject, 1))
print(f'[patch-tts-azure] 已在 {p} 注入 --tts azure 分支')
PY
}

inject_one musereal.py
inject_one nerfreal.py
