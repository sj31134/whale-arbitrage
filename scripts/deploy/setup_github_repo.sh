#!/bin/bash
# GitHub 저장소 생성 및 푸시 스크립트

set -e

REPO_NAME=${1:-"whale-arbitrage"}
GITHUB_USER=${2:-""}

if [ -z "$GITHUB_USER" ]; then
    echo "❌ 사용법: $0 [저장소이름] [GitHub사용자명]"
    echo "예시: $0 whale-arbitrage yourusername"
    exit 1
fi

echo "🚀 GitHub 저장소 설정 시작..."
echo "저장소 이름: $REPO_NAME"
echo "GitHub 사용자: $GITHUB_USER"

# Git 저장소 확인
if [ ! -d ".git" ]; then
    echo "Git 저장소를 초기화합니다..."
    git init
fi

# 원격 저장소 확인
if git remote | grep -q "^origin$"; then
    echo "⚠️  원격 저장소 'origin'이 이미 존재합니다."
    echo "기존 원격 저장소를 제거하시겠습니까? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        git remote remove origin
    else
        echo "기존 원격 저장소를 사용합니다."
        exit 0
    fi
fi

# GitHub CLI로 저장소 생성 시도
if command -v gh &> /dev/null; then
    echo "GitHub CLI를 사용하여 저장소를 생성합니다..."
    gh repo create "$REPO_NAME" --public --source=. --remote=origin --push
    echo "✅ 저장소 생성 및 푸시 완료!"
else
    echo "GitHub CLI가 설치되어 있지 않습니다."
    echo ""
    echo "다음 단계를 수동으로 수행하세요:"
    echo ""
    echo "1. GitHub 웹사이트에서 저장소 생성:"
    echo "   https://github.com/new"
    echo "   Repository name: $REPO_NAME"
    echo ""
    echo "2. 다음 명령어 실행:"
    echo "   git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
fi

