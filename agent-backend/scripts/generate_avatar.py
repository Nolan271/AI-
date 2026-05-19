"""生成数字人口播视频并嵌入到 my-video 项目"""

import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.avatar_service import AvatarService
from app.config import settings


def main():
    """根据文档脚本生成数字人口播视频"""
    # 读取已有的解说脚本
    script_path = Path(settings.hyperframes_abs_path) / "docs" / "script.txt"
    if not script_path.exists():
        print(f"❌ 未找到脚本文件: {script_path}")
        return

    script_text = script_path.read_text(encoding="utf-8").strip()

    # 切分脚本：开场 + 结尾
    paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
    if len(paragraphs) < 2:
        print("❌ 脚本内容不足，至少需要开场和结尾两段")
        return

    opening_text = paragraphs[0]     # 开场欢迎词
    closing_text = paragraphs[-1]    # 结尾告别词

    print("=" * 50)
    print("🎬 数字人口播视频生成")
    print("=" * 50)
    print(f"\n📄 开场台词 ({len(opening_text)}字):")
    print(f"   {opening_text[:80]}...")
    print(f"\n📄 结尾台词 ({len(closing_text)}字):")
    print(f"   {closing_text[:80]}...")

    # 初始化 Avatar 服务
    avatar = AvatarService(
        avatar_id="Anna_public_3_20240119",  # 专业女性
        voice_id="2d9d16b7e4d146e89819c80f6ff47753",  # 小北 - 中文女声
    )

    assets_dir = Path(settings.hyperframes_abs_path) / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 生成开场数字人视频
    print(f"\n🔄 生成开场数字人视频...")
    opening_video = avatar.generate_and_download(
        input_text=opening_text,
        output_path=assets_dir / "avatar-opening.mp4",
        title="Opening Greeting",
        video_aspect_ratio="9:16",
    )
    print(f"✅ 开场视频: {opening_video}")

    # 生成结尾数字人视频
    print(f"\n🔄 生成结尾数字人视频...")
    closing_video = avatar.generate_and_download(
        input_text=closing_text,
        output_path=assets_dir / "avatar-closing.mp4",
        title="Closing Message",
        video_aspect_ratio="9:16",
    )
    print(f"✅ 结尾视频: {closing_video}")

    print("\n" + "=" * 50)
    print("🎉 数字人视频生成完成！")
    print(f"   开场: {opening_video}")
    print(f"   结尾: {closing_video}")
    print("=" * 50)


if __name__ == "__main__":
    main()
