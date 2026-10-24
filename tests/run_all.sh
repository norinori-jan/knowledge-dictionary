#!/usr/bin/env bash
# 全テストを順に実行します。1つでも失敗（NGあり／JSエラーあり／異常終了）したら、終了コード1で終わります。
# 使い方：リポジトリの直下で  bash tests/run_all.sh
set -u
export KD_ROOT="${KD_ROOT:-$(pwd)}"
export KD_OUT="${KD_OUT:-/tmp/kd-out}"
mkdir -p "$KD_OUT"
cp tests/qr-export.json "$KD_OUT"/
fail=0
for f in run.py run2.py run3.py run4.py run5.py run6.py run7.py run8.py run9.py run10.py run11.py run12.py run13.py run14.py; do
  out=$(timeout 280 python3 -I "tests/$f" 2>&1); code=$?
  if [ $code -ne 0 ] || echo "$out" | grep -qE "^  NG |JSエラー: \[" ; then
    echo "（$f が失敗したので、もう1回だけ流します）"
    out=$(timeout 280 python3 -I "tests/$f" 2>&1); code=$?
  fi
  summary=$(echo "$out" | grep -E "^結果|JSエラー" | tr '\n' ' ')
  if [ $code -ne 0 ] || echo "$out" | grep -qE "^  NG |JSエラー: \[" ; then
    echo "NG  $f  $summary"; echo "$out" | tail -40; fail=1
  else
    echo "OK  $f  $summary"
  fi
done
exit $fail
