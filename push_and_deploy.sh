#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ $# -lt 1 ]; then
  echo "用法: ./push_and_deploy.sh \"本次提交说明\""
  exit 1
fi

MSG="$1"

git status

git add .

if git diff --cached --quiet; then
  echo "没有需要提交的变更，跳过 commit。"
else
  git commit -m "$MSG"
fi

git push origin main

if [ -x ./deploy.sh ]; then
  ./deploy.sh
else
  echo "未找到可执行的 deploy.sh，已跳过部署步骤。"
fi

