#!/bin/bash
# GitHub 저장소 생성 및 푸시 스크립트

set -e

GITHUB_USER="JunyongLee9385"
REPO_NAME="whale-arbitrage"

echo "🚀 GitHub 저장소 생성 및 푸시 시작..."
echo "사용자: $GITHUB_USER"
echo "저장소: $REPO_NAME"

# 현재 디렉토리 확인
if [ ! -d ".git" ]; then
    echo "❌ Git 저장소가 아닙니다."
    exit 1
fi

# GitHub CLI 확인
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI 발견"
    
    # 인증 확인
    if gh auth status &> /dev/null; then
        echo "✅ GitHub 인증 완료"
        
        # 저장소 생성 및 푸시
        echo "📦 GitHub 저장소 생성 중..."
        gh repo create "$REPO_NAME" --public --source=. --remote=origin --push 2>&1
        
        if [ $? -eq 0 ]; then
            echo "✅ 저장소 생성 및 푸시 완료!"
            echo ""
            echo "🌐 저장소 URL: https://github.com/$GITHUB_USER/$REPO_NAME"
            exit 0
        fi
    else
        echo "⚠️ GitHub 인증 필요"
        echo "다음 명령어로 인증하세요:"
        echo "  gh auth login"
        exit 1
    fi
else
    echo "⚠️ GitHub CLI가 설치되어 있지 않습니다."
    echo ""
    echo "수동으로 진행하세요:"
    echo ""
    echo "1. GitHub에서 저장소 생성:"
    echo "   https://github.com/new"
    echo "   Repository name: $REPO_NAME"
    echo ""
    echo "2. 다음 명령어 실행:"
    echo "   git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    exit 1
fi

