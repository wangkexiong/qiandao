#!/usr/bin/env bash

if git status | grep accounts.txt; then
  git config --global user.name $GITHUB_USER
  git config --global user.email $GITHUB_EMAIL

  # APPVEYOR checkout latest commit (detached HEAD)
  git clone https://$GITHUB_TOKEN@github.com/$APPVEYOR_REPO_NAME qiandao
  cp accounts.txt qiandao/.
  pushd qiandao

  git add accounts.txt

  MSG=`git log --pretty=format:%s -1`
  REPEAT="Daily Working..."
  if [ "$MSG" = "$REPEAT" ]; then
    git commit --amend -m "$REPEAT" --date=now
    git push --force
  else
    git commit -a -m "$REPEAT"
    git push
  fi

  popd
fi
