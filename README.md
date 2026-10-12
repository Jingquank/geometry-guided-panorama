# Geometry-Guided Panorama

用于生成、编辑和检查 360° × 180°、2:1 等距柱状投影全景图的 agent skill。完整工作流见 [SKILL.md](SKILL.md)。

## 核心原则

- 保留参考图中的建筑结构、物件、材质、光泽，以及表面图案的存在或缺失。
- 只有原图明确存在、或用户明确要求的规则图案，才采用对应的规则铺设；不凭空添加方格地板、接缝或装饰。
- 建筑场景先建立并检查几何引导，再细化外观；看不到的区域采用保守补全。
- 已有规则图案通过世界坐标渲染或确定性合成保护最终像素。
- 使用 18 个透视重投影视角检查接缝、上下极点、地面透视和参考图一致性。

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
```

自动检查验证文件、数学实现和记录一致性，不能替代实际视觉检查。本 skill 不承诺从单张图片恢复真实三维场景，也不将本地全景检查等同于下游重建验证。
