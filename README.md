# NBER Weekly Reader

每周从 NBER 官方目录中挑选已经超过18个月开放期、尚未推送过且符合个人兴趣的 Working Papers，并通过电子邮件发送。

## 它如何工作

1. 从 NBER 官方、每周更新的 TSV 元数据读取标题、摘要、作者、日期和研究项目。
2. 只保留发布超过18个月的论文，不尝试绕过任何访问限制。
3. 主体选择刚刚跨过18个月开放线的最新一周，再加入少量全历史高匹配论文。
4. 根据主题词、NBER Program、喜欢的作者及示例论文评分。
5. 排除已发送的论文，生成带摘要和免费 PDF 链接的邮件；同一自然周不会重复发送。

## 初次设置

1. 安装 Python 3.10 或更高版本。本程序只使用 Python 标准库。
2. 将 `config.example.json` 复制为 `config.json`。
3. 编辑 `config.json`：填写兴趣和邮箱。
4. 如果使用 Gmail，请在 Google 账户开启两步验证并创建“应用专用密码”，不要填写日常登录密码。
5. 在 Windows PowerShell 中设置密码：

   ```powershell
   setx NBER_SMTP_PASSWORD "你的应用专用密码"
   ```

   设置后重新打开终端。

## 先预览，不发送

双击 `run_preview.bat`，或者运行：

```powershell
python nber_digest.py --config config.json --refresh
```

程序会生成 `preview.html`，但不会把论文记为已发送。

## 发送邮件

```powershell
python nber_digest.py --config config.json --refresh --send
```

只有发送成功后，论文才会写入 `state.json`，以后不会重复推荐。

## 每周自动运行（Windows）

打开“任务计划程序”，创建基本任务：

- 触发器：每周一次，例如星期一上午8点；
- 操作：启动 `run_send.bat`；
- “起始于”填写本文件夹的完整路径；
- 确保执行任务的 Windows 账户能够读取 `NBER_SMTP_PASSWORD`。

电脑在执行时需要开机并联网。若需要电脑关机时也能运行，可改用 GitHub Actions 或云服务器，并将邮箱应用密码保存为加密 Secret。

也可以在完成 Gmail 应用密码设置后，用 PowerShell 运行 `install_startup_task.ps1`。它会创建一个登录时触发的任务；程序内置“每自然周最多发送一次”的保护，因此一周内多次开机不会重复发信。

## 调整兴趣

- `topics`：短语与权重，数字越大越重要；可填写中英文，但 NBER 摘要主要是英文。
- `avoid_topics`：出现后大幅降权。
- `programs`：优先的 NBER 研究项目代码，例如货币经济学为 `ME`、国际金融与宏观经济学为 `IFM`。论文摘要页会列出所属项目。
- `authors`：喜欢的作者姓名。
- `liked_papers`：喜欢的论文编号，例如 `w12345`。程序会从这些论文的标题和摘要中学习常见词。
- `liked_titles`：喜欢的论文标题；即使尚未成为 NBER Working Paper，也可以用于建立兴趣画像。

建议先运行几次预览，再调整权重。删除 `state.json` 会清除推送历史。

## 隐私与安全

- 配置文件里不保存邮箱密码；密码从环境变量读取。
- 不要把包含 `config.json`、`state.json` 或密码的文件上传到公开仓库。
- 邮件中的摘要来自 NBER 元数据，PDF 链接指向 NBER 官方网站。

