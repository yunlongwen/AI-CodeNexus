"""
为现有工具添加 identifier 字段

使用方法:
    python scripts/add_tool_identifiers.py
"""
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.services.data_loader import DataLoader
from loguru import logger

# 配置日志
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


def generate_identifier(tool_name: str) -> str:
    """
    生成工具的 identifier
    
    Args:
        tool_name: 工具名称
        
    Returns:
        identifier 字符串
    """
    if not tool_name:
        return ""
    
    # 转换为小写，保留字母、数字、连字符和下划线
    identifier = "".join(c.lower() if c.isalnum() or c in "-_" else "" for c in tool_name)
    return identifier


def add_identifiers_to_tools():
    """为所有工具添加 identifier 字段"""
    tools_dir = project_root / "data" / "tools"
    
    if not tools_dir.exists():
        logger.error(f"工具目录不存在: {tools_dir}")
        return
    
    total_updated = 0
    
    # 遍历所有工具文件
    for tool_file in tools_dir.glob("*.json"):
        if tool_file.name == "featured.json":
            continue  # 跳过 featured.json，因为它是从其他文件汇总的
        
        logger.info(f"处理文件: {tool_file.name}")
        
        # 加载工具
        tools = DataLoader._load_json_file(tool_file)
        
        if not tools:
            logger.warning(f"文件 {tool_file.name} 为空")
            continue
        
        updated_count = 0
        
        # 为每个工具添加 identifier
        for tool in tools:
            if "identifier" not in tool or not tool.get("identifier"):
                tool_name = tool.get("name", "").strip()
                if tool_name:
                    tool["identifier"] = generate_identifier(tool_name)
                    updated_count += 1
                    logger.debug(f"为工具 '{tool_name}' 添加 identifier: {tool['identifier']}")
        
        # 保存文件
        if updated_count > 0:
            if DataLoader._save_json_file(tool_file, tools):
                total_updated += updated_count
                logger.success(f"✅ {tool_file.name}: 更新了 {updated_count} 个工具")
            else:
                logger.error(f"❌ {tool_file.name}: 保存失败")
        else:
            logger.info(f"ℹ️  {tool_file.name}: 所有工具已有 identifier")
    
    logger.info(f"🎉 完成！共更新 {total_updated} 个工具")


if __name__ == "__main__":
    add_identifiers_to_tools()

