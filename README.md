```text
          .-----------------------------------------------.
       .-'                                                 '-.
      /       ____    _    _   _  ___                        \
     |       |  _ \  / \  | \ | |/ _ \                        |
     |       | |_) |/ _ \ |  \| | | | |                       |
     |       |  __// ___ \| |\  | |_| |                       |
     |       |_|  /_/   \_\_| \_|\___/                        |
      \                                                     /
       '-.       GEOMETRY-GUIDED  /  360 x 180           .-'
          '-------------------[ + ]---------------------'
                      ONE IMAGE. ALL AROUND.
```

# Geometry-Guided Panorama

**把一张场景图扩展成可以环视的 360° 全景，尽量保留原图的样子。**

适用于室内、建筑、街道、山林等场景，也可以从文字开始创作，或检查已有全景中的变形。输出为 **2:1 的全景 PNG**，可以放入支持等距柱状投影的全景查看器。

这是给 AI agent 使用的 skill，需要支持图像生成和本地脚本执行的环境。

## 1. 安装到项目

把下面这句话发给你的 agent：

```text
请把 https://github.com/Jingquank/geometry-guided-panorama
安装到当前项目的 .agents/skills/geometry-guided-panorama 目录。
保留完整仓库中的 skill 文件和配套脚本；如果已有安装，先检查差异再更新。
```

环境需要 Python 3、NumPy、Pillow，以及支持 C++17 的编译器。图像生成由宿主环境提供，这个仓库不包含图像模型。让 agent 在开始前检查这些条件即可。

## 2. 上传图片，说明你想保留什么

在项目对话里选择 `geometry-guided-panorama`，附上参考图，再描述需求。例如：

```text
使用 $geometry-guided-panorama，把这张参考图扩展成 360° 全景。
保留原有结构、材质和光线，保守补全看不到的区域。
完成全景验收后，交付一张 2:1 PNG。
```

不用自己写复杂的投影参数。说明**哪些东西必须保留、哪些地方可以改变**就好；没有要求改变的部分，应以原图为准。

## 3. 实际生成示例：Before / After

以下是本项目实际使用的参考图与生成的全景 PNG。点击图片可以查看完整文件。它们来自此前的生成过程，不代表全部已通过最新版本的验收或下游 3D 重建。

### Example 01 — 粉色酒店大堂

粉色墙面、拱窗与原有棋盘地面的全景扩展。

| Before · 原图 | After · 360° 全景 |
| --- | --- |
| [![粉色酒店大堂：原始参考图](assets/examples/pink-lobby-before.png)](assets/examples/pink-lobby-before.png) | [![粉色酒店大堂：生成的 2:1 全景图](assets/examples/pink-lobby-after.png)](assets/examples/pink-lobby-after.png) |

[查看完整全景 PNG](assets/examples/pink-lobby-after.png)

### Example 02 — 阳光厨房

白色柜体、橡木岛台与木板地面的全景扩展。此版本在 PINOC 重建中仍出现岛台和光带弯曲，是后续迭代的案例。

| Before · 原图 | After · 360° 全景 |
| --- | --- |
| [![阳光厨房：原始参考图](assets/examples/oak-kitchen-before.png)](assets/examples/oak-kitchen-before.png) | [![阳光厨房：生成的 2:1 全景图](assets/examples/oak-kitchen-after.png)](assets/examples/oak-kitchen-after.png) |

[查看完整全景 PNG](assets/examples/oak-kitchen-after.png)

### Example 03 — 乡村面包房

木梁、拱门与面包陈列的全景扩展。此版本仍有原图小地垫缺失、部分石板尺寸变化。

| Before · 原图 | After · 360° 全景 |
| --- | --- |
| [![乡村面包房：原始参考图](assets/examples/bakery-before.png)](assets/examples/bakery-before.png) | [![乡村面包房：生成的 2:1 全景图](assets/examples/bakery-after.png)](assets/examples/bakery-after.png) |

[查看完整全景 PNG](assets/examples/bakery-after.png)

全景图在这里以平面展开图显示；请用支持 2:1 等距柱状投影的查看器体验环视效果。

## 它会检查什么？

agent 会先辨认原图中的结构和材质，再生成全景，并检查 **18 个基础视角＋针对重要区域补充的视角**。

检查包括物体形状、遮挡与接触、光影、纹理、接缝和上下方向的完整性。规则取决于原图：木板检查排列，山林检查自然形态，没有方格的地面就不应凭空加上方格。

如果结果有问题，附上**实际使用的全景 PNG、问题截图和所在方向**。如果经过了 3D 重建，也请注明工具和 workflow，便于区分输入图与重建阶段的问题。

**全景验收通过，不等于 3D 重建通过。** 单张图看不到的区域属于合理补全；本 skill 不保证恢复真实三维空间，也不保证任意重建工具中的结果。

---

想了解具体流程？阅读 [完整 skill](SKILL.md) 和 [通用场景验收机制](references/general-scene-qa.md)。
