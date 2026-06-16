# 我把 Codex 接进了 Blender：3D 创作开始像“对软件发指令”

封面图建议：`docs/cover_5x2.png`  
封面比例：5:2，当前文件尺寸 `2000 x 800`  
项目链接：https://github.com/studyself/codex-blender-mcp-demo  
配图/视频建议：`component001_semantic_assembly_animation.gif`、`codex_blender_mcp_case_animation.gif`

这几天我在做一个 Codex + Blender 的本机实验。

我想验证的不是“一句话生成一个孤立 3D 模型”，而是另一件更接近真实工作流的事：

AI 能不能进入 Blender 这种专业创作软件，像一个会写脚本、会检查场景、会反复修改的技术美术助理一样工作？

这次我做了两个 demo。

第一个 demo 是自动搭场景：Codex 通过 Blender MCP 在后台生成一个技术展示场景，包含模型、材质、灯光、相机、标注和 keyframe 动画。

第二个 demo 是修改现有资产：基于 `nidorx/matcaps` 项目里的女性科幻半身雕像，Codex 先分析模型结构，再把最大的连续主体 `component_001` 二次切成 12 个语义模块，最后做拆解和重新组装的动画。

我把项目开源到了 GitHub：

https://github.com/studyself/codex-blender-mcp-demo

这个链接放进文章或页面里时，可以作为项目引用卡片使用。项目 README 第一屏也放了 5:2 封面图，方便读者点进去后立刻看到这次 Codex + Blender 的核心视觉效果。

先说控制链路。

我本机环境是 Windows + Blender 5.1.2。控制 Blender 用的是 `hassledzebra/codex_blender_mcp`，它提供了一个面向 Codex 的 Blender MCP server。这个 server 有两种典型用法：

第一种是 addon 模式：在 Blender UI 里启用插件，Codex 可以实时控制当前打开的场景。

第二种是 subprocess 模式：Codex 每次通过 MCP 调起 Blender 后台进程，执行一段 Blender Python，保存 `.blend`，再渲染结果。

我这次先用 subprocess 模式。它没有实时 UI 那么戏剧化，但特别适合复现和写文章：命令、脚本、输出文件、渲染结果都能留下来。

最小闭环是这样的：

Codex 接收创作目标  
生成 Blender Python  
MCP server 调起 Blender  
Blender 在后台执行脚本  
保存 `.blend`  
渲染 PNG / GIF  
Codex 再读回结果继续修改

第一个 demo 验证的是“自动搭场景”。

我让 Codex 生成一个“Codex -> MCP -> Blender”的 3D 创作工作台场景：左侧是 Prompt 面板，中间是 MCP 控制塔，右侧是 sci-fi rover，地面上有流程标记和网格。这个场景不是我手工在 Blender 里搭的，而是 Codex 把 Blender Python 送进去生成的。

这次实测结果：

Blender 版本：5.1.2  
控制方式：`BLENDER_MCP_MODE=subprocess`  
主要工具：`blender_exec_python`、`blender_scene_info`  
生成对象数：97  
材质数：14  
输出：`.blend` + 1920 x 1080 PNG + GIF 预览  
动画：写入 1-120 帧 keyframe

这个 demo 证明了一件事：Codex + Blender 不是只能“生成模型”，它可以自动搭一个完整场景系统。

它能创建几何体。  
能分配材质。  
能布灯。  
能设置相机。  
能添加 3D 标注。  
能保存可编辑的 `.blend`。  
能渲染图片和动画预览。  
还能读回场景对象信息，检查生成结果。

这已经很像一个初级技术美术助理了。

然后我做了第二个 demo：雕像拆解。

这个 demo 基于 `nidorx/matcaps`。这个项目本来是一个 MatCap 材质库，仓库里有一套 Blender 预览场景，里面包含一个女性科幻半身雕像。

我一开始想直接把这个雕像“拆成零件”。Codex 先用 Blender 分析网格，发现 `PreviewSolideFemaleSCIFIbust` 里面确实有 83 个 loose mesh components。于是第一步先导出了 83 张独立组件图。

但这里出现了一个很有意思的问题：

`component_001` 不是一个小零件，而是整个上半身雕像的主体。它本身是连续网格，里面包括头部、脸部、颈部、胸像和外壳纹理。也就是说，原始模型的 83 个 loose components 并不等于“语义上有意义的 83 个零件”。

这正是 AI 进入创作软件以后会遇到的真实问题：模型拓扑结构和人类理解的“部件”不是一回事。

所以我让 Codex 继续做第二层处理：针对 `component_001` 做语义拆分。

Codex 先分析曲率和锐边，发现仅靠硬边阈值切不开主体。最大块仍然吞掉了 22 万多个面，说明这些科幻面板纹理在拓扑上基本还是一张连续表面。

于是方案从“原始 loose parts 拆解”变成了“连续网格的语义切割”：

cranial shell  
face mask  
jaw + front neck  
rear head plate  
temple / ear module  
neck spine  
upper chest shell  
front bust pod  
side rib panel  
rear torso shell  
lower base block  
connector transition

最终，Codex 把 `component_001` 切成 12 个可动画模块，并做了一个 90 帧、18 fps 的拆解和回装动画。

这个动画里没有多余文字、坐标轴或 UI 矩形，只保留雕像本体和拆出来的零部件。它更适合放进长文和短视频里展示。

这件事比“生成一个好看的雕像”更有意思。

因为它展示的是第二类能力：Codex 修改现有 `.blend` / 现有资产。

它不是从零生成模型，而是：

打开已有 Blender 场景  
定位目标对象  
分析 loose components  
判断最大主体仍是连续网格  
尝试曲率切分  
发现拓扑切不开  
改用语义切割  
生成 12 个新模块  
给模块分配 MatCap 材质  
写入 keyframe 动画  
输出 `.blend`、hero image、GIF 和 JSON 摘要

这就很接近真实生产中的“资产处理”工作了。

在 3D 流程里，很多工作不是凭空创造，而是整理、拆分、命名、修复、重组、加材质、做展示动画。以前这些事需要会 Blender API 的人写脚本。现在 Codex 可以把自然语言目标翻译成脚本操作，再通过 Blender 执行出来。

我觉得 Codex + Blender 至少会出现三类工作流。

第一类是自动搭场景。

比如给 Codex 一段描述，让它生成基础模型、灯光、相机、材质、标注，用来做概念图、技术说明图或交互原型。前面那个 MCP 工作台场景就属于这一类。

第二类是修改现有 `.blend`。

比如检查命名、找高面数对象、解释几何节点、批量修复材质、拆分模型、生成拆解动画、给复杂节点树加注释。这类任务不一定性感，但非常接近真实生产力。雕像拆解 demo 就属于这一类。

第三类是把 CAD / 机器人 / 打印工作流接进来。

前面可以用 text-to-CAD 生成 STEP / STL / GLB，后面再进 Blender 做视觉表达、动画和渲染。这样 Codex 不只是做“艺术模型”，而是可以贯穿硬件、展示和制造链路。

当然，这条路线也有边界。

第一，MCP 控制 Blender 的本质是执行代码。LLM 生成的代码会在 Blender 里运行，最好放在干净项目、虚拟机或没有敏感资料的机器上做。

第二，subprocess 模式适合自动化和复现，但不是实时交互。想要“我在 Blender 视窗里看着 Codex 一步步改场景”，还是要走 addon 模式。

第三，AI 能很快搭出结构，但审美、物理可信度、模型拓扑、可动画性，仍然需要人检查。尤其是刚体、软体、复杂几何节点、拆分现有资产这类任务，不能只看它“跑起来了”，还要看它是不是对。

这次雕像拆解 demo 就是一个例子。

一开始 83 个 loose components 看起来像是“天然可拆解”，但真正检查后发现，最大的 component 还是整个主体。只有继续分析和迭代，才能得到更有表达价值的 12 个语义模块。

我的初步判断：

Codex + Blender 的最大价值，不是替代 3D 艺术家，而是把大量脚本化、规则化、可迭代的操作变成对话式创作。

你描述目标。  
Codex 写操作。  
Blender 执行。  
场景被保存和渲染。  
Codex 读回结果。  
人判断效果。  
Codex 再修改。

这才是一个真正的创作闭环。

如果再往前走一步，我会继续试 addon 实时模式：打开 Blender UI，启动插件，让 Codex 直接改当前视窗里的场景。那时它就不只是“后台生成”，而更像一个坐在 Blender 旁边的技术美术同事。

这条路很值得继续追。

参考：

https://github.com/studyself/codex-blender-mcp-demo  
https://github.com/hassledzebra/codex_blender_mcp  
https://github.com/nidorx/matcaps  
https://www.blender.org/lab/mcp-server/  
https://github.com/earthtojake/text-to-cad
