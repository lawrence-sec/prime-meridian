# Git Setup — Prime Meridian

Run these commands in order after creating your GitHub repo.

## 1. Create the repo on GitHub
Go to github.com/new
- Name: prime-meridian
- Visibility: Public
- Do NOT initialize with README (we have one)

## 2. Initialize and push

cd prime-meridian
git init
git add .
git commit -m "init: Prime Meridian project structure"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/prime-meridian.git
git push -u origin main

## 3. Confirm
Visit https://github.com/YOUR_USERNAME/prime-meridian
