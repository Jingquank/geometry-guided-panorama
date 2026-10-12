# Geometry-Guided Panorama

用于生成、编辑和检查 360° × 180°、2:1 等距柱状投影全景图的 agent skill。完整工作流见 [SKILL.md](SKILL.md)。

## 核心原则

- 保留参考图中的建筑结构、物件、材质、光泽，以及表面图案的存在或缺失。
- 只有原图明确存在、或用户明确要求的规则图案，才采用对应的规则铺设；不凭空添加方格地板、接缝或装饰。
- 建筑场景先建立并检查几何引导，再细化外观；看不到的区域采用保守补全。
- 已有规则图案通过世界坐标渲染或确定性合成保护最终像素。
- 所有场景必做 18 个基础透视视角检查，再根据原图证据添加重点区域视图。
- 按需检查直边、平面、自然曲面、重复排列、接触遮挡与光影，不预设平地、直墙或网格。
- 十项通用检查与逐目标证据进入发布门槛；全景验收和下游 3D 重建结果分开记录。

## 文件

- `SKILL.md`：主工作流与约束。
- `geometry.md`、`refinement.md`、`qa.md`：几何、外观和检查说明。
- `scripts/`：几何引导渲染器、重投影检查器、合成与发布记录检查工具。
- `examples/`：示例场景与地面参数。
- `references/`：执行约定、维护说明及历史测试记录。
- `agents/openai.yaml`：agent 界面元数据。

脚本依赖 Python 3、NumPy、Pillow；几何引导渲染需要支持 C++17 的编译器。图像生成能力由宿主环境提供。

## 回归检查

```bash
python3 scripts/self_test.py
python3 scripts/floor_self_test.py
python3 scripts/execution_self_test.py
python3 scripts/general_scene_self_test.py
```

自动检查验证文件、数学实现和记录一致性，不能替代实际视觉检查。本 skill 不承诺从单张图片恢复真实三维场景，也不将本地全景检查等同于下游重建验证。

当前验收 schema 为 `3-evidence-led`，容器仍使用 pipeline version 3。新流程需要在场景说明中提供 `inspection_plan`，并在引导图和最终图检查时传入 `--scene-spec`。旧审批不会自动迁移，详见 [通用场景验收](references/general-scene-qa.md)。57 项脚本测试通过不代表跨场景视觉生成或 PINOC 重建已通过。
