# 我把 Codex 接进了 Blender：3D 创作开始像“对软件发指令”

配图建议：`codex_blender_mcp_case.png`

这两天我在看 Codex + Blender 的 3D 内容创作路线。比起“让 AI 直接吐一个 3D 模型”，我更关心另一件事：

AI 能不能真正进入 Blender 这种专业创作软件，像一个会写脚本、会检查场景、会反复修改的协作者一样工作？

今天做了一个本机复现。

环境是 Windows + Blender 5.1.2，控制链路用的是 `hassledzebra/codex_blender_mcp`。它提供了一个面向 Codex 的 Blender MCP server，有两种模式：

第一种是 addon 模式：在 Blender UI 里启用插件，Codex 可以实时控制当前打开的场景。

第二种是 subprocess 模式：Codex 每次通过 MCP 调起 Blender 后台进程，执行一段 Blender Python，保存 `.blend`，再渲染结果。

我这次先选了 subprocess 模式，因为它更适合复现和写文章：不用手动点 UI，命令、输出和文件都能留下证据。

这次的最小闭环是：

Codex 发出创作目标  
MCP server 接收工具调用  
Blender 5.1.2 在后台启动  
执行生成场景的 Python 脚本  
保存 `.blend`  
渲染 PNG  
再用 `blender_scene_info` 读取场景对象信息

最终生成了一个“Codex -> MCP -> Blender”的 3D 创作工作台场景：左侧是 Prompt 面板，中间是 MCP 控制塔，右侧是被生成出来的 sci-fi rover，地面上有流程标记和网格。这个场景不是手工在 Blender 里搭的，而是 Codex 通过 MCP 把 Blender Python 送进去生成的。

这次实测结果：

Blender 版本：5.1.2  
控制方式：`BLENDER_MCP_MODE=subprocess`  
主要工具：`blender_exec_python`、`blender_scene_info`  
生成对象数：97  
材质数：14  
输出：`.blend` + 1920 x 1080 PNG  
场景还写入了 1-120 帧的简单动画 keyframe

这个小案例让我对 Codex + Blender 的理解变了。

以前我们说 AI 3D，经常会想象成“一句话生成一个模型”。但真正进入创作流程以后，价值点不只在模型本身，而在软件操作层：

它可以批量创建对象。  
可以按规则命名、分组、加材质。  
可以设置灯光和相机。  
可以生成动画关键帧。  
可以读回场景信息，检查有没有真的生成。  
可以把过程变成可重复执行的脚本。

这更接近“AI 操作员”或“AI 技术美术助理”，而不是一个孤立的 3D 生成器。

而且这个模式和 Blender 很搭。Blender 本来就有强大的 Python API，很多专业流程其实已经是脚本化的：批量改材质、生成几何、处理资产、跑渲染、做检查。Codex 接进去以后，相当于给这些 API 接了一个自然语言和推理层。

我觉得这里会出现三类工作流。

第一类是自动搭场景。  
比如给 Codex 一段描述，让它生成基础模型、灯光、相机、材质、标注，用来做概念图、技术说明图或交互原型。

第二类是修改现有 `.blend`。  
比如检查命名、找高面数对象、解释几何节点、批量修复材质、给复杂节点树加注释。这类任务不性感，但非常接近真实生产力。

第三类是把 CAD / 机器人 / 打印工作流接进来。  
前面可以用 text-to-CAD 生成 STEP / STL / GLB，后面再进 Blender 做视觉表达、动画和渲染。这样 Codex 不是只做“艺术模型”，而是贯穿硬件、展示和制造链路。

不过也要讲边界。

第一，MCP 控制 Blender 的本质是执行代码。Blender 官方 MCP 页面也提醒过：LLM 生成的代码会在 Blender 里运行，应该放在干净环境、虚拟机或没有敏感资料的机器上做。

第二，subprocess 模式适合自动化和复现，但不是实时交互。想要“我在 Blender 视窗里看着 Codex 一步步改场景”，还是要走 addon 模式。

第三，AI 能很快搭出结构，但审美、物理可信度、模型拓扑、可动画性，仍然需要人检查。尤其是刚体、软体、复杂几何节点这类东西，不能只看它“跑起来了”，还要看它是不是对。

我的初步判断：

Codex + Blender 的最大价值，不是替代 3D 艺术家，而是把大量脚本化、规则化、可迭代的操作变成对话式创作。

你描述目标。  
Codex 写操作。  
Blender 执行。  
场景被保存和渲染。  
Codex 再读回结果继续改。

这就是一个真正的创作闭环。

如果再往前走一步，我会想试 addon 实时模式：打开 Blender UI，启动插件，让 Codex 直接改当前视窗里的场景。那时它就不只是“后台生成”，而更像一个坐在 Blender 旁边的技术美术同事。

这条路很值得继续追。

参考：

https://github.com/hassledzebra/codex_blender_mcp  
https://www.blender.org/lab/mcp-server/  
https://github.com/earthtojake/text-to-cad
