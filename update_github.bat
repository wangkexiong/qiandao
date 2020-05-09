
IF EXIST update.flag (
    git config --global user.name %GITHUB_USER%
    git config --global user.email %GITHUB_EMAIL%
    git clone https://%GITHUB_TOKEN%@github.com/%APPVEYOR_REPO_NAME% qiandao
    FOR /F "tokens=*" %%A in (update.flag) DO COPY /Y %%A qiandao\%%A
    PUSHD qiandao
    git add .
    git commit --amend -m "Daily Testing..." --date=now
    git push --force
    POPD
)

