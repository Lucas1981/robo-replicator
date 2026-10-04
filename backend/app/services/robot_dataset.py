import io
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

from app.config import DEBUG_DRAW_SAMPLE_PATH, DEBUG_SKIP_ROBOT_STEP
from app.services.dataset_replay_scripts import write_replay_scripts
from app.services.robot_config import DATASET_FEATURES, FPS
from app.services.robot_trajectory import (
    build_trajectory,
    estimate_duration_seconds,
    write_draw_source_meta,
)
from app.services.svg_parser import SvgParseError, parse_svg_paths

logger = logging.getLogger(__name__)


class RobotDatasetError(RuntimeError):
    """Raised when SVG to LeRobotDataset conversion fails."""


def dataset_output_filename(source_filename: str) -> str:
    stem = Path(source_filename).stem
    if stem.endswith("-paths"):
        stem = stem[: -len("-paths")]
    return f"{stem or 'output'}-draw.zip"


def dataset_output_content_type() -> str:
    return "application/zip"


def svg_to_robot_dataset(svg_bytes: bytes, source_filename: str, task: str | None = None) -> bytes:
    if DEBUG_SKIP_ROBOT_STEP:
        return _load_debug_draw_sample(source_filename)

    task_label = task or f"Draw paths from {source_filename}"
    dataset_dir, temp_parent = _write_dataset_directory(svg_bytes, source_filename, task_label)
    try:
        return _directory_to_zip(dataset_dir)
    finally:
        shutil.rmtree(temp_parent, ignore_errors=True)


def _load_debug_draw_sample(source_filename: str) -> bytes:
    sample_path = DEBUG_DRAW_SAMPLE_PATH
    if not sample_path.is_file():
        raise RobotDatasetError(
            f"DEBUG_SKIP_ROBOT_STEP is enabled but sample dataset zip not found at {sample_path}. "
            "Run: python backend/scripts/generate_robot_sample.py"
        )

    logger.warning(
        "DEBUG_SKIP_ROBOT_STEP is enabled; serving sample dataset from %s for source file %r",
        sample_path,
        source_filename,
    )
    return sample_path.read_bytes()


def _write_dataset_directory(svg_bytes: bytes, source_filename: str, task: str) -> tuple[Path, Path]:
    try:
        parsed = parse_svg_paths(svg_bytes)
        result = build_trajectory(parsed)
    except (SvgParseError, ValueError) as exc:
        raise RobotDatasetError(str(exc)) from exc

    LeRobotDataset = _require_lerobot()
    import torch

    temp_parent = Path(tempfile.mkdtemp(prefix="robo-draw-"))
    temp_root = temp_parent / "dataset"
    repo_id = f"robo-replicator/{_dataset_stem(source_filename)}"

    dataset = LeRobotDataset.create(
        repo_id=repo_id,
        fps=FPS,
        features=DATASET_FEATURES,
        root=temp_root,
        robot_type="so101_follower",
        use_videos=False,
    )

    for joints in result.frames:
        dataset.add_frame(
            {
                "action": torch.tensor(joints, dtype=torch.float32),
                "observation.state": torch.tensor(joints, dtype=torch.float32),
                "task": task,
            }
        )

    dataset.save_episode()
    dataset.finalize()
    write_draw_source_meta(temp_root, result.mapping, source_filename=source_filename)
    write_replay_scripts(temp_root, repo_id)

    duration = estimate_duration_seconds(len(result.frames), FPS)
    logger.info(
        "Built LeRobotDataset for %r: %d paths, %d frames, %.1fs @ %d fps "
        "(svg %gx%g, scale %.6g)",
        source_filename,
        len(parsed.paths),
        len(result.frames),
        duration,
        FPS,
        result.mapping.svg_width,
        result.mapping.svg_height,
        result.mapping.scale,
    )
    return temp_root, temp_parent


def write_dataset_directory(svg_bytes: bytes, output_dir: Path, source_filename: str, task: str) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)

    try:
        parsed = parse_svg_paths(svg_bytes)
        result = build_trajectory(parsed)
    except (SvgParseError, ValueError) as exc:
        raise RobotDatasetError(str(exc)) from exc

    LeRobotDataset = _require_lerobot()
    import torch

    repo_id = f"robo-replicator/{_dataset_stem(source_filename)}"
    dataset = LeRobotDataset.create(
        repo_id=repo_id,
        fps=FPS,
        features=DATASET_FEATURES,
        root=output_dir,
        robot_type="so101_follower",
        use_videos=False,
    )

    for joints in result.frames:
        dataset.add_frame(
            {
                "action": torch.tensor(joints, dtype=torch.float32),
                "observation.state": torch.tensor(joints, dtype=torch.float32),
                "task": task,
            }
        )

    dataset.save_episode()
    dataset.finalize()
    write_draw_source_meta(output_dir, result.mapping, source_filename=source_filename)
    write_replay_scripts(output_dir, repo_id)
    return output_dir


def _dataset_stem(source_filename: str) -> str:
    stem = Path(source_filename).stem or "draw"
    if stem.endswith("-paths"):
        return stem[: -len("-paths")]
    return stem


def _directory_to_zip(directory: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(directory).as_posix())
    return buffer.getvalue()


def _require_lerobot():
    try:
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
    except ImportError as exc:
        raise RobotDatasetError(
            "lerobot is not installed. Install robot export support with:\n"
            "  pip install -r backend/requirements-robot.txt"
        ) from exc
    return LeRobotDataset
