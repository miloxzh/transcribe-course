# transcribe-course

**把课程视频转成可以代替看视频的笔记。**

这是一个 [Claude Code](https://claude.com/claude-code) 的 skill，外加两个子代理和一套小的 Python 工具。给它一节课的视频（幻灯片讲课，或者动作/康复示范），它产出一篇逐字级的 Markdown 笔记，重要画面直接贴进去：

1. **本地转写**：faster-whisper，NVIDIA 显卡上跑 `large-v3`，10–20 倍实时；没显卡走 CPU。
2. **把幻灯片从视频里抠出来**：换页和镜头切换检测 → 候选帧 + 览图 → Claude 看图挑出读者不看会丢信息的那几张。
3. **写稿**：一个子代理按严格的转录规范写：按讲述顺序、不概括、幻灯片上的字抄进正文、改动有记录、拿不准的标出来不猜。
4. **门禁**：模板标题、frontmatter、正文无时间码、贴图都在、**转写里 97% 以上的句子能在笔记里找到**。不过就修，修完再查。
5. **存疑词先用烧录字幕核对**，字幕也定不了的再列给你。

最初是为了把一个 30 节课的形体训练营（幻灯片正课 + 80 多个动作视频）转进 Obsidian 做的，现在改成了通用版：运动康复、物理治疗、瑜伽普拉提教培、教练认证课、大学课程都能用。自带中文和英文两套模板，笔记语言跟着视频走。

[English README →](README.md) ｜ **第一次用先看 [安装与使用说明（中文）](INSTALL.zh-CN.md)**，Claude Code 和 WorkBuddy 都有步骤。

---

## 成稿长什么样

```markdown
---
type: 正课
lesson: 30
title: 最大化肌肥大的训练计划设计 III
source_file: D30_最大化肌肥大的训练计划设计III.mp4
video_length: "26:37"
whisper_model: large-v3
verified: pass
images: 10
term_fixes: "ERM→1RM×26，减轻载期→减载×23，训组分配→训练分配×1（烧录字幕）"
gaps:
  - "25:49 总结口述峰值测试为 85%–90%，19:59 画面写的是 85%–95%，两处均保留"
---

# D30 最大化肌肥大的训练计划设计 III

> 本文全部内容为课程原始转录，未作核查、评价或补充。

## 一句话主旨
介绍线性周期、波动周期、减载期与训练量、强度、动作的周期化调整方法。

## 逐段详述

### 没有周期化会怎样与核心思想 %%00:28–02:15%%
首先为什么要有周期化。没有周期化的训练，到底会发生什么……（每一句，按顺序）

画面《为什么需要周期化》：1. 持续进步——避免平台期；2. 管理疲劳……

![[D30_0215_为何周期.jpg]]
…
```

一节 26 分钟的课 → 约 1.3 万字正文、18 个小节、10 张幻灯片，每处改字都在 `term_fixes` 里，课程前后矛盾的地方在 `gaps` 里。读者拿到课，审核的人拿到痕迹。

## 为什么这么设计

- **转录员，不是分析员。** 模型天生爱"理解后复述"，那样写出来的笔记只有一半长，限定词、例子、数字悄悄丢掉。规范禁止，覆盖率门禁能抓。
- **看覆盖率，不看字数。** 字数指标会诱导扩写。门禁看的是转写里每一段的四字片段（英文是三词片段）能不能在笔记里找到。
- **先有证据再改字。** Whisper 把术语听成同音字是常态。只有幻灯片、烧录字幕或你给的对照表能证实的才改，而且记进 frontmatter；证实不了的保留原词加存疑标记。（有一次按上下文猜的词是错的，字幕上是第三个词——这条教训变成了第 6.5 步。）
- **medium 强度就够了。** 转录是保真任务不是推理任务。同一节 19 分钟的课实测：Sonnet-medium 9.3 万 token、8 分钟、覆盖率 100%；Opus-medium 6.6 万、5 分钟、100%；Sonnet-max 29.6 万 token、41 分钟、97.3%。强度越高越想改写。默认 Sonnet-medium，Opus-medium 兜底。
- **正文不出现时间码。** 读者不需要。时间范围藏在每个小节标题末尾的注释里（Obsidian 用 `%%mm:ss–mm:ss%%`，普通 Markdown 用 `<!-- -->`），门禁和第二遍核对靠它定位。
- **一节课开一个会话。** 最省额度，也绕开超长会话的各种毛病。

## 需要什么

| | |
|---|---|
| Claude Code | 桌面版或命令行版，能开子代理即可 |
| Python | 3.9+，装 `faster-whisper`、`opencv-python`、`numpy`、`Pillow`（`pip install -r requirements.txt`） |
| 显卡 | NVIDIA、显存 ≥ 6 GB（faster-whisper 跑 `large-v3` float16），或 **Apple 芯片的 Mac** 装 `pip install mlx-whisper`（MLX 在 Mac 的 GPU 上跑 large-v3，装了就自动选用）。两者都没有就走 CPU 的 `large-v3-turbo`，约 1 倍实时。 |
| ffmpeg | 可选；AV1/VP9 视频（B 站、YouTube 下载常见）抽帧会快很多 |
| 磁盘 | Whisper 模型 3 GB（第一次用时自动下载）+ 每节课几 MB 的帧 |

## 安装

**装成插件（推荐）：**
```bash
claude plugin marketplace add miloxzh/transcribe-course
claude plugin install transcribe-course@transcribe-course
```
（会话里用 `/plugin marketplace add …` 和 `/plugin install …` 也一样。）

**手动装：** 克隆仓库，把 `skills/transcribe-course/` 复制到 `~/.claude/skills/`，`agents/*.md` 复制到 `~/.claude/agents/`（或项目的 `.claude/` 下），然后重开 Claude Code——子代理只在会话启动时加载。

**其他支持 Agent Skills 格式的工具（WorkBuddy、CodeBuddy、Codex、Cursor 等）：** 把 `skills/transcribe-course/`
整个文件夹复制到那个工具的技能目录（WorkBuddy 是 `~/.workbuddy/skills/`，也可以在它的「上传本地技能」里导入；
CodeBuddy 命令行用 `codebuddy plugin marketplace add miloxzh/transcribe-course` 再
`codebuddy plugin install transcribe-course@transcribe-course`），重启工具，然后用一句话说明要转录哪个视频，
不用斜杠命令。`agents/` 里的子代理在这些工具上是可选的：不能开子代理时，skill 会在主会话里自己写稿，门禁照跑。
`${CLAUDE_SKILL_DIR}` 是 Claude Code 的变量，其他工具上 skill 会按路径自己找到 `scripts/tc.py`。

**Python 包**（装进工具调用 `python` 时用的那个解释器）：
```bash
pip install -r requirements.txt
```
NVIDIA 机器上它会顺带装 `nvidia-cublas-cu12` 和 `nvidia-cudnn-cu12`，faster-whisper 只需要这两个 CUDA 组件，不用装 CUDA 工具包。Apple 芯片的 Mac 上则会装 `mlx-whisper`；Mac 上建议 `brew install ffmpeg`（AV1 视频抽帧用，抽帧硬解参数是 `--hwaccel videotoolbox`）。

国内下载模型慢的话，先设镜像：`HF_ENDPOINT=https://hf-mirror.com`。

## 第一次用

在一个空文件夹里打开 Claude Code，直接说：

> 在这里建一个 transcribe-course 工作区，中文的运动康复课，然后跑一下环境体检。

Claude 会替你跑下面两条命令；自己跑也行（`TC` = `python <skill 路径>/scripts/tc.py`）：
```bash
TC init . --preset rehab-zh --course "肩关节康复"     # 预设：fitness-zh、rehab-zh、rehab-en、generic-zh、generic-en
TC doctor --full                                     # 检查包、显卡、ffmpeg、字体；--full 真跑一次推理
```
`init` 建出来的东西：
```
videos/            课程视频放这里
transcripts/       转写产物（带时间的 .json、.txt、.log）
frames/{stem}/     候选帧、览图、framelist.md、字幕核对图
notes/             成稿；notes/attachments/ 放贴进笔记的图
vocab.txt          这门课的术语，转写前喂给 Whisper——要自己改
terms.tsv          已知听错写法 → 正确写法，门禁时自动替换
transcribe-course.json   语言、模板语言、Obsidian 还是普通 Markdown、模型、设备
```

## 怎么用

把视频放进 `videos/`，在工作区文件夹里打开 Claude Code：

```
/transcribe-course videos/第三课.mp4
```
加 `--careful` 就从一开始用 Opus 写稿。

会发生什么、会问你什么：
1. 转写在后台跑（显卡上 20 分钟的课 1–3 分钟）。
2. Claude 按标题页给视频改成规范名（`D03_课题.mp4`），拿不准会问你。
3. 生成览图；Claude 看图挑帧，写 `frames/{stem}/framelist.md`。
4. 写稿代理产出 `notes/{stem}_draft.md`（5–12 分钟，约 6–15 万 token）。
5. 跑门禁，Claude 按提示修，再查。
6. 存疑词先截烧录字幕核对；字幕也定不了的连上下文列给你。你回一句原词，Claude 改稿并记进 `term_fixes`。

成稿留在 `notes/`。往你的知识库里搬、加链接、加别名是你自己的一步，这是故意的：入库后的笔记会被手工修补，自动同步曾经一次覆盖掉 41 篇改好的笔记。

## 工具箱

skill 跑的每一步都是普通命令行，可以单独用（`python scripts/tc.py <命令> --help`）：

| 命令 | 做什么 |
|---|---|
| `doctor [--full]` | 检查包、显卡、ffmpeg、字体、工作区；`--full` 真跑一次短推理 |
| `init <目录> [--preset …]` | 建工作区、配置、词表、术语表 |
| `transcribe <视频>` | faster-whisper → `transcripts/{stem}.json/.txt/.log`，自带幻觉循环和乱码检查 |
| `frames <视频> [--overview N]` | 换页/切镜检测 → 候选帧、览图、`_candidates.tsv` |
| `grab <视频> <时刻>` | 按秒或 mm:ss 取全分辨率帧 |
| `subs <视频> <时刻…>` | 截取时刻前后的烧录字幕条拼图 |
| `rename <旧名> <新名>` | 视频和所有衍生文件一起改名，绝不覆盖 |
| `attach <stem> <时刻> <描述>` | 按命名规范把帧复制进附件目录，打印嵌入语法 |
| `verify <笔记>` | 模板标题、frontmatter、时间码、贴图、禁词、原文堆砌 |
| `check <转写.json> <笔记>` | verify + 覆盖率 + 随机抽查 → `GATE PASS/FAIL` |
| `strip [--write] <笔记>` | 去掉正文里的时间码 |
| `terms [--write] <笔记>` | 应用 `terms.tsv`，合并进 `term_fixes` |
| `log "<一行>"` | 追加到工作区 `log.md` |

## 改成自己的

| 在哪 | 改什么 |
|---|---|
| `transcribe-course.json` | `language`（Whisper 语言码或 `auto`）、`note_language`（`zh`/`en` 模板）、`flavor`（`obsidian`：`![[x]]` + `%%…%%`；`markdown`：`![](attachments/x)` + `<!-- -->`）、`backend`（`auto`/`faster-whisper`/`mlx`）、`whisper_model`、`cpu_model`、`mlx_model`、`device`、`ffmpeg`、`hwaccel`、`coverage_threshold`、`banned_words`、`declaration_alternatives`、`dirs` |
| `vocab.txt` | 喂给 Whisper 的术语；只有最后约 224 个 token 起作用，保持精简、重要的放最后 |
| `terms.tsv` | `错写<TAB>正确`，盲替换——只放在这门课里不可能有别的意思的词 |
| 工作区 `templates/` | 放一个 frontmatter 里有 `type:` 的 Markdown 文件，`## ` 标题就是这类笔记的合同，`verify` 自动认。可以复制自带模板改，也可以加新类型（`评估`、`案例`……） |
| `references/SPEC.md` | 写稿代理的规则书；笔记要换约定就改它 |

## 仓库结构

```
.claude-plugin/            plugin.json、marketplace.json
agents/                    transcriber.md（Sonnet）、transcriber-careful.md（Opus）
skills/transcribe-course/
  SKILL.md                 Claude 照着跑的操作清单
  scripts/                 tc.py + 每个命令一个模块
  templates/zh、templates/en   lecture.md、technique.md
  references/              SPEC.md、agent-brief.md、frame-picking.md、writer-prompt.md、troubleshooting.md、presets/
examples/                  一节虚构的英文课（转写 + 成稿），用来试门禁
```

转录任何东西之前先试一下门禁：
```bash
python skills/transcribe-course/scripts/tc.py init /tmp/tc-demo --preset generic-en
python skills/transcribe-course/scripts/tc.py check examples/en/L02_shoulder-assessment.json examples/en/L02_shoulder-assessment.md --workspace /tmp/tc-demo
```

## 实测成本（RTX 4080，Claude Code，2026 年 9 月）

| | 26 分钟幻灯片正课 | 3 分钟动作示范 |
|---|---|---|
| 转写（large-v3，显卡） | 159 秒 | 14 秒 |
| 抽帧（seek） | 约 3 分钟 | 6 秒 |
| 写稿（Sonnet，medium） | 11 分钟，14.3 万 token | 3–5 分钟，5–6 万 token |
| 覆盖率 | 99.6% | 100% |

17 分钟的 AV1 示范视频（B 站下载，1080×1920）：顺序抽帧 ffmpeg 软解 2 分 49 秒，`--hwaccel cuda` 58 秒，重跑时复用按秒转储只要 13 秒。

出问题看 [references/troubleshooting.md](skills/transcribe-course/references/troubleshooting.md)（英文）。

## 致谢

流程、规范和踩过的坑：Milo Xu，在转录一个形体训练营的课程时攒下来的。用 Claude Code 搭建。
语音识别：[faster-whisper](https://github.com/SYSTRAN/faster-whisper) / OpenAI Whisper large-v3。

MIT 许可。
