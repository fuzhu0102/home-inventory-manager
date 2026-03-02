---
name: home-inventory-manager
description: 维护、查询本地家庭物品库存。强制通过 manage_inventory.py 脚本进行写操作与自动备份轮转。
---

# Home Inventory Management SOP

## 1. 触发时机 (Trigger Conditions)
- 用户提出录入库存、添加/消耗物品，或提及特定位置的物品状态时。
- 用户提出查询库存、检查过期情况时。
- 用户显式要求删除某项库存记录时。

## 2. 行为准则 (Expected Behaviors)

### A. 录入与修改模式 (Recording & Modifying)
1. **位置与分类确认**：
   - 提取目标 `[LOCATION]`（如：一楼冰箱、卧室床头柜）。
   - 目标路径：`/workspace/家庭库存管理/[LOCATION]库存.md`
   - 提取或询问具体大类（如：冷藏区、冷冻区）。若用户未指定，必须简短询问。
2. **工具调用**：
   - **绝对禁止**使用通用文件写入工具直接覆写文件。
   - **必须调用** `scripts/manage_inventory.py` 执行添加、扣减或分类创建操作。
   - 脚本会自动处理以下后台逻辑，Agent 无须干预：
     - 若目录或文件不存在，自动创建。
     - 每次修改前，自动生成备份文件：`/workspace/家庭库存管理/[LOCATION]库存yymmddhhmmss.md`
     - 自动维护备份数量，同一位置仅保留 1 个最新文件和 3 个最新备份。
3. **数据格式规范**：
   - 表格列固定为：`| 物品 | 数量 | 有效期 | 备注 |`。
   - `数量` 列包含数值与单位（如：`2kg`，`1盒`），不作拆分。
   - `有效期` 严格使用 `YYYY-MM-DD` 格式。

### B. 删除模式 (Deleting)
- **严格限制**：除非用户显式要求删除某一条目，Agent 在任何情况下不得主动删除文件内的记录。
- 执行删除时，同样必须通过调用 `scripts/manage_inventory.py` 传入删除指令，由脚本执行安全移除及备份。

### C. 查询模式 (Querying)
1. **读取数据**：直接读取 `/workspace/家庭库存管理/[LOCATION]库存.md` 的当前内容。
2. **分析与简报生成**：
   - 输出极简的库存现状清单，按大类归纳。
   - 比对当前系统日期（YYYY-MM-DD）与表格中的 `有效期`。
   - **过期/临期提醒**：仅在简报末尾用一两句话指出已过期或7天内临期的物品名称及日期。保持绝对简短，只输出必要信息，不提供多余的建议或主观评论。

## 3. 工具接口定义参考 (Tool Interface Reference)
- 工具名称：`manage_inventory_script`
- 执行方式：`python scripts/manage_inventory.py [ACTION] [LOCATION] [CATEGORY] [ITEM_DATA]`
- Action 包含：`add` (添加), `update` (更新数量), `delete` (删除)

**工具调用参数示例 (Tool Parameter Specification)：**
```json
{
  "action": "add",
  "location": "一楼冰箱",
  "category": "冷冻区",
  "item_data": {
    "物品": "牛排",
    "数量": "2kg",
    "有效期": "2026-08-15",
    "备注": "分装保存"
  }
}