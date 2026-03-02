#!/usr/bin/env python3
import sys
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

# 根据运行时环境自动选择基础路径
import os
# 使用环境变量动态获取用户目录
DEFAULT_WORKSPACE = Path.home() / ".openclaw" / "workspace"
WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE")) if os.environ.get("OPENCLAW_WORKSPACE") else DEFAULT_WORKSPACE
BASE_DIR = WORKSPACE / "家庭库存管理"


def sanitize_filename(name: str) -> str:
    """
    将传入的路径/名称规范化为安全的单段文件名，替换平台保留或危险字符。
    """
    if not isinstance(name, str):
        name = str(name)
    # 除去路径分隔符以及常见文件名非法字符
    illegal = r"[\\/:\"\*\?<>\|]+"
    safe = re.sub(illegal, "_", name)
    # 移除控制字符和多余空白
    safe = re.sub(r"[\x00-\x1f]+", "", safe).strip()
    if not safe:
        safe = "位置"
    return safe

def rotate_backups(target_file: Path, location_name: str):
    """
    执行备份轮转：生成新备份，并确保同一位置保留主文件 + 最新的 3 个备份文件。
    """
    if not target_file.exists():
        return

    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    backup_name = f"{location_name}库存{timestamp}.md"
    backup_path = target_file.parent / backup_name

    shutil.copy2(target_file, backup_path)

    # 使用正则在目录中匹配形如 "{location_name}库存YYMMDDhhmmss.md" 的备份文件
    escaped = re.escape(location_name)
    regex = re.compile(rf"^{escaped}库存(\d{{12}})\.md$")
    backups = []
    for p in target_file.parent.iterdir():
        m = regex.match(p.name)
        if m:
            try:
                ts = datetime.strptime(m.group(1), "%y%m%d%H%M%S")
            except Exception:
                continue
            backups.append((p, ts))

    backups.sort(key=lambda x: x[1], reverse=True)
    # 保留最新3个备份
    for old_backup, _ in backups[3:]:
        try:
            old_backup.unlink()
        except OSError as e:
            print(json.dumps({"status": "warning", "message": f"无法删除备份文件: {str(e)}"}))

def parse_markdown_inventory(content: str) -> dict:
    """
    解析 Markdown 内容为结构化字典：{ "分类名称": [ {"物品":"...", "数量":"...", ...}, ... ] }
    """
    inventory = {}
    current_category = None
    lines = content.splitlines()
    
    headers = []
    
    for line in lines:
        category_match = re.match(r'^##\s+(.+)$', line.strip())
        if category_match:
            current_category = category_match.group(1)
            inventory[current_category] = []
            continue
            
        if current_category and line.strip().startswith('|'):
            # 忽略表头和分隔线
            if '物品' in line and '数量' in line:
                headers = [col.strip() for col in line.split('|')[1:-1]]
                continue
            if '---' in line:
                continue
                
            cols = [col.strip() for col in line.split('|')[1:-1]]
            if len(cols) == 4 and headers:
                item_data = dict(zip(headers, cols))
                inventory[current_category].append(item_data)

    return inventory

def build_markdown_inventory(inventory: dict) -> str:
    """
    将结构化字典重新组装为 Markdown 文本。
    """
    lines = ["# 库存盘点\n"]
    for category, items in inventory.items():
        lines.append(f"## {category}")
        lines.append("| 物品 | 数量 | 有效期 | 备注 |")
        lines.append("|---|---|---|---|")
        for item in items:
            lines.append(f"| {item.get('物品', '')} | {item.get('数量', '')} | {item.get('有效期', '')} | {item.get('备注', '')} |")
        lines.append("\n")
    return "\n".join(lines)

def process_inventory(action: str, location: str, category: str, item_data: dict):
    # 规范化 location 为安全的单段文件名以避免目录穿越或平台非法字符
    safe_location = sanitize_filename(location)
    target_file = BASE_DIR / f"{safe_location}库存.md"

    # 初始化目录
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # 备份逻辑（使用规范化的名称）
    rotate_backups(target_file, safe_location)

    # 读取现有数据
    content = target_file.read_text(encoding="utf-8") if target_file.exists() else ""
    inventory = parse_markdown_inventory(content)
    
    if category not in inventory:
        inventory[category] = []

    items = inventory[category]
    target_item_name = item_data.get("物品")
    
    if not target_item_name:
        raise ValueError("物品名称不能为空")

    # 执行动作
    if action == "add":
        # 检查是否已存在，存在则更新，不存在则追加
        existing_item = next((i for i in items if i["物品"] == target_item_name), None)
        if existing_item:
            existing_item.update(item_data)
        else:
            items.append(item_data)
            
    elif action == "update":
        found = False
        for item in items:
            if item["物品"] == target_item_name:
                item["数量"] = item_data.get("数量", item["数量"])
                item["有效期"] = item_data.get("有效期", item["有效期"])
                item["备注"] = item_data.get("备注", item["备注"])
                found = True
                break
        if not found:
            raise ValueError(f"物品 '{target_item_name}' 不存在")
                
    elif action == "delete":
        initial_count = len(inventory[category])
        inventory[category] = [i for i in items if i["物品"] != target_item_name]
        if len(inventory[category]) == initial_count:
            raise ValueError(f"物品 '{target_item_name}' 不存在")
    else:
        raise ValueError(f"未知的操作类型: {action}")

    # 写入文件
    new_content = build_markdown_inventory(inventory)
    target_file.write_text(new_content, encoding="utf-8")
    print(json.dumps({"status": "success", "action": action, "file": str(target_file)}))

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(json.dumps({"status": "error", "message": "Missing arguments"}))
        sys.exit(1)

    action = sys.argv[1]
    location = sys.argv[2]
    category = sys.argv[3]
    try:
        item_data = json.loads(sys.argv[4])
    except json.JSONDecodeError:
        print(json.dumps({"status": "error", "message": "Invalid JSON for item_data"}))
        sys.exit(1)

    try:
        process_inventory(action, location, category, item_data)
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)