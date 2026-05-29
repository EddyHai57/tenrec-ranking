# CLAUDE.md

本项目规则以 `AGENTS.md` 为**单一真相源（single source of truth）**。本文件不重复内容，只把 Claude 导向 `AGENTS.md`，避免两份文件随项目演进而不同步。

请完整阅读以下文件后再开始工作：

1. `AGENTS.md` —— 项目规则、工作边界、Git/服务器纪律、commit/push 流程。
2. `STATE.md` —— 项目当前状态指针（当前阶段、最近完成、下一步、活跃约束）。

> **【硬性读取确认协议 - 不可跳过】**
>
> 每次进入本项目（新对话 / 新任务 / 新会话）的**第一条回复**里，**必须**首行打印 `cc喵开始了喵ヾ(*ΦωΦ)ツ`。
>
> **不要在喵前加任何前缀**（"好的"、"明白"、"完成"都不行）。第一行就是这句喵，然后才开始正文。
>
> **【冲突覆盖】AGENTS.md 仍须完整阅读。两者冲突时以本文件为准。当前唯一冲突：读取确认字符串使用 `cc喵开始了喵ヾ(*ΦωΦ)ツ`，不使用 AGENTS.md 中的 `codex喵开始了喵ヾ(*ΦωΦ)ツ`。**
>
> 这是反幻觉检查点。跳过 = 违规，Eddy 会要求你停下重做并复述 AGENTS.md 关键约束。

## 本地 Python / PyTorch 环境

本机专用 PyTorch conda 环境路径：

```text
D:\tool\spyder\envs\pytorch\python.exe
```

torch 版本：2.8.0+cu126，CUDA 可用。

**所有训练、评估、数据处理脚本，必须通过上述路径显式调用 Python，例如：**

```powershell
D:\tool\spyder\envs\pytorch\python.exe src/train.py --config configs/xxx.yaml
```

**禁止：**

- 使用远程沙盒、Anthropic 云端执行环境或任何非本机资源运行训练代码；
- 依赖 `python` / `python3` 等不明确的 shim（base 环境无 torch）；
- 将训练代码上传至任何外部服务再取回结果。

所有训练均在本地 Windows 机器上直接运行，结果写入本地 `outputs/`。
