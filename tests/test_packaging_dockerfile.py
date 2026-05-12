from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_precreates_openzues_home_before_user_node() -> None:
    dockerfile_path = REPO_ROOT / "Dockerfile"
    assert dockerfile_path.is_file()

    dockerfile = dockerfile_path.read_text(encoding="utf-8")
    runtime_stage_index = dockerfile.rfind("FROM base-runtime")
    state_dir_index = dockerfile.find(
        "RUN install -d -m 0700 -o node -g node /home/node/.openzues && \\",
        runtime_stage_index,
    )
    user_index = dockerfile.find("USER node", runtime_stage_index)

    assert runtime_stage_index > -1
    assert state_dir_index > -1
    assert user_index > -1
    assert state_dir_index > runtime_stage_index
    assert state_dir_index < user_index
    assert "mkdir -p /home/node/.openzues" not in dockerfile
    assert (
        "stat -c '%U:%G %a' /home/node/.openzues | grep -qx 'node:node 700'"
        in dockerfile
    )
