"""数据库备份与恢复工具"""

import os
import shutil
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from loguru import logger


class DatabaseBackupManager:
    """数据库备份管理器"""

    def __init__(self, db_path: str, backup_dir: str = "data/backup"):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, compress: bool = True, tag: str = None) -> str:
        """创建数据库备份

        Args:
            compress: 是否压缩备份
            tag: 备份标签，可选

        Returns:
            备份文件路径
        """
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag_str = f"_{tag}" if tag else ""
        backup_filename = f"quant_backup_{timestamp}{tag_str}.duckdb"

        if compress:
            backup_filename += ".gz"

        backup_path = self.backup_dir / backup_filename

        # 复制并压缩
        if compress:
            with open(self.db_path, "rb") as f_in:
                with gzip.open(backup_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(self.db_path, backup_path)

        logger.info(f"数据库备份完成: {backup_path} ({self._get_file_size(backup_path):,.2f} MB)")
        return str(backup_path)

    def restore_backup(self, backup_path: str, create_snapshot: bool = True) -> bool:
        """从备份恢复数据库

        Args:
            backup_path: 备份文件路径
            create_snapshot: 恢复前是否创建当前数据库快照

        Returns:
            是否恢复成功
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        # 恢复前先备份当前数据库
        if create_snapshot and self.db_path.exists():
            try:
                snapshot_path = self.create_backup(compress=True, tag="snapshot_before_restore")
                logger.info(f"恢复前已创建快照: {snapshot_path}")
            except Exception as e:
                logger.warning(f"创建快照失败: {e}")

        # 解压并恢复
        is_compressed = backup_path.suffix == ".gz"

        try:
            if is_compressed:
                temp_file = self.backup_dir / "temp_restore.duckdb"
                with gzip.open(backup_path, "rb") as f_in:
                    with open(temp_file, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                shutil.move(temp_file, self.db_path)
            else:
                shutil.copy2(backup_path, self.db_path)

            logger.info(f"数据库恢复成功: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"数据库恢复失败: {e}")
            return False

    def list_backups(self, limit: int = 20) -> List[dict]:
        """列出所有备份文件

        Args:
            limit: 最多显示数量

        Returns:
            备份文件信息列表
        """
        backups = []

        for file in self.backup_dir.glob("quant_backup_*.duckdb*"):
            stat = file.stat()
            create_time = datetime.fromtimestamp(stat.st_mtime)
            size_mb = stat.st_size / (1024 * 1024)

            backups.append({
                "filename": file.name,
                "path": str(file),
                "size_mb": round(size_mb, 2),
                "created_at": create_time,
                "is_compressed": file.suffix == ".gz",
                "tag": self._extract_tag(file.name),
            })

        # 按创建时间倒序
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups[:limit]

    def clean_old_backups(self, keep_days: int = 30, keep_min_count: int = 5) -> int:
        """清理旧备份文件

        Args:
            keep_days: 保留多少天内的备份
            keep_min_count: 至少保留的备份数量

        Returns:
            删除的备份数量
        """
        backups = self.list_backups(limit=1000)
        cutoff_date = datetime.now() - timedelta(days=keep_days)

        # 标记需要删除的备份
        to_delete = []
        for i, backup in enumerate(backups):
            # 保留最近的N个
            if i < keep_min_count:
                continue
            # 删除超过保留天数的
            if backup["created_at"] < cutoff_date:
                to_delete.append(backup)

        # 执行删除
        deleted_count = 0
        for backup in to_delete:
            try:
                Path(backup["path"]).unlink()
                deleted_count += 1
                logger.debug(f"已删除旧备份: {backup['filename']}")
            except Exception as e:
                logger.error(f"删除备份失败 {backup['filename']}: {e}")

        if deleted_count > 0:
            logger.info(f"已清理 {deleted_count} 个旧备份文件")

        return deleted_count

    def get_latest_backup(self) -> Optional[dict]:
        """获取最新的备份文件"""
        backups = self.list_backups(limit=1)
        return backups[0] if backups else None

    def get_backup_info(self, backup_path: str) -> dict:
        """获取备份文件信息"""
        file = Path(backup_path)
        if not file.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        stat = file.stat()
        return {
            "filename": file.name,
            "path": str(file),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime),
            "is_compressed": file.suffix == ".gz",
        }

    def _extract_tag(self, filename: str) -> str:
        """从文件名提取标签"""
        # quant_backup_20260610_153045_tag.duckdb.gz
        parts = filename.replace(".gz", "").replace(".duckdb", "").split("_")
        if len(parts) >= 4:
            return "_".join(parts[3:])
        return ""

    def _get_file_size(self, path: Path) -> float:
        """获取文件大小（MB）"""
        return path.stat().st_size / (1024 * 1024)


def backup_scheduler_job(db_path: str, backup_dir: str = "data/backup") -> dict:
    """调度器任务：每日自动备份数据库

    可以直接在scheduler的任务中调用
    """
    backup_manager = DatabaseBackupManager(db_path, backup_dir)

    try:
        # 创建备份
        backup_path = backup_manager.create_backup(compress=True, tag="daily")

        # 清理旧备份
        deleted = backup_manager.clean_old_backups(keep_days=30, keep_min_count=7)

        # 获取最新备份信息
        latest = backup_manager.get_latest_backup()

        result = {
            "success": True,
            "backup_path": backup_path,
            "size_mb": latest["size_mb"] if latest else 0,
            "old_backups_deleted": deleted,
            "total_backups": len(backup_manager.list_backups()),
        }

        logger.info(f"自动备份任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"自动备份任务失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# CLI命令行支持
def main():
    import sys

    command = sys.argv[1] if len(sys.argv) > 1 else "list"
    db_path = sys.argv[2] if len(sys.argv) > 2 else "data/db/quant.duckdb"
    backup_dir = "data/backup"

    manager = DatabaseBackupManager(db_path, backup_dir)

    if command == "backup":
        print("创建数据库备份...")
        path = manager.create_backup(compress=True)
        info = manager.get_backup_info(path)
        print(f"✅ 备份完成: {info['filename']} ({info['size_mb']:.2f} MB)")

    elif command == "restore":
        backup_path = sys.argv[3] if len(sys.argv) > 3 else None
        if not backup_path:
            latest = manager.get_latest_backup()
            if latest:
                backup_path = latest["path"]
                print(f"使用最新备份: {latest['filename']}")
            else:
                print("❌ 没有找到备份文件")
                return

        print(f"恢复备份: {backup_path}...")
        if manager.restore_backup(backup_path):
            print("✅ 数据库恢复成功")
        else:
            print("❌ 数据库恢复失败")

    elif command == "list":
        backups = manager.list_backups()
        if not backups:
            print("没有找到备份文件")
            return

        print(f"\n{'='*80}")
        print(f"{'文件名':<40} {'大小(MB)':<10} {'创建时间':<20} {'标签':<10}")
        print(f"{'-'*80}")
        for b in backups:
            tag = b['tag'] or "-"
            print(f"{b['filename']:<40} {b['size_mb']:<10.2f} {b['created_at'].strftime('%Y-%m-%d %H:%M:%S'):<20} {tag:<10}")
        print(f"{'='*80}")
        print(f"总计: {len(backups)} 个备份文件\n")

    elif command == "clean":
        keep_days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        print(f"清理 {keep_days} 天前的旧备份（至少保留5个）...")
        deleted = manager.clean_old_backups(keep_days=keep_days, keep_min_count=5)
        print(f"✅ 已删除 {deleted} 个旧备份文件")

    else:
        print("""用法: python -m utils.db_backup [命令] [参数]

命令:
  backup           创建数据库备份
  restore [路径]   恢复备份（不指定路径使用最新）
  list             列出所有备份
  clean [天数]     清理旧备份（默认30天）
""")


if __name__ == "__main__":
    main()
