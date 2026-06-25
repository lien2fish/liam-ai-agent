#!/bin/bash

LOG="/Users/lien/Downloads/Liam AI agent/cache_cleanup.log"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') 開始清理 ===" >> "$LOG"

# npm cache
npm cache clean --force >> "$LOG" 2>&1
echo "npm cache 已清理" >> "$LOG"

# pip cache
pip3 cache purge >> "$LOG" 2>&1
echo "pip cache 已清理" >> "$LOG"

# Library/Logs
rm -rf ~/Library/Logs/*
echo "Library/Logs 已清理" >> "$LOG"

echo "=== 清理完成 ===" >> "$LOG"
