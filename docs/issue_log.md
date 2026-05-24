# 问题日志

本文件记录环境、数据、代码和实验问题。

## ISSUE-20260524-001 - `GIT_SSH_COMMAND` 反斜杠路径被 `ssh` 误解析

### 日期

2026-05-24

### 类型

environment / git

### 现象

首个 push 使用：

```powershell
$env:GIT_SSH_COMMAND='ssh -i C:\Users\Eddy\.ssh\github_key -o IdentitiesOnly=yes'
git push -u origin main
```

push 成功，但输出警告：

```text
Warning: Identity file C:UsersEddy.sshgithub_key not accessible: No such file or directory.
```

### 证据

GitHub 接受了 push，并创建了 `origin/main`；但警告说明显式 `-i` 路径没有被正确解析，实际成功依赖了 `C:\Users\Eddy\.ssh\config` 中的 `github.com` 配置。

### 根因或当前假设

`GIT_SSH_COMMAND` 传给 `ssh` 后，Windows backslash 被当作转义字符处理，导致 `C:\Users\Eddy\.ssh\github_key` 变成不可访问的 `C:UsersEddy.sshgithub_key`。

### 修复或 workaround

在 `GIT_SSH_COMMAND` 中使用 forward slash 路径：

```powershell
$env:GIT_SSH_COMMAND='ssh -i C:/Users/Eddy/.ssh/github_key -o IdentitiesOnly=yes'
```

### 验证

```powershell
ssh -i C:/Users/Eddy/.ssh/github_key -o IdentitiesOnly=yes -T git@github.com
```

输出：

```text
Hi EddyHai57! You've successfully authenticated, but GitHub does not provide shell access.
```

### 状态

Closed

未来 issue 必须记录：

- 日期
- 类型：environment、data、code、training、evaluation、documentation
- 现象
- 证据
- 根因或当前假设
- 修复或 workaround
- 验证
- 状态：open、mitigated、closed
