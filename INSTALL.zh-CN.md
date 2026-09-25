# 安装与使用说明（中文）

这份说明写给第一次用的人。看完就能装好、跑通第一节课。技术细节在 [README.zh-CN.md](README.zh-CN.md)。

它做的事：给它一节课的视频（幻灯片讲课，或动作/康复示范），产出一篇逐字级的 Markdown 笔记，重要画面贴在里面。转写在你自己电脑上跑（Whisper），写稿由模型完成，写完会机械核对一遍：转写里 97% 以上的句子必须能在笔记里找到，不够会自己补。

---

## 一、需要准备

1. 一个能跑 Agent Skill 的工具：**Claude Code** 或 **WorkBuddy** 都行（其他支持 SKILL.md 的工具见第四节）。
2. **Python 3.9 以上**。终端里输 `python --version` 能看到版本号就行。
3. **最好有 NVIDIA 显卡**（显存 6G 以上）或 **Apple 芯片的 Mac**（M1 以上）。有显卡时 20 分钟的课 1 到 3 分钟转完；Mac 装上 mlx-whisper 后走 Mac 自己的 GPU，也快很多；都没有也能跑，转写要等和视频差不多长的时间。
4. **磁盘留 4G 左右**：第一次用会自动下载 3G 的 Whisper 模型。

---

## 二、安装技能

### 用 Claude Code

在 Claude Code 里依次输入：

```
/plugin marketplace add miloxzh/transcribe-course
/plugin install transcribe-course@transcribe-course
```

装完关掉会话重开一次（子代理只在会话启动时加载）。

### 用 WorkBuddy

WorkBuddy 内嵌的是 CodeBuddy 命令行，插件命令一样。在 WorkBuddy 的对话框里依次输入：

```
/plugin marketplace add miloxzh/transcribe-course
/plugin install transcribe-course@transcribe-course
```

装完重启 WorkBuddy。技能列表里应该能看到 transcribe-course。

插件命令不管用的话，手动复制也行：

1. 打开仓库页面，点绿色的 **Code** 按钮，选 **Download ZIP**，下载后解压。
2. 把解压出来的 `skills\transcribe-course` 这个文件夹整个复制到
   `C:\Users\你的用户名\.workbuddy\skills\transcribe-course`（Mac 是 `~/.workbuddy/skills/transcribe-course`）
   （`.workbuddy` 是隐藏文件夹，Windows 在资源管理器地址栏直接输这个路径就能进去，Mac 在访达按 Command+Shift+. 显示隐藏目录；没有 `skills` 文件夹就新建一个。）
   复制完检查层级：`transcribe-course` 文件夹里面直接就是 `SKILL.md`，不要套两层。
   也可以在 WorkBuddy 的技能页面用「上传本地技能」选这个文件夹导入。
3. 重启 WorkBuddy。

手动复制这条路只装了技能，没装子代理。没关系：技能自己会判断，开不了子代理就在当前对话里写稿，核对照做，只是过程长一点。

---

## 三、装 Python 包（Windows）

在终端里执行（装进你平时用的那个 Python）：

```
pip install faster-whisper opencv-python numpy Pillow
```

有 NVIDIA 显卡再加一条（这是 faster-whisper 需要的两个 CUDA 库，不用装 CUDA 工具包）：

```
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

国内下载模型慢，先设一个镜像。在 PowerShell 里执行，然后重启工具：

```
setx HF_ENDPOINT https://hf-mirror.com
```

ffmpeg 可装可不装。B 站下载的 AV1 视频装了会快很多：

```
winget install Gyan.FFmpeg
```

Mac 用户跳过这一节，看下一节。

---

## 三（Mac）、Mac 的步骤（整段照做）

Mac 上的差别只有三处：命令叫 `python3`/`pip3`，Whisper 走 Apple 芯片的 GPU 要多装一个包，隐藏目录要按快捷键才看得见。按顺序来：

1. **确认 Python。** 打开「终端」，输入：

   ```
   python3 --version
   ```

   显示 3.9 以上就行。没有的话先装 Homebrew（brew.sh 首页那一条命令），再 `brew install python`。

2. **装 Python 包。**

   ```
   pip3 install faster-whisper opencv-python numpy Pillow
   ```

   Apple 芯片（M1、M2、M3、M4）的 Mac 再加一条，让 Whisper 跑在 Mac 的 GPU 上，装了就自动选用：

   ```
   pip3 install mlx-whisper
   ```

   Intel 芯片的 Mac 不用装这条，会走 CPU，20 分钟的课大约要等 20 分钟。
   （看芯片：左上角苹果菜单 → 关于本机，「芯片」一栏写 Apple M 开头就是 Apple 芯片。）

3. **装 ffmpeg（建议装）。** B 站下载的 AV1 视频抽帧会快很多：

   ```
   brew install ffmpeg
   ```

4. **国内先设模型镜像。** 在终端里执行下面两条，然后重开终端和工具：

   ```
   echo 'export HF_ENDPOINT=https://hf-mirror.com' >> ~/.zshrc
   source ~/.zshrc
   ```

5. **装技能。** 和第二节一样：Claude Code 或 WorkBuddy 里输入
   `/plugin marketplace add miloxzh/transcribe-course`，再 `/plugin install transcribe-course@transcribe-course`，重启。
   手动复制的话，技能目录在 `~/.workbuddy/skills/`（WorkBuddy）或 `~/.claude/skills/`（Claude Code）。
   这些以点开头的目录在访达里默认看不见，按 **Command + Shift + .** 显示；也可以在终端里 `open ~/.workbuddy/skills` 直接打开。

6. **体检。** 第一次用时让它跑环境体检（第五节第 2 步）。Apple 芯片的 Mac 应该看到一行
   「Apple Silicon: mlx-whisper installed → backend mlx」。体检里如果出现一条
   「Class AVFFrameReceiver is implemented in both …」的警告，不用管，实际转写和抽帧各自只用其中一个库；
   真崩了再 `pip3 uninstall opencv-python`，改装 `pip3 install opencv-python-headless`。

7. **抽帧想用 Mac 的硬件解码**（可选）：在工作区的 `transcribe-course.json` 里把 `"hwaccel"` 填成 `"videotoolbox"`。

---

## 四、其他工具（CodeBuddy 命令行、Codex、Cursor 等）

凡是按 Agent Skills 开放标准读 `SKILL.md` 的工具都能用：把 `skills/transcribe-course/` 整个文件夹复制到那个工具的技能目录，重启。CodeBuddy 命令行还可以直接用插件命令：

```
codebuddy plugin marketplace add miloxzh/transcribe-course
codebuddy plugin install transcribe-course@transcribe-course
```

---

## 五、第一次用

1. 新建一个空文件夹，比如 `D:\康复课`，用你的工具打开它（Claude Code 在这个文件夹里启动；WorkBuddy 把它设成工作目录）。
2. 对它说：

   > 用 transcribe-course 技能在这个文件夹建一个工作区，中文的运动康复课，建好后跑一下环境体检。

   它会自动建好目录，并告诉你显卡、ffmpeg、模型这些有没有问题。想自己跑命令也行，`TC` 代表 `python <技能目录>/scripts/tc.py`：

   ```
   TC init . --preset rehab-zh --course "肩关节康复"
   TC doctor --full
   ```

   预设有 `fitness-zh`、`rehab-zh`、`rehab-en`、`generic-zh`、`generic-en`。

3. 建好的文件夹长这样：

   ```
   videos/            课程视频放这里
   transcripts/       转写产物
   frames/            候选画面和览图
   notes/             成稿；notes/attachments/ 放贴进笔记的图
   vocab.txt          这门课的术语表，转写前喂给 Whisper
   terms.tsv          已知的听错写法 → 正确写法
   transcribe-course.json   配置
   ```

4. 两个文件值得改一下：
   - `vocab.txt`：一行一组术语，逗号分隔。预设里放了一套康复术语，按课程增删。只有最后约 224 个 token 起作用，所以保持精简，重要的放最后。
   - `terms.tsv`：`错写<Tab>正确`，一行一对。转多了发现固定错法就往里加，以后自动替换并记进笔记的 frontmatter。

---

## 六、日常用法

1. 把视频放进 `videos` 文件夹。
2. Claude Code 里输入 `/transcribe-course videos/文件名.mp4`；WorkBuddy 里对它说「用 transcribe-course 把 videos/文件名.mp4 转成笔记」。
3. 中间它会问你两类问题：
   - 视频该叫什么名（课号和标题拿不准时）。
   - 最后剩下的几个听不清的词。它会先用画面里的烧录字幕核对，字幕也定不了的才问你。
4. 成稿在 `notes` 文件夹，图在 `notes/attachments`。一节 20 分钟的课大概 15 到 30 分钟跑完。
5. 一节课开一个新对话，最省额度也最稳。

---

## 七、三个提醒

1. 笔记默认是 Obsidian 格式（图片用 `![[ ]]` 引用，小节标题末尾藏着时间范围）。不用 Obsidian 的话，把 `transcribe-course.json` 里的 `"flavor"` 改成 `"markdown"`。
2. 成稿留在 `notes/`，不会自动搬进你的知识库。搬、改名、加链接是你自己的一步，这是故意的。
3. 出问题先让它读技能文件夹里的 `references/troubleshooting.md`，常见的坑都写在里面了：显卡库缺失、转写陷入重复、AV1 视频抽帧慢、覆盖率不够怎么补。
