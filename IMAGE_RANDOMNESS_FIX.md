# 图片随机性修复说明

## 问题描述
剪映草稿生成时，图片选择不够随机，每次生成的草稿都使用相同的图片顺序。

## 原因分析
在 `generateDraftService.py` 中，默认使用了固定的随机种子 `42`，导致每次运行都产生相同的"随机"结果。

```python
# 修复前
random_seed: Optional[int] = 42  # 固定种子
```

## 解决方案

### 1. 修改默认种子为 None
```python
# 修复后
random_seed: Optional[int] = None  # 不设置默认种子
```

### 2. 增强随机性
当不指定种子时，使用基于当前时间的随机种子：

```python
if random_seed is not None:
    random.seed(random_seed)
    print(f"使用固定随机种子: {random_seed}")
else:
    # 使用当前时间作为随机种子，确保每次运行都不同
    import time
    current_seed = int(time.time() * 1000) % 2147483647
    random.seed(current_seed)
    print(f"使用随机种子: {current_seed} (基于当前时间)")
```

## 使用方法

### 1. 完全随机（推荐）
不指定 `--seed` 参数，每次运行都会产生不同的图片组合：

```bash
python generateDraftService.py --cid creator_id --vid video_id
```

### 2. 可复现结果
需要复现相同结果时，指定种子值：

```bash
python generateDraftService.py --cid creator_id --vid video_id --seed 12345
```

## 测试验证

运行测试脚本验证随机性：

```bash
python test_image_randomness.py
```

测试结果显示：
- ✅ 不设置种子时，每次结果都不同（85-100% 差异）
- ✅ 设置相同种子时，结果完全相同（用于复现）
- ✅ 基于时间的种子确保了真正的随机性

## 影响范围

此修复影响以下功能：
1. 图片选择顺序 - 现在每次都会随机打乱
2. 转场效果选择 - 每次随机选择不同转场
3. 特效选择 - 随机应用不同特效

## 注意事项

1. **默认行为改变**：现在默认是完全随机，不再是固定顺序
2. **向后兼容**：仍可通过 `--seed` 参数实现可复现的结果
3. **性能影响**：随机性不会影响生成速度

## 修改的文件

- `draft_gen/generateDraftService.py`
  - 第907行：默认种子从 `42` 改为 `None`
  - 第980行：命令行参数默认值从 `42` 改为 `None`
  - 第280-288行：添加基于时间的随机种子生成

## 总结

通过移除默认的固定种子并使用基于时间的随机初始化，成功实现了图片选择的完全随机性，让每次生成的视频都有不同的视觉体验。