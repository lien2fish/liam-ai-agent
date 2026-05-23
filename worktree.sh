#!/bin/bash
# Worktree 管理腳本 - 仿照 Boris Cherny 的平行作業方式
# 用法：
#   ./worktree.sh init       → 建立 work/2 ~ work/5 共4個 worktree
#   ./worktree.sh list       → 列出所有 worktree
#   ./worktree.sh clean      → 刪除所有額外的 worktree
#   ./worktree.sh go <n>     → 印出第 n 個 worktree 路徑（搭配 cd 使用）

MAIN_DIR="/Users/lien/Downloads/Liam AI agent"
WORK_BASE="/Users/lien/Downloads/Liam AI agent/work"

case "$1" in
  init)
    for i in 2 3 4 5; do
      WORK_DIR="$WORK_BASE/$i"
      BRANCH="work-$i"
      if [ -d "$WORK_DIR" ]; then
        echo "⏭  work/$i 已存在，跳過"
      else
        cd "$MAIN_DIR"
        git worktree add "$WORK_DIR" -b "$BRANCH" main 2>/dev/null || \
        git worktree add "$WORK_DIR" "$BRANCH" 2>/dev/null
        echo "✅ 建立 work/$i → branch: $BRANCH"
      fi
    done
    echo ""
    echo "📋 目前所有 worktree："
    git -C "$MAIN_DIR" worktree list
    ;;
  list)
    git -C "$MAIN_DIR" worktree list
    ;;
  clean)
    for i in 2 3 4 5; do
      WORK_DIR="$WORK_BASE/$i"
      if [ -d "$WORK_DIR" ]; then
        git -C "$MAIN_DIR" worktree remove "$WORK_DIR" --force
        echo "🗑  已刪除 work/$i"
      fi
    done
    git -C "$MAIN_DIR" worktree prune
    ;;
  go)
    N="$2"
    if [ "$N" = "1" ]; then
      echo "$MAIN_DIR"
    else
      echo "$WORK_BASE/$N"
    fi
    ;;
  *)
    echo "用法："
    echo "  ./worktree.sh init     建立 work/2 ~ work/5"
    echo "  ./worktree.sh list     列出所有 worktree"
    echo "  ./worktree.sh clean    清除所有額外 worktree"
    echo "  ./worktree.sh go <n>   取得第 n 個 worktree 路徑"
    ;;
esac
