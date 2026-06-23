# Git 速查笔记(03 Python 工程)

> Git = 给代码拍"存档点"的工具,像游戏存档。仓库藏在项目根目录的隐藏文件夹 `.git/` 里,管理【整个项目】,不是某个子文件夹里的代码文件。

## 核心心智模型:三个区

改一次代码,要经过三个区才进存档:

```
你改文件            你挑要存的              正式拍存档
工作区  ──git add──▶  暂存区  ──git commit──▶  仓库(历史)
```

比喻(拍合影):工作区 = 所有改动;`add` = 点名谁入镜;`commit` = 咔嚓拍下 + 写备注。

## 日常循环(每天 80% 在用)

```
放心改 → git status(看状态)→ git diff(看改了啥)
       → 满意就 add + commit;不满意就 restore 丢掉
```

## 常用命令

| 命令 | 作用 |
|---|---|
| `git init` | 在项目里建仓库(只做一次) |
| `git status` | 看哪些文件 untracked(没见过)/ modified(改了) |
| `git diff` | 看具体改了哪几行(`+` 新增、`-` 删除) |
| `git add .` | 把改动放进暂存区(`.` = 全部) |
| `git commit -m "说明"` | 拍一个存档点 |
| `git log --oneline` | 翻看历史存档点 |
| `git restore <文件>` | 后悔药:丢掉【还没提交】的改动,退回上个存档 |

## 一次性设置(提交身份)

```
git config --global user.name  "你的名字"
git config --global user.email "你的邮箱"
```

会署进每个 commit;推到 GitHub 也用它认人。

## ⚠️ 安全铁律

- `.env`(API key)、`.venv/`、`__pycache__/` 绝不提交 → 写进 `.gitignore`。
- Git 历史是永久的:密钥一旦提交,就永远留在历史里(真实泄密事故的常见原因)。
