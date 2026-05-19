"""Generate digital avatar talking-head video (outputs to output/avatar/)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.avatar_service import AvatarService


def main():
    """Generate digital avatar video from user input text"""
    print("=" * 50)
    print(" Digital Avatar Video Generation")
    print("=" * 50)

    if len(sys.argv) > 1:
        input_text = " ".join(sys.argv[1:])
    else:
        input_text = input("Enter avatar speech text: ").strip()

    if not input_text:
        print("No input text provided")
        return

    print(f"\nSpeech text ({len(input_text)} chars):")
    print(f"   {input_text[:100]}...")

    avatar = AvatarService(
        avatar_id="Anna_public_3_20240119",
        voice_id="2d9d16b7e4d146e89819c80f6ff47753",
    )

    output_dir = Path("./output/avatar")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "avatar-video.mp4"

    print(f"\nGenerating avatar video...")
    result = avatar.generate_and_download(
        input_text=input_text,
        output_path=output_path,
        title="Avatar Video",
        video_aspect_ratio="9:16",
    )
    print(f"Video saved: {result}")

    print("\n" + "=" * 50)
    print("Avatar video generation complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
